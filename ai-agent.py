#!/usr/bin/env python3
# Local-Ai Agent v0.8.7.6 [j5onrf] [06-20-26]

import sys, re, os, json, threading, time, subprocess, shutil, tty, termios, select
import urllib.request as urlreq, urllib.error as urlerr

try: import readline
except ImportError: pass

sys.argv = [arg for arg in sys.argv if arg != ""]
CFG_DIR = os.path.expanduser("~/.config/local-ai")
CONTEXT_FILE, SKILLS_DIR = f"{CFG_DIR}/ai-context.md", f"{CFG_DIR}/skills"
DESTRUCTIVE_KEYWORDS, TOKEN_RE = ["rm ", "dd ", "mkfs", "shred", "chmod -R 777", "> /dev/sda"], re.compile(r"[^\w\s]")
STOP_WORDS = {"is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"}
_CACHED_ENTRIES, _LAST_M_TIME = None, 0
BASE_PROMPT = "Local shell AI assistant (read-only access).\nProvide direct, natural plain-text answers using any provided system context.\nNo markdown (no bolding, no headers, no bullet lists).\nAlways write full, complete, and helpful sentences.\n\n"

class InlineSpinner:
    def __init__(self): self.chars, self.active, self.thread = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", False, None
    def _spin(self):
        idx = 0
        while self.active:
            sys.stderr.write(f"\r\033[1;32m{self.chars[idx % 10]}\033[0m "); sys.stderr.flush()
            idx, _ = idx + 1, time.sleep(0.08)
        sys.stderr.write("\r\x1b[2K\r"); sys.stderr.flush()
    def start(self): self.active, self.thread = True, threading.Thread(target=self._spin, daemon=True); self.thread.start()
    def stop(self): self.active = False; self.thread.join() if self.thread else None

def sanitize_input(text): return re.sub(r"[`$]", "", text).strip() if text else ""
def tokenize(text): return [w for w in TOKEN_RE.sub(" ", text.lower()).split() if len(w) > 1 and w not in STOP_WORDS]
def check_danger(cmd): return f"DANGER_FLAGGED:{cmd}" if cmd and any(kw in cmd.lower() for kw in DESTRUCTIVE_KEYWORDS) else cmd

def ensure_mysys_exists():
    if not os.path.exists(f"{SKILLS_DIR}/system/mysys.md"):
        try: subprocess.run([sys.executable, f"{CFG_DIR}/tools/generate-profile"])
        except Exception: pass

def find_skill_file(skills_dir, name):
    for r, _, files in os.walk(skills_dir):
        if r[len(skills_dir):].count(os.sep) <= 3:
            for f in files:
                if f.lower() == f"{name.lower()}.md": return os.path.join(r, f)
    return None

def load_skill_content(skill_name):
    sf = find_skill_file(SKILLS_DIR, skill_name) if skill_name else None
    if not sf: return ""
    if "system" in skill_name.lower(): ensure_mysys_exists()
    try:
        with open(sf) as f: return f.read().strip()
    except Exception as e:
        sys.stderr.write(f"\033[1;31mError loading skill '{skill_name}': {e}\033[0m\n")
        return ""

def print_stock_error(n):
    sh = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    sys.stderr.write(f"zsh: command not found: {n}\n" if "zsh" in sh else f"bash: {n}: command not found\n")

def run_local_tool(cmd):
    try:
        env = {**os.environ, "AI_CONTEXT_RUN": "1"}
        out = subprocess.check_output(re.sub(r'\|\s*(leaf|mdcat|cat|glow)\b.*$', '', cmd.strip()).strip(), shell=True, text=True, timeout=15, env=env).strip()
        return f"{out}\n" if out else "Action executed successfully.\n"
    except Exception as e:
        return f"[SYSTEM ERROR] Failed to run local tool: {e}\n"

def load_context_entries():
    global _CACHED_ENTRIES, _LAST_M_TIME
    if not os.path.exists(CONTEXT_FILE):
        sys.stderr.write(f"\n\033[1;31m[CRITICAL ERROR]: ai-context.md not found: {CONTEXT_FILE}\033[0m\n"); return []
    try:
        mtime = os.path.getmtime(CONTEXT_FILE)
        if _CACHED_ENTRIES is not None and mtime <= _LAST_M_TIME: return _CACHED_ENTRIES
        with open(CONTEXT_FILE) as f:
            lines = [s for l in f.read().splitlines() if (s := l.strip()) and not s.startswith("#") and "--->" in s]
        entries = []
        for line in lines:
            cmd, intents = line.split("--->", 1)
            intent_list = [i.strip() for i in intents.split(",") if i.strip()]
            primary = intent_list[0] if intent_list else ""
            for intent in intent_list:
                if tokens := tokenize(intent):
                    entries.append({"cmd": cmd.strip(), "intent": intent, "primary": primary, "tokens": tokens})
        _CACHED_ENTRIES, _LAST_M_TIME = entries, mtime
        return entries
    except Exception: return []

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
        if cmd not in seen:
            seen.add(cmd); top.append(f"{primary}|||{clean_tool_prefix(cmd)}")
            if len(top) >= 5: break
    return "\n".join(top)

