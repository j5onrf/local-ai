# File: ~/.config/local-ai/modules/agent_core.py
import os
import sys
import re
import json
import time
import urllib.request as urlreq
import urllib.error as urlerr
import requests
import agent_ui as ui

# --- OPTIONAL SPEED-TEST HOOK ---
try:
    import speed_test
except ImportError:
    speed_test = None

# --- FAST-PATH BYTE EXTRACTOR ---
def extract_stream_content(line_bytes: bytes) -> str:
    """Performs raw byte-level searching to extract streaming tokens.
    
    Bypasses full-line string decoding and dictionary creation entirely for a major CPU speedup.
    """
    idx = line_bytes.find(b'"content":"')
    if idx == -1:
        idx = line_bytes.find(b'"text":"')
        if idx == -1:
            return ""
        start = idx + 8
    else:
        start = idx + 11

    end = start
    length = len(line_bytes)
    while end < length:
        char = line_bytes[end]
        if char == 34:  # ASCII for double quote '"'
            break
        if char == 92:  # ASCII for backslash '\'
            end += 2    # Skip escaped character
        else:
            end += 1

    try:
        raw_str_bytes = line_bytes[start:end]
        json_str = b'"' + raw_str_bytes + b'"'
        return json.loads(json_str.decode("utf-8", errors="ignore"))
    except Exception:
        return line_bytes[start:end].decode("utf-8", errors="ignore")


# --- CASCADING COMPLETION ENGINES ---
def stream(messages, prefix, gkey, spinner_class, show_stats: bool = True):
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    sf = os.path.join(workspace, ".agent", "session.json")
    
    saved_id = None
    if os.path.exists(sf):
        try:
            with open(sf, "r", encoding="utf-8") as f:
                saved_id = json.load(f).get("last_interaction_id")
        except Exception:
            pass

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
                cfg_dir = os.path.expanduser("~/.config/local-ai")
                with open(os.path.join(cfg_dir, ".request_log"), "a", encoding="utf-8") as f:
                    f.write(f"{int(time.time())}|gemini-interactions\n")
            except Exception:
                pass
            
            first, acc, resolved_id = True, [], None
            for line in response:
                dec = line.decode("utf-8").strip()
                if not dec:
                    continue
                if dec.startswith("data:"):
                    dec = dec[5:].strip()
                if dec == "[DONE]":
                    continue
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
                            if sys.stdout.isatty():
                                sys.stdout.write(f"\r\x1b[2K\r\033[1;32m{prefix}\033[0m ")
                                sys.stdout.flush()
                            first = False
                            if speed_test and show_stats:
                                speed_test.start()
                        print(content, end="", flush=True)
                        acc.append(content)
                        if speed_test and show_stats:
                            speed_test.count_token(content)
                except Exception:
                    pass
            print("")
            if speed_test and show_stats:
                speed_test.end()
            
            if resolved_id:
                try:
                    os.makedirs(os.path.dirname(sf), exist_ok=True)
                    with open(sf, "w", encoding="utf-8") as f:
                        json.dump({"last_interaction_id": resolved_id}, f)
                except Exception:
                    pass
            return "".join(acc)
    except urlerr.HTTPError as e:
        spinner.stop()
        if saved_id and e.code in (400, 404):
            try:
                os.remove(sf)
            except Exception:
                pass
        return None
    except Exception:
        spinner.stop()
        return None


