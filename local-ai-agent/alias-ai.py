#!/usr/bin/env python3
# Local-Ai Agent v0.8.3.3 [j5onrf] [06-12-26]

import sys, re, os, json, threading, time, math, subprocess, shutil
import urllib.request as urlreq, urllib.error as urlerr

try: import readline
except ImportError: pass

sys.argv = [arg for arg in sys.argv if arg != ""]

# Standard, unified absolute paths
CONTEXT_FILE = os.path.expanduser("~/.config/local-ai/local-ai-agent/ai-context.md")
INDEX_FILE = os.path.expanduser("~/.config/local-ai/local-ai-agent/ai-context.idx")
CFG_DIR = os.path.dirname(CONTEXT_FILE)

DESTRUCTIVE_KEYWORDS = ["rm ", "dd ", "mkfs", "shred", "chmod -R 777", "> /dev/sda"]
TOKEN_RE = re.compile(r"[^\w\s]")

STOP_WORDS = {"is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", "me", "you", "my", "your", "we", "us", "show", "get", "run", "check", "please", "can", "could", "would", "tell", "find", "list", "are", "about", "in", "next", "few", "days", "going", "soon", "anytime", "day", "week"}
UNIVERSAL_SYSTEM_KEYWORDS = {"system", "sys", "os", "linux", "kernel", "cpu", "gpu", "hardware", "motherboard", "memory", "ram", "storage", "disk", "drive", "nvme", "port", "network", "wifi", "ip", "dns", "log", "error", "specs", "hostname", "crash", "slow", "performance", "driver", "package", "status", "health", "window", "manager", "sddm", "gdm", "bootloader", "grub"}

class InlineSpinner:
    def __init__(self):
        self.chars, self.active, self.thread = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"], False, None

    def _spin(self):
        idx = 0
        while self.active:
            sys.stderr.write(f"\r\033[1;32m{self.chars[idx % 10]}\033[0m ")
            sys.stderr.flush()
            idx, _ = idx + 1, time.sleep(0.08)
        sys.stderr.write("\r\x1b[2K\r"); sys.stderr.flush()

    def start(self):
        self.active = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        self.active = False
        if self.thread: self.thread.join()

def sanitize_input(text):
    return re.sub(r"[`$]", "", text).strip() if text else ""

def tokenize(text):
    return [w for w in TOKEN_RE.sub(" ", text.lower()).split() if len(w) > 1 and w not in STOP_WORDS]

def get_active_system_keywords():
    keywords = set(UNIVERSAL_SYSTEM_KEYWORDS)
    p_path = os.path.join(CFG_DIR, "tools/skills/mysys.md")
    if os.path.exists(p_path):
        try:
            with open(p_path, "r") as f: keywords.update(t for t in tokenize(f.read()) if len(t) > 2)
        except: pass
    return keywords

def print_stock_error(cmd_name):
    shell = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    sys.stderr.write(f"zsh: command not found: {cmd_name}\n" if "zsh" in shell else f"bash: {cmd_name}: command not found\n")

def run_local_tool(cmd):
    cleaned_cmd = re.sub(r'\|\s*mdcat\b.*$', '', cmd.strip()).strip()
    try:
        out = subprocess.check_output(cleaned_cmd, shell=True, text=True, timeout=15).strip()
        return f"{out}\n" if out else "Action executed successfully.\n"
    except Exception as e:
        sys.stderr.write(f"\033[1;31mTool execution failed: {str(e)}\033[0m\n")
        return f"[SYSTEM ERROR] Failed to run local tool: {str(e)}\n"

