#!/usr/bin/env python3
# Local-Ai Agent v0.8.9.4 [j5onrf] [06-27-26]

import sys, re, os, json, select, subprocess, shutil
import urllib.request as urlreq, urllib.error as urlerr

sys.argv = [arg for arg in sys.argv if arg != ""]
CFG_DIR = os.path.expanduser("~/.config/local-ai")
CONTEXT_FILE, SKILLS_DIR = f"{CFG_DIR}/ai-context.md", f"{CFG_DIR}/skills"
DESTRUCTIVE_KEYWORDS = ["rm ", "dd ", "mkfs", "shred", "chmod -R 777", "> /dev/sda"]
TOKEN_RE, _CACHED_ENTRIES, _LAST_M_TIME = re.compile(r"[^\w\s]"), None, 0
STOP_WORDS = {"is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"}
BASE_PROMPT = "Local shell AI assistant (read-only access).\nProvide direct, natural plain-text answers using any provided system context.\nNo markdown (no bolding, no headers, no bullet lists).\nAlways write full, complete, and helpful sentences.\n\n"

# Bootstrap on-demand modules folder path
sys.path.append(os.path.join(CFG_DIR, "tools", "modules"))

check_query_spelling = lambda q, gk: ("RUN", q)
try:
    from spellcheck import check_query_spelling
except ImportError: pass

sanitize_input = lambda t: re.sub(r"[`$]", "", t).strip() if t else ""
tokenize = lambda t: [w for w in TOKEN_RE.sub(" ", t.lower()).split() if len(w) > 1 and w not in STOP_WORDS]
check_danger = lambda c: f"DANGER_FLAGGED:{c}" if c and any(kw in c.lower() for kw in DESTRUCTIVE_KEYWORDS) else c

def ensure_mysys_exists():
    if not os.path.exists(f"{SKILLS_DIR}/system/mysys.md"):
        try: subprocess.run([sys.executable, f"{CFG_DIR}/tools/generate-profile"])
        except Exception: pass

def find_skill_file(d, n):
    return next((os.path.join(r, f) for r, _, fs in os.walk(d) if r[len(d):].count(os.sep) <= 3 for f in fs if f.lower() == f"{n.lower()}.md"), None)

def load_skill_content(n):
    if not n: return ""
    skills = [s.lstrip("-").lower() for s in n.split()]
    contents = []
    for skill in skills:
        sf = find_skill_file(SKILLS_DIR, skill)
        if sf:
            if "system" in skill: ensure_mysys_exists()
            try:
                with open(sf, "r", encoding="utf-8") as f:
                    contents.append(f.read().strip())
            except Exception as e:
                sys.stderr.write(f"\033[1;31mError loading skill '{skill}': {e}\033[0m\n")
    return "\n\n".join(contents)

def print_stock_error(n):
    sh = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    sys.stderr.write(f"zsh: command not found: {n}\n" if "zsh" in sh else f"bash: {n}: command not found\n")

def run_local_tool(c):
    try:
        out = subprocess.check_output(re.sub(r'\|\s*(leaf|mdcat|cat|glow)\b.*$', '', c.strip()).strip(), shell=True, text=True, timeout=15, env={**os.environ, "AI_CONTEXT_RUN": "1"}).strip()
        return f"{out}\n" if out else "Action executed successfully.\n"
    except Exception as e: return f"[SYSTEM ERROR] Failed to run local tool: {e}\n"

def load_context_entries():
    global _CACHED_ENTRIES, _LAST_M_TIME
    if not os.path.exists(CONTEXT_FILE):
        sys.stderr.write(f"\n\033[1;31m[CRITICAL ERROR]: ai-context.md not found: {CONTEXT_FILE}\033[0m\n"); return []
    try:
        mtime = os.path.getmtime(CONTEXT_FILE)
        if _CACHED_ENTRIES is not None and mtime <= _LAST_M_TIME: return _CACHED_ENTRIES
        with open(CONTEXT_FILE) as f:
            lines = [s for l in f.read().splitlines() if (s := l.strip()) and not s.startswith("#") and "--->" in s]
        _CACHED_ENTRIES = []
        for line in lines:
            cmd, intents = line.split("--->", 1)
            intents = [i.strip() for i in intents.split(",") if i.strip()]
            for intent in intents:
                if tokens := tokenize(intent):
                    _CACHED_ENTRIES.append({"cmd": cmd.strip(), "intent": intent, "primary": intents[0], "tokens": tokens})
        _LAST_M_TIME = mtime
        return _CACHED_ENTRIES
    except: return []

