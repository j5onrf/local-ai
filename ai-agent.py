#!/usr/bin/env python3
# Local-Ai Agent v0.8.9.8 [j5onrf] [06-29-26]

import os
import sys
import re
import json
import time
import shutil
import select
import subprocess
import urllib.request as urlreq
import urllib.error as urlerr

# Optional imports with proper error boundary
try:
    import readline
    # Raw strings suppress python invalid escape warnings
    readline.parse_and_bind(r'"\e[A": previous-history')
    readline.parse_and_bind(r'"\e[B": next-history')
except ImportError:
    pass

# Strip empty arguments
sys.argv = [arg for arg in sys.argv if arg != ""]

# Configurations
CFG_DIR = os.path.expanduser("~/.config/local-ai")
CONTEXT_FILE = os.path.join(CFG_DIR, "ai-context.md")
SKILLS_DIR = os.path.join(CFG_DIR, "skills")
DESTRUCTIVE_KEYWORDS = ["rm ", "dd ", "mkfs", "shred", "chmod -R 777", "> /dev/sda"]
TOKEN_RE = re.compile(r"[^\w\s]")
STOP_WORDS = {
    "is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", 
    "for", "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"
}
BASE_PROMPT = (
    "Local shell AI assistant (read-only access).\n"
    "Provide direct, natural plain-text answers using any provided system context.\n"
    "No markdown (no bolding, no headers, no bullet lists).\n"
    "Always write full, complete, and helpful sentences.\n\n"
)

# Bootstrap on-demand modules path
sys.path.append(os.path.join(CFG_DIR, "tools", "modules"))

# Lazy/conditional import setup
def check_query_spelling(query, get_key_fn):
    try:
        from spellcheck import check_query_spelling as spelling_func
        return spelling_func(query, get_key_fn)
    except ImportError:
        return "RUN", query

# Cache placeholders
_CACHED_ENTRIES = None
_LAST_M_TIME = 0


def sanitize_input(text: str) -> str:
    """Removes backticks and dollar signs to sanitize shell user inputs."""
    if not text:
        return ""
    return re.sub(r"[`$]", "", text).strip()


def tokenize(text: str) -> list:
    """Splits text into lowercase tokens, filtering out stop words and short symbols."""
    if not text:
        return []
    cleaned = TOKEN_RE.sub(" ", text.lower())
    return [
        word for word in cleaned.split() 
        if len(word) > 1 and word not in STOP_WORDS
    ]


def ensure_mysys_exists():
    """Ensures profile generation exists for system interactions."""
    mysys_path = os.path.join(SKILLS_DIR, "system", "mysys.md")
    if not os.path.exists(mysys_path):
        try:
            generator = os.path.join(CFG_DIR, "tools", "generate-profile")
            subprocess.run([sys.executable, generator], check=False)
        except Exception as e:
            sys.stderr.write(f"\033[90m[sys] Profile bootstrap error: {e}\033[0m\n")


def find_skill_file(base_dir: str, skill_name: str) -> str or None:
    """Recursively searches for matching skill markdown files up to 3 levels deep."""
    target_filename = f"{skill_name.lower()}.md"
    for root, _, files in os.walk(base_dir):
        # Constraint: Do not traverse deeper than 3 levels from base
        relative_depth = root[len(base_dir):].count(os.sep)
        if relative_depth > 3:
            continue
        for filename in files:
            if filename.lower() == target_filename:
                return os.path.join(root, filename)
    return None


def load_skill_content(skills_str: str) -> str:
    """Parses and returns content of matching local system/agent skill files."""
    if not skills_str:
        return ""
    
    skills = [s.lstrip("-").lower() for s in skills_str.split()]
    contents = []
    
    for skill in skills:
        skill_file = find_skill_file(SKILLS_DIR, skill)
        if skill_file:
            if "system" in skill:
                ensure_mysys_exists()
            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    contents.append(f.read().strip())
            except Exception as e:
                sys.stderr.write(f"\033[1;31mError loading skill '{skill}': {e}\033[0m\n")
                
    return "\n\n".join(contents)