def load_vector_index():
    if not os.path.exists(CONTEXT_FILE):
        sys.stderr.write(f"\n\033[1;31m[CRITICAL ERROR]: ai-context.md not found at: {CONTEXT_FILE}\033[0m\n")
        return {}, []
    try:
        if os.path.exists(INDEX_FILE) and os.path.getmtime(CONTEXT_FILE) <= os.path.getmtime(INDEX_FILE):
            with open(INDEX_FILE, "r") as f:
                data = json.load(f)
                if data.get("entries"):
                    return data.get("idfs", {}), data.get("entries", [])
    except:
        pass
    try:
        with open(CONTEXT_FILE, "r") as f: lines = f.read().splitlines()
        index_data = []
        for line in [l.strip() for l in lines if l.strip() and not l.startswith("#") and "--->" in l and "----->" not in l]:
            cmd, intents = line.split("----->" if "----->" in line else "--->", 1)
            intent_list = [i.strip() for i in intents.split(",")]
            primary_intent = intent_list[0] if intent_list else ""
            for intent in intent_list:
                tokens = tokenize(intent)
                if tokens: index_data.append({"cmd": cmd.strip(), "intent": intent, "primary": primary_intent, "tokens": tokens, "len": len(tokens)})
        from collections import defaultdict
        df = defaultdict(int)
        for entry in index_data:
            for t in set(entry["tokens"]): df[t] += 1
        idfs = {t: math.log(1.0 + (len(index_data) / count)) for t, count in df.items()}
        with open(INDEX_FILE, "w") as f: json.dump({"idfs": idfs, "entries": index_data}, f)
        return idfs, index_data
    except Exception as e:
        sys.stderr.write(f"\033[1;31mError compiling index: {str(e)}\033[0m\n")
        return {}, []

def check_danger(cmd):
    return f"DANGER_FLAGGED:{cmd}" if cmd and any(kw in cmd.lower() for kw in DESTRUCTIVE_KEYWORDS) else cmd

def matrix_search(query, threshold=0.55):
    query_tokens = tokenize(query)
    if not query_tokens: return None
    idfs, entries = load_vector_index()
    if not entries: return None
    candidates, q_set = [], set(query_tokens)
    for entry in entries:
        ent_tokens = entry.get("tokens", [])
        # Prefix Match Bypass
        if len(query_tokens) >= len(ent_tokens) and query_tokens[:len(ent_tokens)] == ent_tokens:
            candidates.append((2.0, entry["cmd"], entry.get("primary", entry["intent"])))
            continue
        intersect = q_set & set(ent_tokens)
        if not intersect or (len(query_tokens) == 1 and query_tokens[0] != entry["intent"].strip().lower()): continue
        match_weight = sum(idfs.get(t, 1.0) for t in intersect)
        q_weight = sum(idfs.get(t, 1.0) for t in q_set)
        entry_weight = sum(idfs.get(t, 1.0) for t in ent_tokens)
        score = (2.0 * match_weight) / (q_weight + entry_weight) if (q_weight + entry_weight) > 0 else 0.0
        if len(intersect) == len(ent_tokens) and (len(intersect) / len(q_set) >= 0.50): score += 0.20
        if score >= threshold: candidates.append((score, entry["cmd"], entry.get("primary", entry["intent"])))
    if not candidates: return None
    candidates.sort(key=lambda x: (-x[0], len(x[2])))
    seen, top = set(), []
    for _, cmd, primary in candidates:
        if cmd not in seen:
            seen.add(cmd); top.append(f"{primary}|||{check_danger(cmd)}")
            if len(top) == 3: break
    return "\n".join(top)

def get_key():
    import tty, termios, select
    fd = sys.stdin.fileno()
    try: old = termios.tcgetattr(fd)
    except termios.error:
        try: return os.read(fd, 1).decode("utf-8", errors="ignore")
        except: return ""
    try:
        tty.setraw(fd)
        r = os.read(fd, 1)
        if r == b'\x1b' and select.select([fd], [], [], 0.05)[0]: r += os.read(fd, 2)
    finally: termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return r.decode("utf-8", errors="ignore")

def clean_tool_prefix(cmd):
    is_tool = cmd.startswith("[TOOL]")
    cleaned = cmd.replace("[TOOL]", "", 1).strip() if is_tool else cmd
    if cleaned.startswith("DANGER_FLAGGED:"):
        inner = cleaned.replace("DANGER_FLAGGED:", "", 1)
        is_tool = inner.startswith("[TOOL]")
        cleaned = f"DANGER_FLAGGED:{inner.replace('[TOOL]', '', 1).strip()}" if is_tool else cleaned
    has_mdcat = bool(shutil.which("mdcat"))
    if is_tool:
        if "mdcat" not in cleaned: cleaned = f"{cleaned} | {'mdcat' if has_mdcat else 'cat'}"
    elif "mdcat" in cleaned and not has_mdcat:
        cleaned = re.sub(r'\|\s*mdcat\b.*$', '', cleaned).strip()
    return cleaned

