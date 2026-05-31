#!/usr/bin/env python3
# AI Suggestion v0.7.3.3 [j5onrf] [05-31-26]

import sys
import re
import os
import json

CONTEXT_FILE = os.path.expanduser("~/.config/local-ai/ai-suggestion/ai-context.txt")
INDEX_FILE = os.path.expanduser("~/.config/local-ai/ai-suggestion/ai-context.idx")
USAGE_FILE = os.path.expanduser("~/.config/local-ai/ai-suggestion/api-usage.json")
DESTRUCTIVE_KEYWORDS = ["rm ", "dd ", "mkfs", "shred", "chmod -R 777", "> /dev/sda"]

# Pre-compile regex patterns to save execution time
TOKEN_RE = re.compile(r"[^\w\s]")

# Standard English stop-words to prevent grammatical collisions (0ms overhead)
STOP_WORDS = {
    "is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", 
    "for", "me", "you", "my", "your", "we", "us", "show", "get", "run", "check",
    "please", "can", "could", "would", "tell", "find", "list", "are", "about", 
    "in", "next", "few", "days", "going", "soon", "anytime", "day", "week"
}

def sanitize_input(text):
    if not text:
        return ""
    return re.sub(r"[`$]", "", text).strip()

def tokenize(text):
    # Lowercase and replace non-alphanumeric with spaces using pre-compiled regex
    raw_tokens = [w for w in TOKEN_RE.sub(" ", text.lower()).split() if len(w) > 1]
    # Filter out common stop-words to keep the matching strictly keyword-focused
    return [t for w in raw_tokens if (t := w) not in STOP_WORDS]

def compile_vector_index():
    if not os.path.exists(CONTEXT_FILE):
        return False
    with open(CONTEXT_FILE, "r") as f:
        lines = f.read().splitlines()
    index_data = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "----->" in line or "--->" not in line:
            continue
        cmd_side, intents_side = line.split("--->", 1)
        intents = [i.strip() for i in intents_side.split(",")]
        for intent in intents:
            tokens = tokenize(intent)
            if tokens:
                index_data.append({"cmd": cmd_side.strip(), "intent": intent, "tokens": tokens})
    # Write as a minified, single-line JSON to optimize read operations
    with open(INDEX_FILE, "w") as f:
        json.dump(index_data, f)
    return True

# Highly efficient EAFP file timestamp check (minimizes syscall overhead)
try:
    mtime_ctx = os.path.getmtime(CONTEXT_FILE)
    try:
        mtime_idx = os.path.getmtime(INDEX_FILE)
        if mtime_ctx > mtime_idx:
            compile_vector_index()
    except OSError:
        compile_vector_index()
except OSError:
    pass

def check_danger(cmd):
    if not cmd:
        return cmd
    cmd_lower = cmd.lower()
    if any(kw in cmd_lower for kw in DESTRUCTIVE_KEYWORDS):
        return f"DANGER_FLAGGED:{cmd}"
    return cmd

def matrix_search(query, threshold=0.50): # Lowered slightly to capture close alternative candidates
    try:
        query_tokens = tokenize(query)
        if not query_tokens:
            return None
        with open(INDEX_FILE, "r") as f:
            index_data = json.load(f)
    except OSError:
        return None

    query_set = set(query_tokens)
    len_query = len(query_tokens)
    
    # Correctly initialize the candidates list
    candidates = []
    
    for entry in index_data:
        match_count = len(query_set.intersection(entry["tokens"]))
        if match_count == 0:
            continue
        score = (2.0 * match_count) / (len_query + len(entry["tokens"]))
        if score >= threshold:
            candidates.append((score, entry["cmd"], entry["intent"]))
            
    # Sort candidates by score descending
    candidates.sort(reverse=True, key=lambda x: x[0])
    
    # Extract up to 3 unique command contenders with their matching intents
    seen = set()
    top_entries = []
    for score, cmd, intent in candidates:
        if cmd not in seen:
            seen.add(cmd)
            # Evaluate danger flag on the command
            danger_cmd = check_danger(cmd)
            top_entries.append(f"{intent}|||{danger_cmd}")
            if len(top_entries) == 3:
                break
                
    return "\n".join(top_entries) if top_entries else None