def jaccard_search(query, threshold=0.45):
    q_clean, q_tokens = query.strip().lower(), set(tokenize(query))
    if not q_tokens or not (entries := load_context_entries()): return None
    candidates = []
    for entry in entries:
        ent_tokens, ent_clean = set(entry["tokens"]), entry["intent"].strip().lower()
        score = len(q_tokens & ent_tokens) / len(q_tokens | ent_tokens) if (q_tokens & ent_tokens) else 0.0
        if q_clean in ent_clean: score = max(score, 0.8)
        if q_clean == ent_clean: score = 3.0
        if score >= threshold: candidates.append((score, entry["cmd"], entry.get("primary", entry["intent"])))
    if not candidates: return None
    if any("system" in c[1].lower() for c in candidates): ensure_mysys_exists()
    candidates.sort(key=lambda x: (-x[0], len(x[2])))
    seen, top = set(), []
    for _, cmd, primary in candidates:
        if cmd not in seen and len(top) < 5:
            seen.add(cmd); top.append(f"{primary}|||{clean_tool_prefix(cmd)}")
    return "\n".join(top)

def clean_tool_prefix(cmd):
    is_tool = cmd.startswith("[TOOL]")
    c = cmd.replace("[TOOL]", "", 1).strip() if is_tool else cmd
    if c.startswith("DANGER_FLAGGED:"):
        c = f"DANGER_FLAGGED:{c.replace('DANGER_FLAGGED:', '').replace('[TOOL]', '').strip()}"
    c, pager = c.replace(" --s", "").strip(), ""
    for f, p in [(" --leaf", "leaf"), (" --glow", "glow"), (" --cat", "cat"), (" --mdcat", "mdcat")]:
        if c.endswith(f): c, pager = c[:-len(f)].strip(), p; break
    if not pager and is_tool: pager = "mdcat" if shutil.which("mdcat") else "cat"
    return f"{c} | {pager}" if pager and (pager != "mdcat" or shutil.which("mdcat")) else c

def get_system_context(query):
    q_tokens = tokenize(query)
    if not q_tokens or "\n" in query.strip(): return ""
    for entry in load_context_entries():
        ent_tokens = entry.get("tokens", [])
        if any(q_tokens[i:i+len(ent_tokens)] == ent_tokens for i in range(len(q_tokens) - len(ent_tokens) + 1)):
            cmd = entry.get("cmd", "")
            if cmd.startswith("[TOOL]"):
                tool = cmd.replace("[TOOL]", "").strip()
                if "system" in tool.lower(): ensure_mysys_exists()
                is_safe = " --s" in tool
                tool = tool.replace(" --s", "").strip()
                for f in [" --leaf", " --glow", " --cat", " --mdcat"]:
                    if tool.endswith(f): tool = tool[:-len(f)].strip()
                intent_tokens = set(tokenize(entry.get("intent", "")))
                args = " ".join([w for w in query.split() if tokenize(w) and tokenize(w)[0] not in intent_tokens])
                if "$1" in tool or "{}" in tool: tool = tool.replace("$1", args).replace("{}", args).strip()
                if is_safe:
                    sys.stderr.write(f"\033[2m[sys] Executing: {tool}\033[0m\n"); sys.stderr.flush()
                    return run_local_tool(tool)
                sys.stderr.write(f"\033[1;30m[sys] Run tool: \033[1;36m{tool}\033[1;30m? [↵ run  Esc]: \033[0m"); sys.stderr.flush()
                # On-demand import of key-handling module for system confirmation prompts
                from ux import get_key
                key = get_key()
                if key in ('\x03', '\x1b'):
                    sys.stderr.write("\r\x1b[K\033[2;31m[sys] Cancelled.\033[0m\n"); sys.stderr.flush(); sys.exit(130)
                is_run = key in ('\r', '\n', '', 'y', 'Y')
                sys.stderr.write(f"\r\x1b[K{f'\033[2m[sys] Executing: {tool}' if is_run else '\033[2;31m[sys] Skipped tool execution.'}\033[0m\n"); sys.stderr.flush()
                return run_local_tool(tool) if is_run else ""
        return ""