def print_stock_error(command_name: str):
    """Outputs a standard 'command not found' error formatted to match the active shell."""
    shell_name = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    if "zsh" in shell_name:
        sys.stderr.write(f"zsh: command not found: {command_name}\n")
    else:
        sys.stderr.write(f"bash: {command_name}: command not found\n")


def run_local_tool(cmd: str) -> str:
    """Executes a matching local shell command safely with standard timeouts."""
    try:
        # Strip trailing pipelines/pagers to capture clean stdout/stderr
        sanitized_cmd = re.sub(r'\|\s*(leaf|mdcat|cat|glow)\b.*$', '', cmd.strip()).strip()
        output = subprocess.check_output(
            sanitized_cmd,
            shell=True,
            text=True,
            timeout=15,
            env={**os.environ, "AI_CONTEXT_RUN": "1"}
        ).strip()
        return f"{output}\n" if output else "Action executed successfully.\n"
    except Exception as e:
        return f"[SYSTEM ERROR] Failed to run local tool: {e}\n"


def load_context_entries() -> list:
    """Loads and caches parsed tool mapping rules from the context configuration."""
    global _CACHED_ENTRIES, _LAST_M_TIME
    if not os.path.exists(CONTEXT_FILE):
        sys.stderr.write(f"\n\033[1;31m[CRITICAL ERROR]: ai-context.md not found at {CONTEXT_FILE}\033[0m\n")
        return []
        
    try:
        current_mtime = os.path.getmtime(CONTEXT_FILE)
        if _CACHED_ENTRIES is not None and current_mtime <= _LAST_M_TIME:
            return _CACHED_ENTRIES
            
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            lines = [
                cleaned for line in f.read().splitlines()
                if (cleaned := line.strip()) and not cleaned.startswith("#") and "--->" in cleaned
            ]
            
        parsed_entries = []
        for line in lines:
            cmd, intents_str = line.split("--->", 1)
            intents = [intent.strip() for intent in intents_str.split(",") if intent.strip()]
            if not intents:
                continue
            for intent in intents:
                tokens = tokenize(intent)
                if tokens:
                    parsed_entries.append({
                        "cmd": cmd.strip(),
                        "intent": intent,
                        "primary": intents[0],
                        "tokens": tokens
                    })
                    
        _CACHED_ENTRIES = parsed_entries
        _LAST_M_TIME = current_mtime
        return _CACHED_ENTRIES
    except Exception as e:
        sys.stderr.write(f"\033[1;31m[sys] Error parsing ai-context.md: {e}\033[0m\n")
        return []


def jaccard_search(query: str, threshold: float = 0.45) -> str or None:
    """Calculates Jaccard similarity indices to match input text to target tools."""
    q_clean = query.strip().lower()
    q_tokens = set(tokenize(query))
    if not q_tokens:
        return None
        
    entries = load_context_entries()
    if not entries:
        return None
        
    candidates = []
    for entry in entries:
        ent_tokens = set(entry["tokens"])
        ent_clean = entry["intent"].strip().lower()
        
        # Calculate standard intersection over union score
        intersection = q_tokens & ent_tokens
        union = q_tokens | ent_tokens
        score = len(intersection) / len(union) if union else 0.0
        
        # Boost matches for substring/exact occurrences
        if q_clean in ent_clean:
            score = max(score, 0.8)
        if q_clean == ent_clean:
            score = 3.0
            
        if score >= threshold:
            candidates.append((score, entry["cmd"], entry.get("primary", entry["intent"])))
            
    if not candidates:
        return None
        
    if any("system" in c[1].lower() for c in candidates):
        ensure_mysys_exists()
        
    # Sort by descending score and ascending keyword string length
    candidates.sort(key=lambda x: (-x[0], len(x[2])))
    
    seen = set()
    top_entries = []
    for _, cmd, primary in candidates:
        if cmd not in seen and len(top_entries) < 5:
            seen.add(cmd)
            top_entries.append(f"{primary}|||{clean_tool_prefix(cmd)}")
            
    return "\n".join(top_entries)