def parse_universal_file(file_path):
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        return []

    new_mappings = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("--"):
            continue
        
        # 1. Parse direct ---> context format (for merging external context files)
        if "--->" in line and not line.startswith("----->"):
            cmd_side, intents_side = line.split("--->", 1)
            new_mappings.append((cmd_side.strip(), intents_side.strip(), True))
            continue

        # 2. Parse Bash/Zsh Aliases
        alias_match = re.match(r"^alias\s+(\w+)\s*=\s*(.*)", line)
        if alias_match:
            trigger = alias_match.group(1).strip()
            cmd_part = alias_match.group(2).strip().strip("'\"")
            new_mappings.append((cmd_part, trigger, False))
            continue

        # 3. Parse Hyprland Legacy Binds (.conf)
        if line.startswith("bind") and "exec," in line:
            try:
                left_side, cmd_part = line.split("exec,", 1)
                cmd_part = cmd_part.strip().strip("'\"")
                parts = [p.strip() for p in left_side.split(",")]
                trigger_key = ""
                for p in reversed(parts):
                    clean_p = p.replace("bind", "").replace("=", "").strip()
                    if clean_p:
                        trigger_key = clean_p
                        break
                if cmd_part:
                    new_mappings.append((cmd_part, trigger_key, False))
            except Exception:
                pass
            continue

        # 4. Parse Hyprland 0.55+ Modern Lua Binds (.lua)
        # e.g., hl.bind("SUPER + SHIFT + Q", hl.dsp.exec_cmd("firefox"))
        if "hl.bind" in line and "hl.dsp.exec_cmd" in line:
            try:
                cmd_match = re.search(
                    r"hl\.dsp\.exec_cmd\(\s*\[*['\"]*(.*?)['\"]*\]*\s*\)", line
                )
                key_match = re.search(
                    r"hl\.bind\(\s*\[*['\"]*(.*?)['\"]*\]*\s*,", line
                )
                if cmd_match and key_match:
                    cmd_part = cmd_match.group(1).strip().strip("'\"")
                    trigger_key = key_match.group(1).strip().strip("'\"")
                    
                    # Split into short, non-truncating lines to prevent clipboard bugs
                    trigger_key = trigger_key.replace("mainMod ..", "SUPER")
                    trigger_key = trigger_key.replace("mainMod", "SUPER")
                    trigger_key = trigger_key.replace("..", "+")
                    trigger_key = trigger_key.replace("\"", "").replace("'", "")
                    trigger_key = trigger_key.strip()
                    trigger_key = re.sub(r"\s+", " ", trigger_key)
                    if cmd_part:
                        new_mappings.append((cmd_part, trigger_key, False))
            except Exception:
                pass
            continue

        # 5. Parse Neovim Lua Keymaps
        if "keymap.set" in line or "api.nvim_set_keymap" in line:
            try:
                quoted_strings = re.findall(r"['\"](.*?)['\"]", line)
                if len(quoted_strings) >= 3:
                    trigger = quoted_strings[1]
                    cmd_part = quoted_strings[2]
                    is_cmd_valid = trigger and cmd_part
                    if is_cmd_valid and not cmd_part.startswith(":") and not cmd_part.startswith("<"):
                        new_mappings.append((cmd_part, trigger, False))
                    elif cmd_part.startswith(":"):
                        new_mappings.append((f"nvim {cmd_part}", trigger, False))
            except Exception:
                pass
            continue

        # 6. Parse WezTerm / Lua config binds
        if "SpawnCommand" in line and "args" in line:
            try:
                key_match = re.search(r"key\s*=\s*['\"](.*?)['\"]", line)
                args_match = re.search(
                    r"args\s*=\s*\{\s*['\"](.*?)['\"]", line
                )
                if key_match and args_match:
                    trigger = key_match.group(1).strip()
                    cmd_part = args_match.group(1).strip()
                    new_mappings.append((cmd_part, trigger, False))
            except Exception:
                pass
            continue
            
    return new_mappings