def get_system_context(query):
    context, q_tokens = "", tokenize(query)
    if not q_tokens: return ""
    idfs, entries = load_vector_index()
    matched_cmd, matched_intent = None, None
    for entry in entries:
        ent_tokens = entry.get("tokens", [])
        if len(q_tokens) >= len(ent_tokens) and q_tokens[:len(ent_tokens)] == ent_tokens:
            matched_cmd, matched_intent = entry.get("cmd"), entry.get("intent")
            break
    if matched_cmd and matched_cmd.startswith("[TOOL]"):
        tool_cmd = matched_cmd.replace("[TOOL]", "").strip()
        intent_tokens = set(tokenize(matched_intent))
        args = " ".join([w for w in query.split() if tokenize(w) and tokenize(w)[0] not in intent_tokens])
        if args: tool_cmd = f"{tool_cmd} {args}"
        sys.stderr.write(f"\033[90m[sys] Executing: {tool_cmd}\033[0m\n"); sys.stderr.flush()
        context = run_local_tool(tool_cmd)
    if set(q_tokens) & get_active_system_keywords():
        profile_path = os.path.join(CFG_DIR, "tools/skills/mysys.md")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "r") as f: context = f.read().strip() + "\n\n" + context
            except: pass
    return context

def run_interactive_selection(intent):
    if re.search(r'[\[\]{}()=\'"",;|<>#]', intent):
        print_stock_error(intent); sys.exit(127)
    matched_base = matrix_search(intent)
    if not matched_base: print_stock_error(intent); sys.exit(127)
    options = matched_base.split("\n")
    num_opts, current_idx = len(options), 0
    sys.stderr.write("\033[?25l"); sys.stderr.flush()
    try:
        while True:
            entry = options[current_idx]
            current_intent, current_cmd = entry.split("|||", 1)
            display_idx, current_cmd = current_idx + 1, clean_tool_prefix(current_cmd)
            is_danger = current_cmd.startswith("DANGER_FLAGGED:")
            cmd_to_show = current_cmd.replace("DANGER_FLAGGED:", "") if is_danger else current_cmd
            display_cmd = cmd_to_show.replace(" >/dev/null 2>&1", "").replace(os.path.expanduser("~"), "~")
            idx_str = f"{display_idx:02d}/{num_opts:02d}"
            if is_danger:
                sys.stderr.write("\r\x1b[K\033[1;31m▲ WARNING: Destructive payload detected\033[0m\n")
                sys.stderr.write(f"\r\x1b[K\033[1;30m[\033[1;31m{idx_str}\033[1;30m]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n")
                sys.stderr.write("\r\x1b[K\033[1;30m::\033[0m execute payload? [y/N]: ")
            else:
                sys.stderr.write(f"\r\x1b[K\033[1;30m[\033[1;32m{idx_str}\033[1;30m]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n")
                sys.stderr.write("\r\x1b[K\033[1;30m::\033[0m ↵ run  any skip: ")
            sys.stderr.flush()
            key = get_key()
            if key in ('\x03', '\x1b') or (not is_danger and key not in ('\r', '', '\x1b[A', '\x1b[B')):
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n"); sys.stderr.flush(); break
            if is_danger:
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K"); sys.stderr.flush()
                if key.lower() == 'y': sys.stdout.write(cmd_to_show); sys.stdout.flush()
                else: sys.stderr.write("Aborted safely.\n")
                break
            if key in ('\r', ''): 
                # Cleanly advance cursor to a new line before executing confirmed commands
                sys.stderr.write("\n"); sys.stderr.flush()
                sys.stdout.write(cmd_to_show); sys.stdout.flush(); break
            elif key == '\x1b[A':
                current_idx = (current_idx - 1 + num_opts) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
            elif key == '\x1b[B':
                current_idx = (current_idx + 1) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
    finally: sys.stderr.write("\033[?25h"); sys.stderr.flush()