def get_key():
    fd = sys.stdin.fileno()
    try: old = termios.tcgetattr(fd)
    except termios.error:
        try: return os.read(fd, 1).decode("utf-8", errors="ignore")
        except: return ""
    try:
        tty.setraw(fd); r = os.read(fd, 1)
        if r == b'\x1b' and select.select([fd], [], [], 0.05)[0]: r += os.read(fd, 2)
    finally: termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return r.decode("utf-8", errors="ignore")

def clean_tool_prefix(cmd):
    is_tool = cmd.startswith("[TOOL]")
    c = cmd.replace("[TOOL]", "", 1).strip() if is_tool else cmd
    if c.startswith("DANGER_FLAGGED:"):
        c = f"DANGER_FLAGGED:{c.replace('DANGER_FLAGGED:', '').replace('[TOOL]', '').strip()}"
    c = c.replace(" --s", "").strip()
    pager = ""
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
                if is_safe: tool = tool.replace(" --s", "").strip()
                for f in [" --leaf", " --glow", " --cat", " --mdcat"]:
                    if tool.endswith(f): tool = tool[:-len(f)].strip()
                intent_tokens = set(tokenize(entry.get("intent", "")))
                args = " ".join([w for w in query.split() if tokenize(w) and tokenize(w)[0] not in intent_tokens])
                if "$1" in tool or "{}" in tool:
                    tool = tool.replace("$1", args).replace("{}", args).strip()
                if is_safe:
                    sys.stderr.write(f"\033[2m[sys] Executing: {tool}\033[0m\n"); sys.stderr.flush()
                    return run_local_tool(tool)
                
                sys.stderr.write(f"\033[1;30m[sys] Run tool: \033[1;36m{tool}\033[1;30m? [↵ run  Esc]: \033[0m"); sys.stderr.flush()
                key = get_key()
                if key in ('\x03', '\x1b'):
                    sys.stderr.write("\r\x1b[K\033[2;31m[sys] Cancelled.\033[0m\n"); sys.stderr.flush(); sys.exit(130)
                is_run = key in ('\r', '\n', '', 'y', 'Y')
                msg = f"\033[2m[sys] Executing: {tool}" if is_run else "\033[2;31m[sys] Skipped tool execution."
                sys.stderr.write(f"\r\x1b[K{msg}\033[0m\n"); sys.stderr.flush()
                return run_local_tool(tool) if is_run else ""
    return ""

def run_interactive_selection(intent):
    if re.search(r'[\[\]{}()=\'"",;|<>#]', intent): print_stock_error(intent); sys.exit(127)
    matched_base = jaccard_search(intent)
    if not matched_base: print_stock_error(intent); sys.exit(127)
    options = matched_base.split("\n")
    num_opts, current_idx = len(options), 0
    sys.stderr.write("\033[?25l"); sys.stderr.flush()
    try:
        while True:
            current_intent, current_cmd = options[current_idx].split("|||", 1)
            current_cmd = clean_tool_prefix(current_cmd)
            is_danger = current_cmd.startswith("DANGER_FLAGGED:")
            cmd_to_show = current_cmd.replace("DANGER_FLAGGED:", "")
            display_cmd = cmd_to_show.replace(" >/dev/null 2>&1", "").replace(os.path.expanduser("~"), "~")
            idx_str = f"{current_idx + 1:02d}/{num_opts:02d}"
            if is_danger:
                sys.stderr.write(f"\r\x1b[K\033[1;31m▲ WARNING: Destructive payload detected\033[0m\n\r\x1b[K\033[1;30m[\033[1;31m{idx_str}\033[1;30m]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n\r\x1b[K\033[1;30m::\033[0m execute payload? [y/N]: ")
            else:
                sys.stderr.write(f"\r\x1b[K\033[1;30m[\033[1;32m{idx_str}\033[1;30m]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n\r\x1b[K\033[1;30m::\033[0m ↵ run  Esc: ")
            sys.stderr.flush()
            key = get_key()
            if key in ('\x03', '\x1b') or (not is_danger and key not in ('\r', '', '\x1b[A', '\x1b[B')):
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n"); sys.stderr.flush(); break
            if is_danger:
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K"); sys.stderr.flush()
                if key.lower() == 'y':
                    if "system" in cmd_to_show: ensure_mysys_exists()
                    sys.stdout.write(cmd_to_show)
                else: sys.stderr.write("Aborted safely.\n")
                sys.stdout.flush(); break
            if key in ('\r', ''):
                sys.stderr.write("\n"); sys.stderr.flush()
                if "system" in cmd_to_show: ensure_mysys_exists()
                sys.stdout.write(cmd_to_show); sys.stdout.flush(); break
            elif key in ('\x1b[A', '\x1b[B'):
                current_idx = (current_idx + (1 if key == '\x1b[B' else -1) + num_opts) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
    except KeyboardInterrupt:
        sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n"); sys.stderr.flush(); sys.exit(130)
    finally: sys.stderr.write("\033[?25h"); sys.stderr.flush()

