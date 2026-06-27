# File: /home/j5/.config/local-ai/tools/modules/gemini_client.py
# Description: Isolated stateful client for Gemini Interactions API. Keeps ai-agent.py minimal.

import os
import json
import time
import urllib.request as urlreq
import urllib.error as urlerr

def stream(messages, prefix, gkey, spinner_class):
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    sf = os.path.join(workspace, ".agent", "session.json")
    
    # 1. Load Stored State
    saved_id = None
    if os.path.exists(sf):
        try:
            with open(sf) as f:
                saved_id = json.load(f).get("last_interaction_id")
        except:
            pass

    # 2. Format request payload
    model = os.environ.get("CLOUD_MODEL", "gemini-3.5-flash")
    body = {"model": model, "input": messages[-1]["content"] if messages else "", "stream": True}
    if messages and messages[0]["role"] == "system":
        body["system_instruction"] = messages[0]["content"]
    if saved_id:
        body["previous_interaction_id"] = saved_id

    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    headers = {"x-goog-api-key": gkey, "Content-Type": "application/json"}
    req = urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    spinner = spinner_class()

    try:
        spinner.start()
        with urlreq.urlopen(req, timeout=30) as response:
            try:
                # Log API usage
                cfg_dir = os.path.expanduser("~/.config/local-ai")
                open(os.path.join(cfg_dir, ".request_log"), "a").write(f"{int(time.time())}|gemini-interactions\n")
            except: pass
            
            first, acc, resolved_id = True, [], None
            for line in response:
                dec = line.decode("utf-8").strip()
                if not dec: continue
                if dec.startswith("data:"): dec = dec[5:].strip()
                if dec == "[DONE]": continue
                try:
                    data = json.loads(dec)
                    if data.get("event_type") == "interaction.completed":
                        resolved_id = data.get("interaction", {}).get("id")
                    
                    content = ""
                    if data.get("event_type") == "step.delta":
                        delta = data.get("delta", {})
                        content = delta.get("text", "") if delta.get("type") == "text" else delta.get("content", {}).get("text", "")
                    
                    if content:
                        if first:
                            spinner.stop()
                            import sys
                            if sys.stdout.isatty():
                                sys.stdout.write(f"\r\x1b[2K\r\033[1;32m{prefix}\033[0m ")
                                sys.stdout.flush()
                            first = False
                        print(content, end="", flush=True)
                        acc.append(content)
                except:
                    pass
            print("")
            
            # Save the new ID for the next turn
            if resolved_id:
                try:
                    os.makedirs(os.path.dirname(sf), exist_ok=True)
                    with open(sf, "w") as f:
                        json.dump({"last_interaction_id": resolved_id}, f)
                except:
                    pass
            return "".join(acc)
            
    except urlerr.HTTPError as e:
        spinner.stop()
        # Self-healing: if the session expired (400/404), delete the tracking file and trigger fallback
        if saved_id and e.code in (400, 404):
            try: os.remove(sf)
            except: pass
        return None  # Returning None triggers fallback to the normal stateless loops in ai-agent.py
    except Exception:
        spinner.stop()
        return None