def stream_llm_response(messages, prefix="AI: "):
    configs = []
    gkey, okey = os.environ.get("GEMINI_API_KEY"), os.environ.get("OPENROUTER_API_KEY")
    if gkey:
        configs.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {"Content-Type": "application/json", "Authorization": f"Bearer {gkey}"}, os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite"), {}))
    if okey:
        m = os.environ.get("OPENROUTER_MODEL", "poolside/laguna-m.1:free")
        configs.append(("https://openrouter.ai/api/v1/chat/completions", {"Content-Type": "application/json", "Authorization": f"Bearer {okey}", "HTTP-Referer": "https://github.com/j5onrf/ai-suggestion"}, m, {"models": [m, "qwen/qwen3-coder:free", "openrouter/free"]}))
    ckey, curl = os.environ.get("CLOUD_API_KEY"), os.environ.get("CLOUD_API_URL")
    if ckey and curl:
        configs.append((curl, {"Content-Type": "application/json", "Authorization": f"Bearer {ckey}"}, os.environ.get("CLOUD_MODEL"), {}))
    configs.append(("http://localhost:8080/v1/chat/completions", {"Content-Type": "application/json"}, None, {}))

    spinner = InlineSpinner()
    for url, headers, model, extra in configs:
        body, retries, backoff_sec = {"messages": messages, "stream": True, **extra}, 2, 1.5
        if model: body["model"] = model
        req = urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        while retries >= 0:
            try:
                spinner.start()
                with urlreq.urlopen(req, timeout=10) as response:
                    first, acc = True, []
                    for line in response:
                        dec = line.decode("utf-8").strip()
                        if dec.startswith("data: "): dec = dec[6:].strip()
                        if not dec or dec == "[DONE]": continue
                        try:
                            data = json.loads(dec)
                            content = ""
                            if "choices" in data and data["choices"]: content = data["choices"][0].get("delta", {}).get("content", "")
                            elif "candidates" in data and data["candidates"]: content = data["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if content:
                                if first:
                                    spinner.stop()
                                    if sys.stdout.isatty():
                                        sys.stdout.write("\r\x1b[2K\r"); sys.stdout.flush()
                                        print(f"\033[1;32m{prefix}\033[0m ", end="", flush=True)
                                    first = False
                                print(content, end="", flush=True); acc.append(content)
                        except Exception: pass
                    print("\n"); return "".join(acc)
            except urlerr.HTTPError as e:
                spinner.stop()
                if e.code == 429 and retries > 0:
                    time.sleep(backoff_sec)
                    retries, backoff_sec = retries - 1, backoff_sec * 2
                    continue
                elif e.code == 400:
                    try: sys.stderr.write(f"\n\033[1;31m[API 400 Error]: {e.read().decode('utf-8')}\033[0m\n")
                    except: sys.stderr.write("\n\033[1;31m[API 400 Error]: Bad Request syntax or payload limit.\033[0m\n")
                    break
                else: break
            except Exception:
                spinner.stop()
                break
    print("\033[1;31mError: All fallbacks/local servers are offline.\033[0m\n")
    return None

if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
    if len(sys.argv) >= 3: run_interactive_selection(" ".join(sys.argv[2:]))
    sys.exit(0)

if len(sys.argv) > 1 and sys.argv[1] in ("--talk", "--talk-chat"):
    if sys.argv[1] == "--talk-chat" or len(sys.argv) == 2:
        is_agent = (sys.argv[1] == "--talk-chat")
        if is_agent:
            active_skill = os.environ.get("AI_ACTIVE_SKILL")
            print(f"\033[1;36mAI Agent Session Initialized | Context Loaded{f' [{active_skill}]' if active_skill else ''} | Ctrl+C to exit.\033[0m\n")
        else:
            print("\033[1;34mLocal AI Conversation Mode. Ctrl+C to quit.\033[0m\n")
        pending_query, chat_history = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None, []
        try:
            while True:
                if pending_query: query, pending_query = pending_query, None
                else:
                    try: raw_query = input("\033[1;30m❯\033[0m ")
                    except EOFError: break
                    if not raw_query.strip(): continue
                    query = raw_query.strip()
                    if query.lower() in ("exit", "quit", "q"):
                        print("\r\033[1;33mExiting conversation.\033[0m"); sys.exit(0)

                system_context = get_system_context(query)
                prompt = (
                    "You are a helpful, conversational local AI shell assistant with read-only terminal access.\n"
                    "Use the provided real-time system context (if available) to answer the user's question clearly, concisely, and directly.\n"
                    "Do not use markdown formatting like bold asterisks (**) or header hashes (#) in your response, as the output is rendered directly in a raw terminal.\n"
                    "Do not state that you cannot access their system, as the data has already been provided to you.\n\n"
                )
                if system_context: prompt += f"### Real-time System Context:\n{system_context}\n\n"
                prompt += f"User Question: {query}"
                chat_history.append({"role": "user", "content": prompt})

                ans = stream_llm_response(chat_history, prefix="Agent:" if is_agent else "AI:")
                if ans: chat_history.append({"role": "assistant", "content": ans})
                else: chat_history.pop()
        except KeyboardInterrupt:
            print("\n\r\033[1;33mExiting conversation.\033[0m"); sys.exit(0)

    elif len(sys.argv) > 2:
        query_parts = sys.argv[2:]
        system_context = ""
        SKILLS_DIR = os.path.join(CFG_DIR, "tools/skills")
        
        # Evaluate skills if the query or final parameter is formatted as a flag
        if query_parts and query_parts[-1].startswith("-"):
            skill_name = query_parts[-1].lstrip("-").lower()
            skill_file = os.path.join(SKILLS_DIR, f"{skill_name}.md")
            
            if os.path.exists(skill_file):
                try:
                    with open(skill_file, "r") as f: system_context = f.read().strip() + "\n\n"
                    query_parts = query_parts[:-1]
                except Exception as e:
                    sys.stderr.write(f"\033[1;31mError loading skill profile: {str(e)}\033[0m\n")

        query = " ".join(query_parts)
        system_context += get_system_context(query)
        prompt = (
            "You are a helpful, conversational local AI shell assistant with read-only terminal access.\n"
            "Use the provided real-time system context (if available) to answer the user's question clearly, concisely, and directly.\n"
            "Do not use markdown formatting like bold asterisks (**) or header hashes (#) in your response, as the output is rendered directly in a raw terminal.\n"
            "Do not state that you cannot access their system, as the data has already been provided to you.\n\n"
        )
        if system_context: prompt += f"### Real-time System Context:\n{system_context}\n\n"
        prompt += f"User Question: {query}"
        stream_llm_response([{"role": "user", "content": prompt}], prefix="AI:")
        sys.exit(0)

user_input = sanitize_input(" ".join(sys.argv[1:])) if len(sys.argv) > 1 else ""
if not user_input or sys.argv[1].startswith("--"): sys.exit(0)

if re.search(r'[\[\]{}()=\'"",;|<>#]', user_input):
    print_stock_error(user_input); sys.exit(127)

matched_base = matrix_search(user_input)
if matched_base:
    out_lines = []
    for line in matched_base.split("\n"):
        intent, cmd = line.split("|||", 1)
        is_tool = cmd.startswith("[TOOL]")
        cleaned_cmd = cmd.replace('[TOOL]', '', 1).strip() if is_tool else cmd
        has_mdcat = bool(shutil.which("mdcat"))
        if is_tool:
            if "mdcat" not in cleaned_cmd: cleaned_cmd = f"{cleaned_cmd} | {'mdcat' if has_mdcat else 'cat'}"
        else:
            if "mdcat" in cleaned_cmd and not has_mdcat:
                cleaned_cmd = re.sub(r'\|\s*mdcat\b.*$', '', cleaned_cmd).strip()
        out_lines.append(f"{intent}|||{cleaned_cmd}")
    print("\n".join(out_lines)); sys.exit(0)
else:
    print_stock_error(user_input); sys.exit(127)