def stream_response(messages: list, prefix: str = "AI: ", cfg_dir: str = "", show_stats: bool = False) -> str or None:
    acc = []
    spinner = ui.InlineSpinner()
    try:
        gkey = os.environ.get("GEMINI_API_KEY")
        if gkey:
            try:
                ans = stream(messages, prefix, gkey, ui.InlineSpinner, show_stats)
                if ans is not None:
                    return ans
            except Exception:
                pass
                
        configs = []
        okey = os.environ.get("OPENROUTER_API_KEY")
        if gkey:
            configs.append((
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                {"Authorization": f"Bearer {gkey}"},
                os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite"),
                {},
                30
            ))
        if okey:
            configs.append((
                "https://openrouter.ai/api/v1/chat/completions",
                {
                    "Authorization": f"Bearer {okey}",
                    "HTTP-Referer": "https://github.com/j5onrf/local-ai"
                },
                os.environ.get("OPENROUTER_MODEL", "openrouter/free"),
                {},
                180
            ))
        configs.append(("http://localhost:8080/v1/chat/completions", {}, "local-model", {}, 180))
        
        for url, headers, model, extra, timeout in configs:
            body = {"messages": messages, "stream": True, **extra}
            if model:
                body["model"] = model
                
            req = urlreq.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", **headers},
                method="POST"
            )
            retries = 2
            backoff = 1.5
            while retries >= 0:
                try:
                    spinner.start()
                    with urlreq.urlopen(req, timeout=timeout) as response:
                        try:
                            p = "gemini" if "generativelanguage" in url else "openrouter" if "openrouter" in url else None
                            if p and cfg_dir:
                                with open(os.path.join(cfg_dir, ".request_log"), "a", encoding="utf-8") as lf:
                                    lf.write(f"{int(time.time())}|{p}\n")
                        except Exception:
                            pass
                        first, resolved_model = True, None
                        for line in response:
                            if not line.startswith(b"data:"):
                                continue
                            content = extract_stream_content(line)
                            if content:
                                if first:
                                    spinner.stop()
                                    if sys.stdout.isatty():
                                        sys.stdout.write(f"\r\x1b[2K\r\033[1;32m{prefix}\033[0m ")
                                        sys.stdout.flush()
                                    first = False
                                    if speed_test and show_stats:
                                        speed_test.start()
                                print(content, end="", flush=True)
                                acc.append(content)
                                if speed_test and show_stats:
                                    speed_test.count_token(content)
                            else:
                                try:
                                    dec = line.decode("utf-8").strip()
                                    if dec.startswith("data:"):
                                        dec = dec[5:].strip()
                                    if dec == "[DONE]" or not dec:
                                        continue
                                    data = json.loads(dec)
                                    if "model" in data and not resolved_model:
                                        resolved_model = data["model"]
                                except Exception:
                                    pass
                        print("")
                        if speed_test and show_stats:
                            speed_test.end()
                        if resolved_model and resolved_model != model and sys.stdout.isatty():
                            home_dir = os.path.expanduser("~")
                            target_path = os.path.join(home_dir, "ollama_backup") + "/"
                            display_model = resolved_model
                            if display_model.startswith(target_path):
                                display_model = display_model.replace(target_path, ".../")
                            sys.stdout.write(f"\033[90m[via {display_model}]\033[0m\n")
                            sys.stdout.flush()
                        return "".join(acc)
                except urlerr.HTTPError as e:
                    spinner.stop()
                    if e.code == 429 and retries > 0:
                        time.sleep(backoff)
                        retries -= 1
                        backoff *= 2
                    elif e.code == 400:
                        sys.stderr.write(f"\n\033[1;31m[API 400 Error]: {e.read().decode('utf-8')}\033[0m\n")
                        break
                    else:
                        host = url.split('/')[2]
                        sys.stderr.write(f"\033[90m[sys] {host} failed: HTTP {e.code}\033[0m\n")
                        break
                except Exception as e:
                    spinner.stop()
                    host = url.split('/')[2]
                    sys.stderr.write(f"\033[90m[sys] {host} failed: {e}\033[0m\n")
                    break
    except KeyboardInterrupt:
        try: spinner.stop()
        except Exception: pass
        sys.stderr.write("\n\r\x1b[2K\r[sys] Interrupted.\n")
        sys.stderr.flush()
        return "".join(acc) if 'acc' in locals() else None
    return None


def get_accurate_token_count(text: str, server_url: str = "http://localhost:8080") -> int:
    try:
        res = requests.post(f"{server_url}/tokenize", json={"content": text}, timeout=3)
        return len(res.json().get("tokens", []))
    except Exception:
        return len(text) // 4


def show_memory_status(messages: list, max_context: int = 8192, server_url: str = "http://localhost:8080") -> None:
    total_toks = sum(get_accurate_token_count(m.get("content", ""), server_url) for m in messages)
    pct = (total_toks / max_context) * 100
    bar_len = 20
    filled = int((total_toks / max_context) * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    sys.stderr.write(f"\n\033[2m[sys] Context Window: {total_toks}/{max_context} tokens\033[0m\n")
    sys.stderr.write(f"\033[2m[sys] Usage: [{bar}] {pct:.1f}%\033[0m\n")
    sys.stderr.write(f"\033[2m[sys] Remaining: {max_context - total_toks} tokens\033[0m\n\n")
    sys.stderr.flush()
    
def prune_history(history: list, max_tokens: int = None) -> list:
    """Prunes old messages from conversation history to stay within context windows."""
    if len(history) <= 1:
        return history
    try:
        target_limit = int(os.environ.get("AI_MAX_TOKENS", 8192)) if max_tokens is None else max_tokens
    except Exception:
        target_limit = 8192

    sys_prompt = history[0]
    current_tokens = len(sys_prompt["content"]) // 4
    selected_messages = []

    for msg in reversed(history[1:]):
        approx_tokens = len(msg["content"]) // 4
        if not selected_messages or (current_tokens + approx_tokens <= target_limit):
            selected_messages.append(msg)
            current_tokens += approx_tokens
        else:
            break

    return [sys_prompt] + list(reversed(selected_messages))