def clean_tool_prefix(cmd: str) -> str:
    """Cleans up internal syntax wrappers, system flags, and append options."""
    is_tool = cmd.startswith("[TOOL]")
    cleaned = cmd.replace("[TOOL]", "", 1).strip() if is_tool else cmd
    
    if cleaned.startswith("DANGER_FLAGGED:"):
        cleaned = f"DANGER_FLAGGED:{cleaned.replace('DANGER_FLAGGED:', '').replace('[TOOL]', '').strip()}"
        
    cleaned = cleaned.replace(" --s", "").strip()
    pager = ""
    
    pagers = [(" --leaf", "leaf"), (" --glow", "glow"), (" --cat", "cat"), (" --mdcat", "mdcat")]
    for flag, pg in pagers:
        if cleaned.endswith(flag):
            cleaned = cleaned[:-len(flag)].strip()
            pager = pg
            break
            
    if not pager and is_tool:
        pager = "mdcat" if shutil.which("mdcat") else "cat"
        
    if pager and (pager != "mdcat" or shutil.which("mdcat")):
        return f"{cleaned} | {pager}"
    return cleaned


def get_system_context(query: str) -> str:
    """Checks context mapping rules, triggers verification prompts, and returns context."""
    q_tokens = tokenize(query)
    if not q_tokens or "\n" in query.strip():
        return ""
        
    for entry in load_context_entries():
        ent_tokens = entry.get("tokens", [])
        # Match sequential sub-token segments inside user queries
        token_match = any(
            q_tokens[i : i + len(ent_tokens)] == ent_tokens 
            for i in range(len(q_tokens) - len(ent_tokens) + 1)
        )
        if token_match:
            cmd = entry.get("cmd", "")
            if cmd.startswith("[TOOL]"):
                tool = cmd.replace("[TOOL]", "").strip()
                # Run confirmation checks if silent execution flag is absent
                if " --s" not in tool:
                    from ux import confirm_tool
                    if not confirm_tool(tool):
                        return ""
                        
                if "system" in tool.lower():
                    ensure_mysys_exists()
                    
                tool = tool.replace(" --s", "").strip()
                for flag in [" --leaf", " --glow", " --cat", " --mdcat"]:
                    if tool.endswith(flag):
                        tool = tool[:-len(flag)].strip()
                        
                intent_tokens = set(tokenize(entry.get("intent", "")))
                args_list = [
                    w for w in query.split() 
                    if tokenize(w) and tokenize(w)[0] not in intent_tokens
                ]
                args = " ".join(args_list)
                
                # Replace dynamic wildcards with arguments
                if "$1" in tool or "{}" in tool:
                    tool = tool.replace("$1", args).replace("{}", args).strip()
                    
                sys.stderr.write(f"\033[2m[sys] Executing: {tool}\033[0m\n")
                sys.stderr.flush()
                return run_local_tool(tool)
    return ""


def stream_llm_response(messages: list, prefix: str = "AI: ") -> str or None:
    """Sends API requests across server cascades, streaming output directly to stdout."""
    gkey = os.environ.get("GEMINI_API_KEY")
    if gkey:
        try:
            import gemini_client
            from ux import InlineSpinner
            ans = gemini_client.stream(messages, prefix, gkey, InlineSpinner)
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
        
    configs.append((
        "http://localhost:8080/v1/chat/completions",
        {},
        "local-model",
        {},
        180
    ))
    
    from ux import InlineSpinner
    spinner = InlineSpinner()
    
    try:
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
                            if p:
                                log_file = os.path.join(CFG_DIR, ".request_log")
                                with open(log_file, "a") as lf:
                                    lf.write(f"{int(time.time())}|{p}\n")
                        except Exception:
                            pass
                            
                        first = True
                        acc = []
                        resolved_model = None
                        
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
                                if "model" in data and not resolved_model:
                                    resolved_model = data["model"]
                                    
                                content = ""
                                if "choices" in data and data["choices"]:
                                    content = data["choices"][0].get("delta", {}).get("content", "")
                                elif "candidates" in data and data["candidates"]:
                                    parts = data["candidates"][0].get("content", {}).get("parts", [{}])
                                    content = parts[0].get("text", "")
                                    
                                if content:
                                    if first:
                                        spinner.stop()
                                        if sys.stdout.isatty():
                                            sys.stdout.write(f"\r\x1b[2K\r\033[1;32m{prefix}\033[0m ")
                                            sys.stdout.flush()
                                        first = False
                                    print(content, end="", flush=True)
                                    acc.append(content)
                            except Exception:
                                pass
                                
                        print("")
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
        sys.stderr.write("\033[1;31mError: All fallbacks/local servers are offline.\033[0m\n\n")
    except KeyboardInterrupt:
        spinner.stop()
        sys.stderr.write("\n\r\x1b[2K\rCancelled.\n")
        sys.stderr.flush()
        sys.exit(130)
    return None