def stream_llm_response(messages, prefix="AI: "):
    configs, gkey, okey, ckey, curl = [], os.environ.get("GEMINI_API_KEY"), os.environ.get("OPENROUTER_API_KEY"), os.environ.get("CLOUD_API_KEY"), os.environ.get("CLOUD_API_URL")
    if gkey: 
        configs.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {"Authorization": f"Bearer {gkey}"}, os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite"), {}, 15))
    if okey:
        m = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
        configs.append(("https://openrouter.ai/api/v1/chat/completions", {"Authorization": f"Bearer {okey}", "HTTP-Referer": "https://github.com/j5onrf/local-ai"}, m, {}, 20))
    if ckey and curl: 
        configs.append((curl, {"Authorization": f"Bearer {ckey}"}, os.environ.get("CLOUD_MODEL"), {}, 30))
    configs.append(("http://localhost:8080/v1/chat/completions", {}, "local-model", {}, 180))
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
                            p and open(os.path.join(CFG_DIR, ".request_log"), "a").write(f"{int(time.time())}|{p}\n")
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
                                        if sys.stdout.isatty():
                                            sys.stdout.write("\r\x1b[2K\r\033[1;32m" + prefix + "\033[0m ")
                                            sys.stdout.flush()
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
                    elif e.code == 400:
                        sys.stderr.write(f"\n\033[1;31m[API 400 Error]: {e.read().decode('utf-8')}\033[0m\n"); break
                    else:
                        sys.stderr.write(f"\033[90m[sys] {url.split('/')[2]} failed: HTTP {e.code}\033[0m\n")
                        break
                except Exception as e:
                    spinner.stop()
                    sys.stderr.write(f"\033[90m[sys] {url.split('/')[2]} failed: {e}\033[0m\n")
                    break
    except KeyboardInterrupt:
        spinner.stop(); sys.stderr.write("\n\r\x1b[2K\rCancelled.\n"); sys.stderr.flush(); sys.exit(130)
    sys.stderr.write("\033[1;31mError: All fallbacks/local servers are offline.\033[0m\n\n"); return None

try:
    args = sys.argv[1:]
    if args:
        if args[0] == "--interactive":
            if len(args) >= 2: run_interactive_selection(" ".join(args[1:]))
            sys.exit(0)

        if args[0] in ("--talk", "--talk-chat"):
            is_agent = (args[0] == "--talk-chat")
            if is_agent or len(args) == 1:
                active_skill = os.environ.get("AI_ACTIVE_SKILL")
                skill_content = load_skill_content(active_skill.lstrip("-")) if active_skill else ""
                active_system_prompt = BASE_PROMPT
                if skill_content: active_system_prompt += f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n"
                clean_name = active_skill.lstrip("-") if active_skill else ""
                print(f"\033[1;36mAI Agent Session Initialized | Context Loaded{f' [{clean_name}]' if clean_name else ''} | Ctrl+C to exit.\033[0m\n" if is_agent else "\033[1;34mLocal AI Conversation Mode. Ctrl+C to quit.\033[0m\n")
                pending_query, chat_history = " ".join(args[1:]) if len(args) > 1 else None, [{"role": "system", "content": active_system_prompt}]
                try:
                    while True:
                        if pending_query: query, pending_query = pending_query, None
                        else:
                            try: raw_query = input("\033[1;30m❯\033[0m ")
                            except EOFError: break
                            if not raw_query.strip(): continue
                            query = raw_query.strip()
                            if query.lower() in ("exit", "quit", "q"): print("\r\033[1;33mExiting conversation.\033[0m"); sys.exit(0)
                        q_lower = query.lower().strip()
                        cmd_match = re.match(r'^/?([ftba])(?:\s+(\d+))?$', q_lower)
                        if cmd_match:
                            think_bin = f"{CFG_DIR}/tools/chat"
                            if os.path.exists(think_bin):
                                try: subprocess.run([sys.executable, think_bin, query], input=json.dumps(chat_history), text=True)
                                except Exception as e: sys.stderr.write(f"\033[1;31m[Warning] chat tool failed: {e}\033[0m\n")
                            else: sys.stderr.write("\033[1;31mError: chat tool not found at tools/chat\033[0m\n")
                            continue
                        system_context = get_system_context(query)
                        prompt = (f"### Real-time System Context:\n{system_context}\n\n" if system_context else "") + f"User Question: {query}"
                        chat_history.append({"role": "user", "content": prompt})
                        try: readline.add_history(query)
                        except: pass
                        ans = stream_llm_response(chat_history, prefix="Agent:" if is_agent else "AI:")
                        if ans: chat_history.append({"role": "assistant", "content": ans})
                except KeyboardInterrupt: print("\n\r\033[1;33mExiting conversation.\033[0m"); sys.exit(0)

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