def stream_llm_response(messages, prefix="AI: "):
    gkey = os.environ.get("GEMINI_API_KEY")
    if gkey:
        try:
            import gemini_client
            # On-demand import of the CLI Spinner
            from ux import InlineSpinner
            ans = gemini_client.stream(messages, prefix, gkey, InlineSpinner)
            if ans is not None: return ans
        except: pass
    configs, okey = [], os.environ.get("OPENROUTER_API_KEY")
    if gkey:
        configs.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {"Authorization": f"Bearer {gkey}"}, os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite"), {}, 30))
    if okey:
        configs.append(("https://openrouter.ai/api/v1/chat/completions", {"Authorization": f"Bearer {okey}", "HTTP-Referer": "https://github.com/j5onrf/local-ai"}, os.environ.get("OPENROUTER_MODEL", "openrouter/free"), {}, 180))
    configs.append(("http://localhost:8080/v1/chat/completions", {}, "local-model", {}, 180))
    from ux import InlineSpinner
    spinner = InlineSpinner()
    try:
        for url, headers, model, extra, timeout in configs:
            body = {"messages": messages, "stream": True, **extra}
            if model: body["model"] = model
            req = urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", **headers}, method="POST")
            retries, backoff = 2, 1.5
            while retries >= 0:
                try:
                    spinner.start()
                    with urlreq.urlopen(req, timeout=timeout) as response:
                        try:
                            p = "gemini" if "generativelanguage" in url else "openrouter" if "openrouter" in url else None
                            if p: open(os.path.join(CFG_DIR, ".request_log"), "a").write(f"{int(time.time())}|{p}\n")
                        except: pass
                        first, acc, resolved_model = True, [], None
                        for line in response:
                            dec = line.decode("utf-8").strip()
                            if not dec: continue
                            if dec.startswith("data:"): dec = dec[5:].strip()
                            if dec == "[DONE]": continue
                            try:
                                data = json.loads(dec)
                                if "model" in data and not resolved_model: resolved_model = data["model"]
                                content = ""
                                if "choices" in data and data["choices"]: content = data["choices"][0].get("delta", {}).get("content", "")
                                elif "candidates" in data and data["candidates"]: content = data["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                                if content:
                                    if first:
                                        spinner.stop()
                                        if sys.stdout.isatty(): sys.stdout.write(f"\r\x1b[2K\r\033[1;32m{prefix}\033[0m "); sys.stdout.flush()
                                        first = False
                                    print(content, end="", flush=True); acc.append(content)
                            except: pass
                        print("")
                        if resolved_model and resolved_model != model and sys.stdout.isatty():
                            sys.stdout.write(f"\033[90m[via {resolved_model}]\033[0m\n"); sys.stdout.flush()
                        return "".join(acc)
                except urlerr.HTTPError as e:
                    spinner.stop()
                    if e.code == 429 and retries > 0: time.sleep(backoff); retries, backoff = retries - 1, backoff * 2
                    elif e.code == 400: sys.stderr.write(f"\n\033[1;31m[API 400 Error]: {e.read().decode('utf-8')}\033[0m\n"); break
                    else: sys.stderr.write(f"\033[90m[sys] {url.split('/')[2]} failed: HTTP {e.code}\033[0m\n"); break
                except Exception as e:
                    spinner.stop()
                    sys.stderr.write(f"\033[90m[sys] {url.split('/')[2]} failed: {e}\033[0m\n"); break
        sys.stderr.write("\033[1;31mError: All fallbacks/local servers are offline.\033[0m\n\n")
    except KeyboardInterrupt:
        spinner.stop(); sys.stderr.write("\n\r\x1b[2K\rCancelled.\n"); sys.stderr.flush(); sys.exit(130)
    return None

try:
    args = sys.argv[1:]
    if args:
        if args[0] == "--interactive" and len(args) >= 2:
            # On-demand import of Option Selection Carousel
            from ux import run_interactive_selection
            run_interactive_selection(" ".join(args[1:]), jaccard_search, clean_tool_prefix, print_stock_error, ensure_mysys_exists)
            sys.exit(0)

        if args[0] in ("--talk", "--talk-chat"):
            is_agent = (args[0] == "--talk-chat")
            if is_agent or len(args) == 1:
                active_skill = os.environ.get("AI_ACTIVE_SKILL")
                skills_list = []
                if active_skill:
                    for s in active_skill.split():
                        s_clean = s.lstrip("-").lower()
                        if s_clean not in skills_list: skills_list.append(s_clean)
                for arg in args:
                    if arg.startswith("-") and arg not in ("--talk", "--talk-chat"):
                        s_clean = arg.lstrip("-").lower()
                        if s_clean not in skills_list: skills_list.append(s_clean)

                skill_content_list = []
                for skill in skills_list:
                    content = load_skill_content(skill)
                    if content: skill_content_list.append(content)
                skill_content = "\n\n".join(skill_content_list)
                active_system_prompt = skill_content if (is_agent and skill_content) else (BASE_PROMPT + (f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n" if skill_content else ""))
                
                workspace_path = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
                home_dir = os.path.expanduser("~")
                safe_name = workspace_path[len(home_dir):].lstrip("/") if workspace_path.startswith(home_dir) else workspace_path
                safe_name = safe_name.replace("/", "-").strip("-") or "home"
                
                chat_history, loaded_skills = [{"role": "system", "content": active_system_prompt}], set(skills_list)
                pending_query, clean_name = (" ".join(args[1:]) if len(args) > 1 else None), (" ".join(skills_list))
                spell_active, memory_active = True, True
                
                db_turns = 0
                if is_agent:
                    try: db_turns = int(subprocess.run([sys.executable, f"{CFG_DIR}/tools/ai-agent-sessions", "get-count", safe_name], capture_output=True, text=True).stdout.strip())
                    except: pass

                # On-demand import and drawing of the Codex-style Info Box
                from ux import draw_session_box
                draw_session_box(workspace_path, home_dir, is_agent, db_turns, active_system_prompt, clean_name)

                try:
                    while True:
                        if pending_query: query, pending_query = pending_query, None
                        else:
                            try: raw_query = input("\x01\033[1;30m\x02❯\x01\033[0m\x02 ")
                            except EOFError: break
                            finally:
                                try: readline.set_startup_hook(None)
                                except: pass
                                
                            if not raw_query.strip(): continue
                            query = raw_query.strip()
                            if query.lower() in ("exit", "quit", "q"): 
                                print("\r\033[1;33mExiting conversation.\033[0m"); sys.exit(0)
                            if query.strip() in ("/d", "/e"):
                                spell_active = (query.strip() == "/e")
                                print(f"\033[1;33m[sys] Spellchecker {'enabled' if spell_active else 'disabled'}.\033[0m\n")
                                continue
                            if query.strip() == "/m":
                                memory_active = not memory_active
                                print(f"\033[1;33m[sys] Memory recall {'enabled' if memory_active else 'disabled'}.\033[0m\n")
                                continue
                            if query == "/tok":
                                subprocess.run([sys.executable, f"{CFG_DIR}/tools/ai-agent-sessions", "show-tok"], input=json.dumps(chat_history), text=True)
                                continue

                            if spell_active and not query.startswith(("/", "-", "#", "```")):
                                # On-demand key-handling for spellcheck checks
                                from ux import get_key
                                action, query = check_query_spelling(query, get_key)
                                if action == "EDIT":
                                    try: readline.set_startup_hook(lambda: readline.insert_text(query))
                                    except: pass
                                    continue
                                elif action == "DISABLE":
                                    spell_active = False
                        
                        q_strip = query.strip()
                        if q_strip in ("/skill", "/s") or q_strip.startswith(("/skill ", "/s ")):
                            res = subprocess.run([sys.executable, f"{CFG_DIR}/tools/ai-agent-skills", safe_name, q_strip], input=json.dumps(chat_history), stdout=subprocess.PIPE, text=True)
                            if res.stdout.strip():
                                try: chat_history = json.loads(res.stdout.strip())
                                except Exception as e: print(f"Error loading session: {e}")
                            continue

                        if query.startswith("-save"):
                            tag = query.replace("-save", "").strip()
                            subprocess.run([sys.executable, f"{CFG_DIR}/tools/ai-agent-sessions", "save", safe_name, tag], input=json.dumps(chat_history), text=True)
                            continue
                        
                        if query in ("-load", "-timeline"):
                            res = subprocess.run([sys.executable, f"{CFG_DIR}/tools/ai-agent-sessions", "load", safe_name], stdin=sys.stdin, stdout=subprocess.PIPE, text=True)
                            if res.stdout.strip():
                                try:
                                    chat_history = json.loads(res.stdout.strip())
                                    print(f"\033[1;32m[session-mgr] Restored session ({len(chat_history)-1} turns loaded).\033[0m\n")
                                except Exception as e: print(f"Error loading session: {e}")
                            else:
                                print(f"\033[1;31m[session-mgr] Load aborted.\033[0m\n")
                            continue

                        past_memory = ""
                        is_init_map = query.startswith(("#", "[", "{")) or "\n" in query.strip() or "last_interaction_id" in query or "index-map" in query
                        if is_agent and memory_active and not is_init_map:
                            res = subprocess.run([sys.executable, f"{CFG_DIR}/tools/ai-agent-sessions", "get-context", safe_name, query], stdout=subprocess.PIPE, text=True)
                            if res.returncode == 2:
                                pending_query = None
                                continue
                            if res.returncode == 3:
                                memory_active = False
                            past_memory = res.stdout.strip()

                        q_lower = query.lower().strip()
                        cmd_match = re.match(r'^/?([ftba])(?:\s+(\d+))?$', q_lower)
                        if cmd_match:
                            think_bin = f"{CFG_DIR}/tools/chat"
                            if os.path.exists(think_bin):
                                try: subprocess.run([sys.executable, think_bin, query], input=json.dumps(chat_history), text=True)
                                except Exception as e: sys.stderr.write(f"\033[1;31m[Warning] chat failed: {e}\033[0m\n")
                            else: sys.stderr.write("\033[1;31mError: chat tool not found\033[0m\n")
                            continue
                        
                        if is_init_map:
                            prompt = f"### SYSTEM INSTRUCTIONS (CRITICAL OVERRIDE):\n{active_system_prompt}\n\n### CODESPACE MAP:\n{query}"
                        else:
                            system_context = get_system_context(query)
                            combined_context = (f"{past_memory}\n\n" if past_memory else "") + system_context
                            prompt = (f"### Real-time System Context:\n{combined_context}\n\n" if combined_context else "") + f"User Question: {query}"
                        
                        chat_history.append({"role": "user", "content": prompt})
                        if not is_init_map:
                            try: readline.add_history(query)
                            except: pass
                        # On-demand import of context history pruner
                        from ux import prune_history
                        pruned_history = prune_history(chat_history)
                        ans = stream_llm_response(pruned_history, prefix="Agent:" if is_agent else "AI:")
                        if ans: 
                            chat_history.append({"role": "assistant", "content": ans})
                            if is_agent:
                                subprocess.run([sys.executable, f"{CFG_DIR}/tools/ai-agent-sessions", "log-turn", safe_name, query, ans])
                                if not is_init_map:
                                    local_history_file = os.path.join(os.environ.get("AI_WORKSPACE_PATH", os.getcwd()), "history.md")
                                    try:
                                        mode = "a" if os.path.exists(local_history_file) else "w"
                                        with open(local_history_file, mode) as hf:
                                            if mode == "w": hf.write(f"# Workspace History: {os.path.basename(os.path.dirname(local_history_file))}\n\n")
                                            hf.write(f"## [{time.strftime('%Y-%m-%d %H:%M')}] User:\n{query}\n\n### Agent:\n{ans}\n\n---\n\n")
                                    except Exception:
                                        pass
                except KeyboardInterrupt: 
                    print("\n\r\033[1;33mExiting conversation.\033[0m"); sys.exit(0)

            elif len(args) > 1:
                query_parts = args[1:]
                active_system_prompt = BASE_PROMPT
                if query_parts and query_parts[-1].startswith("-"):
                    skill_name = query_parts[-1].lstrip("-").lower()
                    skill_content = load_skill_content(skill_name)
                    if skill_content: active_system_prompt += f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n"
                    query_parts = query_parts[:-1]
                query = " ".join(query_parts)
                system_context = get_system_context(query)
                messages = [
                    {"role": "system", "content": active_system_prompt},
                    {"role": "user", "content": (f"### Real-time System Context:\n{system_context}\n\n" if system_context else "") + f"User Question: {query}"}
                ]
                stream_llm_response(messages, prefix="AI:")
                sys.exit(0)

        user_input = sanitize_input(" ".join(args))
        if not user_input or args[0].startswith("--"): sys.exit(0)
        if re.search(r"[\[\]{}()='\",;|#<>]", user_input): print_stock_error(user_input); sys.exit(127)
        matched_base = jaccard_search(user_input)
        if matched_base:
            print("\n".join(f"{line.split('|||', 1)[0]}|||{clean_tool_prefix(line.split('|||', 1)[1])}" for line in matched_base.split("\n")))
            sys.exit(0)
        print_stock_error(user_input); sys.exit(127)
except KeyboardInterrupt: sys.stderr.write("\nCancelled.\n"); sys.exit(130)