def run_interactive_flow(args: list):
    """Executes the interactive command finder selection carousel."""
    from ux import run_interactive_selection
    intent_str = " ".join(args[1:])
    run_interactive_selection(
        intent_str, 
        jaccard_search, 
        clean_tool_prefix, 
        print_stock_error, 
        ensure_mysys_exists
    )
    sys.exit(0)


def run_interactive_chat(args: list):
    """Executes the conversational shell interactive loop."""
    is_agent = (args[0] == "--talk-chat")
    active_skill = os.environ.get("AI_ACTIVE_SKILL")
    skills_list = []
    
    if active_skill:
        for s in active_skill.split():
            s_clean = s.lstrip("-").lower()
            if s_clean not in skills_list:
                skills_list.append(s_clean)
                
    for arg in args:
        if arg.startswith("-") and arg not in ("--talk", "--talk-chat"):
            s_clean = arg.lstrip("-").lower()
            if s_clean not in skills_list:
                skills_list.append(s_clean)

    skill_content_list = [load_skill_content(sk) for sk in skills_list]
    skill_content = "\n\n".join(filter(None, skill_content_list))
    
    if is_agent and skill_content:
        active_system_prompt = skill_content
    elif skill_content:
        active_system_prompt = BASE_PROMPT + f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n"
    else:
        active_system_prompt = BASE_PROMPT
        
    workspace_path = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    home_dir = os.path.expanduser("~")
    
    if workspace_path.startswith(home_dir):
        safe_name = workspace_path[len(home_dir):].lstrip("/")
    else:
        safe_name = workspace_path
        
    safe_name = safe_name.replace("/", "-").strip("-") or "home"
    
    chat_history = [{"role": "system", "content": active_system_prompt}]
    pending_query = " ".join(args[1:]) if len(args) > 1 else None
    clean_name = " ".join(skills_list)
    spell_active = True
    memory_active = True
    
    db_turns = 0
    if is_agent:
        try:
            count_script = os.path.join(CFG_DIR, "tools", "ai-agent-sessions")
            res = subprocess.run(
                [sys.executable, count_script, "get-count", safe_name],
                capture_output=True,
                text=True,
                check=False
            )
            db_turns = int(res.stdout.strip())
        except Exception:
            pass

    from ux import draw_session_box
    draw_session_box(workspace_path, home_dir, is_agent, db_turns, active_system_prompt, clean_name)

    try:
        while True:
            if pending_query:
                query = pending_query
                pending_query = None
            else:
                try:
                    raw_query = input("\x01\033[1;30m\x02❯\x01\033[0m\x02 ")
                except EOFError:
                    break
                finally:
                    try:
                        readline.set_startup_hook(None)
                    except Exception:
                        pass
                        
                if not raw_query.strip():
                    continue
                    
                query = raw_query.strip()
                if query.lower() in ("exit", "quit", "q"):
                    print("\r\033[1;33mExiting conversation.\033[0m")
                    sys.exit(0)
                if query.strip() in ("/d", "/e"):
                    spell_active = (query.strip() == "/e")
                    print(f"\033[1;33m[sys] Spellchecker {'enabled' if spell_active else 'disabled'}.\033[0m\n")
                    continue
                if query.strip() == "/m":
                    memory_active = not memory_active
                    print(f"\033[1;33m[sys] Memory recall {'enabled' if memory_active else 'disabled'}.\033[0m\n")
                    continue
                if query == "/tok":
                    tok_tool = os.path.join(CFG_DIR, "tools", "ai-agent-sessions")
                    subprocess.run([sys.executable, tok_tool, "show-tok"], input=json.dumps(chat_history), text=True, check=False)
                    continue

                if spell_active and not query.startswith(("/", "-", "#", "```")):
                    from ux import get_key
                    action, query = check_query_spelling(query, get_key)
                    if action == "EDIT":
                        try:
                            readline.set_startup_hook(lambda: readline.insert_text(query))
                        except Exception:
                            pass
                        continue
                    elif action == "DISABLE":
                        spell_active = False
            
            q_strip = query.strip()
            if q_strip in ("/skill", "/s") or q_strip.startswith(("/skill ", "/s ")):
                skill_tool = os.path.join(CFG_DIR, "tools", "ai-agent-skills")
                res = subprocess.run(
                    [sys.executable, skill_tool, safe_name, q_strip],
                    input=json.dumps(chat_history),
                    stdout=subprocess.PIPE,
                    text=True,
                    check=False
                )
                if res.stdout.strip():
                    try:
                        chat_history = json.loads(res.stdout.strip())
                    except Exception as e:
                        print(f"Error loading session: {e}")
                continue

            if query.startswith("-save"):
                tag = query.replace("-save", "").strip()
                save_tool = os.path.join(CFG_DIR, "tools", "ai-agent-sessions")
                subprocess.run([sys.executable, save_tool, "save", safe_name, tag], input=json.dumps(chat_history), text=True, check=False)
                continue
            
            if query in ("-load", "-timeline"):
                load_tool = os.path.join(CFG_DIR, "tools", "ai-agent-sessions")
                res = subprocess.run(
                    [sys.executable, load_tool, "load", safe_name],
                    stdin=sys.stdin,
                    stdout=subprocess.PIPE,
                    text=True,
                    check=False
                )
                if res.stdout.strip():
                    try:
                        chat_history = json.loads(res.stdout.strip())
                        print(f"\033[1;32m[session-mgr] Restored session ({len(chat_history)-1} turns loaded).\033[0m\n")
                    except Exception as e:
                        print(f"Error loading session: {e}")
                else:
                    print(f"\033[1;31m[session-mgr] Load aborted.\033[0m\n")
                continue

            past_memory = ""
            is_init_map = (
                query.startswith(("#", "[", "{")) or 
                "\n" in query.strip() or 
                "last_interaction_id" in query or 
                "index-map" in query
            )
            
            if is_agent and memory_active and not is_init_map:
                context_tool = os.path.join(CFG_DIR, "tools", "ai-agent-sessions")
                res = subprocess.run(
                    [sys.executable, context_tool, "get-context", safe_name, query],
                    stdout=subprocess.PIPE,
                    text=True,
                    check=False
                )
                if res.returncode == 2:
                    pending_query = None
                    continue
                if res.returncode == 3:
                    memory_active = False
                past_memory = res.stdout.strip()

            q_lower = query.lower().strip()
            cmd_match = re.match(r'^/?([ftba])(?:\s+(\d+))?$', q_lower)
            if cmd_match:
                think_bin = os.path.join(CFG_DIR, "tools", "chat")
                if os.path.exists(think_bin):
                    try:
                        subprocess.run([sys.executable, think_bin, query], input=json.dumps(chat_history), text=True, check=False)
                    except Exception as e:
                        sys.stderr.write(f"\033[1;31m[Warning] chat failed: {e}\033[0m\n")
                else:
                    sys.stderr.write("\033[1;31mError: chat tool not found\033[0m\n")
                continue
            
            if is_init_map:
                prompt = f"### SYSTEM INSTRUCTIONS (CRITICAL OVERRIDE):\n{active_system_prompt}\n\n### CODESPACE MAP:\n{query}"
            else:
                system_context = get_system_context(query)
                combined_context = (f"{past_memory}\n\n" if past_memory else "") + system_context
                prompt = (f"### Real-time System Context:\n{combined_context}\n\n" if combined_context else "") + f"User Question: {query}"
            
            chat_history.append({"role": "user", "content": prompt})
            if not is_init_map:
                try:
                    readline.add_history(query)
                except Exception:
                    pass
            from ux import prune_history
            pruned_history = prune_history(chat_history)
            ans = stream_llm_response(pruned_history, prefix="Agent:" if is_agent else "AI:")
            if ans: 
                chat_history.append({"role": "assistant", "content": ans})
                if is_agent:
                    log_tool = os.path.join(CFG_DIR, "tools", "ai-agent-sessions")
                    subprocess.run([sys.executable, log_tool, "log-turn", safe_name, query, ans], check=False)
                    if not is_init_map:
                        local_history_file = os.path.join(os.environ.get("AI_WORKSPACE_PATH", os.getcwd()), "history.md")
                        try:
                            mode = "a" if os.path.exists(local_history_file) else "w"
                            with open(local_history_file, mode, encoding="utf-8") as hf:
                                if mode == "w":
                                    hf.write(f"# Workspace History: {os.path.basename(os.path.dirname(local_history_file))}\n\n")
                                hf.write(f"## [{time.strftime('%Y-%m-%d %H:%M')}] User:\n{query}\n\n### Agent:\n{ans}\n\n---\n\n")
                        except Exception:
                            pass
    except KeyboardInterrupt: 
        print("\n\r\033[1;33mExiting conversation.\033[0m")
        sys.exit(0)