def generate_intents_for_cmd(cmd, trigger):
    # Safe fallback if LLM is offline
    default_intents = f"launch {trigger}, run {cmd.split()[0]} via {trigger}" if trigger else f"run {cmd.split()[0]}"
    url, headers, model = get_api_config()
    import requests
    try:
        prompt = (
            f"Generate 3 natural language intents (phrases) a user would type "
            f"into a terminal to trigger this command: '{cmd}'. Output ONLY the "
            f"phrases separated by commas. No explanations, no numbering, no formatting."
        )
        payload = {
            "messages": [
                {"role": "system", "content": "You are a strict terminal command to intent translator. Output only comma-separated phrases."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        if model:
            payload["model"] = model
            
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            ans = response.json()["choices"][0]["message"]["content"].strip()
            ans = re.sub(r"^\d+\.\s*", "", ans)
            if ans and len(ans) < 150:
                return f"{ans}, {default_intents}"
    except Exception:
        pass
    return default_intents

def get_api_config():
    # Default to local llama-server on localhost:8080
    url = "http://localhost:8080/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    model = None

    # Check if Google Gemini API is configured
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {gemini_key}"
        }
        # Default to stable Gemini Flash, but allow custom models via environment variables
        model = os.environ.get("CLOUD_MODEL", "gemini-1.5-flash")
        return url, headers, model

    # Check for generic OpenAI-compatible cloud provider (e.g. OpenRouter, Groq, Together)
    cloud_key = os.environ.get("CLOUD_API_KEY")
    cloud_url = os.environ.get("CLOUD_API_URL")
    if cloud_key and cloud_url:
        url = cloud_url
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cloud_key}"
        }
        model = os.environ.get("CLOUD_MODEL")
        return url, headers, model

    return url, headers, model

def log_usage(model_name, prompt_tokens, completion_tokens, total_tokens):
    try:
        os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
        data = {}
        if os.path.exists(USAGE_FILE):
            with open(USAGE_FILE, "r") as f:
                data = json.load(f)
        
        # Capture current transaction details
        data["last_model"] = model_name or "local"
        data["last_prompt_tokens"] = prompt_tokens
        data["last_completion_tokens"] = completion_tokens
        data["last_total_tokens"] = total_tokens
        
        # Accumulate cumulative stats
        data["total_prompt_tokens"] = data.get("total_prompt_tokens", 0) + prompt_tokens
        data["total_completion_tokens"] = data.get("total_completion_tokens", 0) + completion_tokens
        data["total_total_tokens"] = data.get("total_total_tokens", 0) + total_tokens
        data["total_calls"] = data.get("total_calls", 0) + 1
        
        with open(USAGE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def print_usage_on_demand():
    if not os.path.exists(USAGE_FILE):
        print("\033[1;31mError: No API usage data found yet. Run an AI command first.\033[0m")
        sys.exit(1)
    try:
        with open(USAGE_FILE, "r") as f:
            data = json.load(f)
        model = data.get("last_model", "unknown")
        p_tok = data.get("last_prompt_tokens", 0)
        c_tok = data.get("last_completion_tokens", 0)
        t_tok = data.get("last_total_tokens", 0)
        print(f"\033[1;30m[Model: {model} | Prompt: {p_tok}t | Gen: {c_tok}t | Total: {t_tok}t]\033[0m")
        sys.exit(0)
    except Exception as e:
        print(f"Error reading usage: {str(e)}")
        sys.exit(1)

# ==============================================================================
# ROUTING & EXECUTION
# ==============================================================================

# On-Demand Token Usage monitor
if len(sys.argv) > 1 and sys.argv[1] == "--usage":
    print_usage_on_demand()

# Manual Status Dashboard Monitor
if len(sys.argv) > 1 and sys.argv[1] == "--status":
    url, headers, model = get_api_config()
    is_cloud = "googleapis" in url
    
    # Count mapped entries and tools cleanly
    mappings_count = 0
    tools_count = 0
    if os.path.exists(CONTEXT_FILE):
        try:
            with open(CONTEXT_FILE, "r") as f:
                lines = f.read().splitlines()
            for line in lines:
                if "--->" in line and not line.startswith("#"):
                    mappings_count += 1
                    if line.strip().startswith("[TOOL]"):
                        tools_count += 1
        except Exception:
            pass

    # Print a beautiful, high-contrast, compact ASCII dashboard card
    print("\033[1;36m┌──────────────────────────────────────────────────────────┐\033[0m")
    print("\033[1;36m│          AI-SUGGESTION SYSTEM MONITOR & DASHBOARD        │\033[0m")
    print("\033[1;36m├──────────────────────────────────────────────────────────┤\033[0m")
    
    # Active Connection Mode
    if is_cloud:
        print(f"\033[1;36m│\033[0m  Active Mode:     \033[1;32mGoogle Gemini Cloud API\033[0m                \033[1;36m│\033[0m")
        key_show = os.environ.get("GEMINI_API_KEY", "")[:8] + "..."
        print(f"\033[1;36m│\033[0m  API Key:         \033[1;30mLoaded ({key_show})\033[0m                      \033[1;36m│\033[0m")
        print(f"\033[1;36m│\033[0m  Cloud Model:     \033[1;35m{model or 'gemini-1.5-flash'}\033[0m                 \033[1;36m│\033[0m")
        
        # Tools Status strings
        gr_status = "\033[1;32mGoogle Search Grounding via --gs\033[0m"
        print(f"\033[1;36m│\033[0m  Active Tools:    {gr_status:<49}\033[1;36m│\033[0m")
    else:
        print(f"\033[1;36m│\033[0m  Active Mode:     \033[1;34mLocal Llama Server\033[0m                     \033[1;36m│\033[0m")
        print(f"\033[1;36m│\033[0m  Connection Port: \033[1;30mhttp://localhost:8080\033[0m                   \033[1;36m│\033[0m")
        
    print("\033[1;36m├──────────────────────────────────────────────────────────┤\033[0m")
    
    # Local Index Metrics
    print(f"\033[1;36m│\033[0m  Context Database: \033[1;30m{CONTEXT_FILE.replace(os.path.expanduser('~'), '~')}\033[0m    \033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m  Mapped Shortcuts: \033[1;33m{mappings_count:<5}\033[0m                                 \033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m  Active [TOOL]s:   \033[1;33m{tools_count:<5}\033[0m                                 \033[1;36m│\033[0m")
    
    # Check if index exists
    idx_exists = "\033[1;32mActive & Synced\033[0m" if os.path.exists(INDEX_FILE) else "\033[1;31mMissing\033[0m"
    print(f"\033[1;36m│\033[0m  Search Index:    {idx_exists:<49}\033[1;36m│\033[0m")
    
    # Cumulative API usage stats (if file exists)
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r") as f:
                u_data = json.load(f)
            print("\033[1;36m├──────────────────────────────────────────────────────────┤\033[0m")
            last_msg = f"{u_data.get('last_model', 'local')} ({u_data.get('last_total_tokens', 0)}t total)"
            print(f"\033[1;36m│\033[0m  Last Request:    \033[1;30m{last_msg:<41}\033[0m\033[1;36m│\033[0m")
            print(f"\033[1;36m│\033[0m  Lifetime Calls:  \033[1;30m{u_data.get('total_calls', 0):<41}\033[0m\033[1;36m│\033[0m")
            print(f"\033[1;36m│\033[0m  Lifetime Tokens: \033[1;30m{u_data.get('total_total_tokens', 0):<41}\033[0m\033[1;36m│\033[0m")
        except Exception:
            pass
            
    print("\033[1;36m└──────────────────────────────────────────────────────────┘\033[0m")
    sys.exit(0)

# Map bindings and aliases configuration mode (Universal Parser)
if len(sys.argv) > 1 and sys.argv[1] == "--map":
    if len(sys.argv) < 3:
        print("Error: Please specify the path to your config file.")
        print("Usage: ai --map /path/to/file")
        sys.exit(1)
    file_path = sys.argv[2]
    mappings = parse_universal_file(file_path)
    if not mappings:
        print("No valid configurations (aliases, keybinds, or mappings) found or file could not be read.")
        sys.exit(1)
        
    print(f"⚡ Starting Universal Configuration Mapper... Found {len(mappings)} entry candidates.")
    successful = 0
    try:
        os.makedirs(os.path.dirname(CONTEXT_FILE), exist_ok=True)
        with open(CONTEXT_FILE, "a") as f:
            for cmd, trigger, is_pre_mapped in mappings:
                if is_pre_mapped:
                    print(f"  → Merging mapping: {cmd} ---> {trigger}")
                    f.write(f"\n{cmd} ---> {trigger}")
                    successful += 1
                else:
                    # Clean trailing redirects if they already exist
                    cmd_write = cmd
                    # Detect if key trigger looks like a desktop/GUI binder
                    is_gui_bind = trigger and any(k in trigger.lower() for k in ["f", "print", "ctrl", "alt", "super", "shift", "mod"])
                    if is_gui_bind and not cmd_write.endswith(">/dev/null 2>&1") and not cmd_write.startswith("alias"):
                        cmd_write = f"{cmd_write} >/dev/null 2>&1"
                        
                    print(f"  → Mapping command: {cmd_write}")
                    intents = generate_intents_for_cmd(cmd_write, trigger)
                    f.write(f"\n{cmd_write} ---> {intents}")
                    successful += 1
        compile_vector_index()
        print(f"✓ Successfully mapped {successful} items to ai-context.txt and recompiled index!")
        sys.exit(0)
    except Exception as e:
        print(f"Error writing to context: {str(e)}")
        sys.exit(1)

# Teach Mode (Supports both CLI Quick-add and Editor mode)
if len(sys.argv) > 1 and (sys.argv[1] == "--teach" or sys.argv[1] == "--learn"):
    if len(sys.argv) >= 4:
        # Quick-add mode (ai --teach "command" "intent")
        cmd_to_learn = sys.argv[2]
        intent_to_learn = sys.argv[3]
        try:
            os.makedirs(os.path.dirname(CONTEXT_FILE), exist_ok=True)
            with open(CONTEXT_FILE, "a") as f:
                f.write(f"\n{cmd_to_learn} ---> {intent_to_learn}")
            compile_vector_index()
            print("SUCCESS")
            sys.exit(0)
        except Exception:
            pass
    sys.exit(1)

# Handle interactive chat mode flag or direct conversational queries
if len(sys.argv) > 1 and sys.argv[1] == "--talk":
    # Lazy-load requests library only when active network chat is needed
    import requests
    url, headers, model = get_api_config()
    
    if len(sys.argv) > 2:
        raw_query = " ".join(sys.argv[2:])
        
        # Check if the query explicitly requests Google Search grounding
        use_google_search = False
        if raw_query.startswith("--gs "):
            use_google_search = True
            query = raw_query[5:].strip()
        elif raw_query == "--gs":
            use_google_search = True
            query = ""
        else:
            query = raw_query

        # Safety validation
        if use_google_search and not os.environ.get("GEMINI_API_KEY"):
            print("\033[1;31mError: Google Search grounding (--gs) requires a valid GEMINI_API_KEY.\033[0m")
            sys.exit(1)
        
        # 1. Run a local matrix check to see if query maps to a [TOOL]
        system_context = ""
        # Skip local tool check if explicitly requesting search grounding
        if not use_google_search:
            tool_match = matrix_search(query)
            if tool_match:
                first_match = tool_match.split("\n")[0]
                if "|||" in first_match:
                    intent, cmd = first_match.split("|||", 1)
                    if cmd.startswith("[TOOL]"):
                        tool_cmd = cmd.replace("[TOOL]", "").strip()
                        # Lazy-load subprocess only when executing a local tool
                        import subprocess
                        try:
                            # Increased timeout safety from 8s to 15s to support slow package/mirror syncs
                            output = subprocess.check_output(tool_cmd, shell=True, text=True, timeout=15).strip()
                            # Clean confirmation for silent GUI tools
                            if not output:
                                output = "Action executed successfully."
                            # Inject raw output only - no path or filename leaks to prevent LLM confusion
                            system_context = f"{output}\n"
                        except Exception as e:
                            # Print explicit red warning directly to terminal stderr if tool crashes or times out (no "DEBUG" prefix)
                            print(f"\033[1;31mTool execution failed: {str(e)}\033[0m", file=sys.stderr)
                            system_context = f"[SYSTEM ERROR] Failed to run local tool: {str(e)}\n"

        # 2. Compile conversational assistant system prompt
        system_prompt = (
            "You are a helpful, conversational local AI shell assistant with read-only "
            "terminal access. Use the provided real-time system context to answer "
            "the user's questions clearly, concisely, and directly. Do not state "
            "that you cannot access their machine, as the required data has "
            "already been successfully fetched and provided to you."
        )
        if system_context:
            system_prompt += (
                f"\n\n# Real-time System Context\n"
                f"Use the following real-time data to answer the user's request:\n"
                f"{system_context}"
            )

        # 3. Generate correct REST request payload for requested route
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if use_google_search and gemini_key:
            # Route to native Google Developer streamGenerateContent endpoint
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model or 'gemini-1.5-flash'}:streamGenerateContent?alt=sse"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": gemini_key
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": query}
                        ]
                    }
                ],
                "tools": [
                    {"google_search": {}}
                ]
            }
        else:
            # Standard local / Cloud OpenAI-compatible endpoint payload route
            unified_prompt = ""
            if system_context:
                unified_prompt += (
                    f"[REAL-TIME SYSTEM CONTEXT]\n"
                    f"You have read-only terminal access. The required system data has "
                    f"already been successfully fetched and is provided below:\n{system_context}\n"
                    f"Do not state that you cannot access their system, as the data has "
                    f"already been successfully provided to you.\n\n"
                )
            unified_prompt += f"User Question: {query}"

            payload = {
                "messages": [
                    {"role": "user", "content": unified_prompt}
                ],
                "stream": True
            }
            if model:
                payload["model"] = model

        try:
            response = requests.post(url, json=payload, headers=headers, stream=True)
            # Raise an HTTPError if Google returns an API failure (like 401 Unauthorized) [1]
            response.raise_for_status()
            
            first_chunk = True
            for chunk in response.iter_lines():
                if not chunk:
                    continue
                decoded = chunk.decode("utf-8").replace("data: ", "").strip()
                if decoded == "[DONE]":
                    break
                try:
                    data = json.loads(decoded)
                    
                    # 1. Parse standard streaming text completions (OpenAI format)
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["delta"].get("content", "")
                        if content:
                            if first_chunk:
                                print("\033[1;32mAI: \033[0m", end="", flush=True)
                                first_chunk = False
                            print(content, end="", flush=True)
                            
                    # 2. Parse native Google GenerateContentResponse stream chunks
                    if "candidates" in data and len(data["candidates"]) > 0:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                            content = candidate["content"]["parts"][0].get("text", "")
                            if content:
                                if first_chunk:
                                    print("\033[1;32mAI: \033[0m", end="", flush=True)
                                    first_chunk = False
                                print(content, end="", flush=True)

                    # 3. Parse standard stream usage chunk (OpenAI format)
                    if "usage" in data and data["usage"]:
                        usage = data["usage"]
                        p_tok = usage.get("prompt_tokens", 0)
                        c_tok = usage.get("completion_tokens", 0)
                        t_tok = usage.get("total_tokens", 0)
                        log_usage(model, p_tok, c_tok, t_tok)

                    # 4. Parse native Google GenerateContentResponse usage metadata
                    if "usageMetadata" in data:
                        metadata = data["usageMetadata"]
                        p_tok = metadata.get("promptTokenCount", 0)
                        c_tok = metadata.get("candidatesTokenCount", 0)
                        t_tok = metadata.get("totalTokenCount", 0)
                        log_usage(model, p_tok, c_tok, t_tok)
                except Exception:
                    pass
            print()
        except requests.exceptions.RequestException as e:
            # Dynamic Error feedback: check if in cloud vs local mode
            if os.environ.get("GEMINI_API_KEY") or os.environ.get("CLOUD_API_KEY"):
                print(f"\033[1;31mError: Cloud AI API request failed: {str(e)}\033[0m")
            else:
                print("\033[1;31mError: Local AI server is offline. Please start your server.\033[0m")
        except KeyboardInterrupt:
            print("\n\033[1;33mInterrupted.\033[0m")
        sys.exit(0)
    else:
        print("\033[1;34m💬 Local AI Conversation Mode. Ctrl+C to quit.\033[0m\n")
        try:
            while True:
                raw_query = input("❯ ")
                if not raw_query.strip():
                    continue

                # Parse optional grounding trigger inside conversational loop
                use_google_search = False
                if raw_query.strip().startswith("--gs "):
                    use_google_search = True
                    query = raw_query.strip()[5:].strip()
                elif raw_query.strip() == "--gs":
                    use_google_search = True
                    query = ""
                else:
                    query = raw_query.strip()

                # Safety validation
                if use_google_search and not os.environ.get("GEMINI_API_KEY"):
                    print("\033[1;31mError: Google Search grounding (--gs) requires a valid GEMINI_API_KEY.\033[0m")
                    continue

                # 1. Run a local matrix check inside the interactive chat loop
                system_context = ""
                if not use_google_search:
                    tool_match = matrix_search(query)
                    if tool_match and tool_match.startswith("[TOOL]"):
                        tool_cmd = tool_match.replace("[TOOL]", "").strip()
                        # Lazy-load subprocess only when executing a local tool
                        import subprocess
                        try:
                            # Increased timeout safety from 8s to 15s to support slow package/mirror syncs
                            output = subprocess.check_output(tool_cmd, shell=True, text=True, timeout=15).strip()
                            # Clean confirmation for silent GUI tools
                            if not output:
                                output = "Action executed successfully."
                            # Inject raw output only - no path or filename leaks to prevent LLM confusion
                            system_context = f"{output}\n"
                        except Exception as e:
                            # Print explicit red warning directly to terminal stderr if tool crashes or times out (no "DEBUG" prefix)
                            print(f"\033[1;31mTool execution failed: {str(e)}\033[0m", file=sys.stderr)
                            system_context = f"[SYSTEM ERROR] Failed to run local tool: {str(e)}\n"

                # 2. Compile conversational assistant system prompt
                system_prompt = (
                    "You are a helpful, conversational local AI shell assistant with read-only "
                    "terminal access. Use the provided real-time system context to answer "
                    "the user's questions clearly, concisely, and directly. Do not state "
                    "that you cannot access their machine, as the required data has "
                    "already been successfully fetched and provided to you."
                )
                if system_context:
                    system_prompt += (
                        f"\n\n# Real-time System Context\n"
                        f"Use the following real-time data to answer the user's request:\n"
                        f"{system_context}"
                    )

                # 3. Generate correct REST request payload for requested route
                gemini_key = os.environ.get("GEMINI_API_KEY")
                if use_google_search and gemini_key:
                    # Route to native Google Developer streamGenerateContent endpoint
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model or 'gemini-1.5-flash'}:streamGenerateContent?alt=sse"
                    headers = {
                        "Content-Type": "application/json",
                        "x-goog-api-key": gemini_key
                    }
                    payload = {
                        "contents": [
                            {
                                "parts": [
                                    {"text": query}
                                ]
                            }
                        ],
                        "tools": [
                            {"google_search": {}}
                        ]
                    }
                else:
                    # Standard local / Cloud OpenAI-compatible endpoint payload route
                    unified_prompt = ""
                    if system_context:
                        unified_prompt += (
                            f"[REAL-TIME SYSTEM CONTEXT]\n"
                            f"You have read-only terminal access. The required system data has "
                            f"already been successfully fetched and is provided below:\n{system_context}\n"
                            f"Do not state that you cannot access their system, as the data has "
                            f"already been successfully provided to you.\n\n"
                        )
                    unified_prompt += f"User Question: {query}"

                    payload = {
                        "messages": [
                            {"role": "user", "content": unified_prompt}
                        ],
                        "stream": True
                    }
                    if model:
                        payload["model"] = model
                    
                try:
                    response = requests.post(url, json=payload, headers=headers, stream=True)
                    # Raise an HTTPError if Google returns an API failure (like 401 Unauthorized) [1]
                    response.raise_for_status()
                    
                    first_chunk = True
                    for chunk in response.iter_lines():
                        if not chunk:
                            continue
                        decoded = chunk.decode("utf-8").replace("data: ", "").strip()
                        if decoded == "[DONE]":
                            break
                        try:
                            data = json.loads(decoded)
                            
                            # 1. Parse standard streaming text completions (OpenAI format)
                            if "choices" in data and len(data["choices"]) > 0:
                                content = data["choices"][0]["delta"].get("content", "")
                                if content:
                                    if first_chunk:
                                        print("\033[1;32mAI: \033[0m", end="", flush=True)
                                        first_chunk = False
                                    print(content, end="", flush=True)
                                    
                            # 2. Parse native Google GenerateContentResponse stream chunks
                            if "candidates" in data and len(data["candidates"]) > 0:
                                candidate = data["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                                    content = candidate["content"]["parts"][0].get("text", "")
                                    if content:
                                        if first_chunk:
                                            print("\033[1;32mAI: \033[0m", end="", flush=True)
                                            first_chunk = False
                                        print(content, end="", flush=True)

                            # 3. Parse standard stream usage chunk (OpenAI format)
                            if "usage" in data and data["usage"]:
                                usage = data["usage"]
                                p_tok = usage.get("prompt_tokens", 0)
                                c_tok = usage.get("completion_tokens", 0)
                                t_tok = usage.get("total_tokens", 0)
                                log_usage(model, p_tok, c_tok, t_tok)

                            # 4. Parse native Google GenerateContentResponse usage metadata
                            if "usageMetadata" in data:
                                metadata = data["usageMetadata"]
                                p_tok = metadata.get("promptTokenCount", 0)
                                c_tok = metadata.get("candidatesTokenCount", 0)
                                t_tok = metadata.get("totalTokenCount", 0)
                                log_usage(model, p_tok, c_tok, t_tok)
                        except Exception:
                            pass
                    print("\n")
                except requests.exceptions.RequestException:
                    print("\033[1;31mError: Local AI server is offline. Please start your server.\033[0m\n")
        except KeyboardInterrupt:
            print("\n\033[1;33mExiting conversation.\033[0m")
            sys.exit(0)

# ==============================================================================
# INPUT PROCESSING (Direct shell typo lookup only)
# ==============================================================================
user_input = sanitize_input(" ".join(sys.argv[1:])) if len(sys.argv) > 1 else ""
if not user_input or sys.argv[1].startswith("--"):
    sys.exit(0)

# Matrix Search (Automation/Commands)
matched_base = matrix_search(user_input)
if matched_base:
    # Clean any [TOOL] prefixes out before sending the suggestions to the shell hook
    lines = matched_base.split("\n")
    out_lines = []
    for line in lines:
        intent, cmd = line.split("|||", 1)
        if cmd.startswith("[TOOL]"):
            cmd = cmd.replace("[TOOL]", "").strip()
        out_lines.append(f"{intent}|||{cmd}")
    print("\n".join(out_lines))
    sys.exit(0)
else:
    print("Command Not Found")
    sys.exit(1)