def run_direct_query(args: list):
    """Executes a direct shell query command without entering full chat loop."""
    query_parts = args[1:]
    active_system_prompt = BASE_PROMPT
    if query_parts and query_parts[-1].startswith("-"):
        skill_name = query_parts[-1].lstrip("-").lower()
        skill_content = load_skill_content(skill_name)
        if skill_content:
            active_system_prompt += f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n"
        query_parts = query_parts[:-1]
        
    query = " ".join(query_parts)
    system_context = get_system_context(query)
    messages = [
        {"role": "system", "content": active_system_prompt},
        {
            "role": "user", 
            "content": (f"### Real-time System Context:\n{system_context}\n\n" if system_context else "") + f"User Question: {query}"
        }
    ]
    stream_llm_response(messages, prefix="AI:")
    sys.exit(0)


def run_matching_search(args: list):
    """Handles single terminal queries, attempting local tool execution first."""
    user_input = sanitize_input(" ".join(args))
    if not user_input or args[0].startswith("--"):
        sys.exit(0)
    if re.search(r"[\[\]{}()='\",;|#<>]", user_input):
        print_stock_error(user_input)
        sys.exit(127)
    matched_base = jaccard_search(user_input)
    if matched_base:
        lines = []
        for line in matched_base.split("\n"):
            primary, cmd = line.split("|||", 1)
            lines.append(f"{primary}|||{clean_tool_prefix(cmd)}")
        print("\n".join(lines))
        sys.exit(0)
    print_stock_error(user_input)
    sys.exit(127)


def main():
    """Main program entry point orchestrating CLI args and flows."""
    try:
        args = sys.argv[1:]
        if args:
            if args[0] == "--interactive" and len(args) >= 2:
                run_interactive_flow(args)
                return

            if args[0] in ("--talk", "--talk-chat"):
                if args[0] == "--talk-chat" or len(args) == 1:
                    run_interactive_chat(args)
                else:
                    run_direct_query(args)
                return

            # Fallback to plain query/search execution
            run_matching_search(args)
    except KeyboardInterrupt:
        sys.stderr.write("\nCancelled.\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
