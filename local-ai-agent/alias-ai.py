#!/usr/bin/env python3
# Local-Ai Agent v0.8.3.9 [j5onrf] [06-14-26]

import sys, re, os, json, threading, time, math, subprocess, shutil
import urllib.request as urlreq, urllib.error as urlerr

try: import readline
except ImportError: pass

sys.argv = [arg for arg in sys.argv if arg != ""]

# Standard, unified absolute paths (Updated to point to root skills folder)
CONTEXT_FILE = os.path.expanduser("~/.config/local-ai/local-ai-agent/ai-context.md")
INDEX_FILE = os.path.expanduser("~/.config/local-ai/local-ai-agent/ai-context.idx")
CFG_DIR = os.path.dirname(CONTEXT_FILE)
MYSYS_FILE = os.path.join(CFG_DIR, "skills/system/mysys.md")
SKILLS_DIR = os.path.join(CFG_DIR, "skills")

DESTRUCTIVE_KEYWORDS = ["rm ", "dd ", "mkfs", "shred", "chmod -R 777", "> /dev/sda"]
TOKEN_RE = re.compile(r"[^\w\s]")
STOP_WORDS = {"is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", "me", "you", "my", "your", "we", "us", "show", "get", "run", "check", "please", "can", "could", "would", "tell", "find", "list", "are", "about", "in", "next", "few", "days", "going", "soon", "anytime", "day", "week"}

BASE_PROMPT = (
    "You are a helpful, conversational local AI shell assistant with read-only terminal access.\n"
    "Use the provided real-time system context (if available) to answer the user's question clearly, concisely, and directly.\n"
    "Do not use markdown formatting like bold asterisks (**) or header hashes (#) in your response, as the output is rendered directly in a raw terminal.\n"
    "Do not state that you cannot access their system, as the data has already been provided to you.\n\n"
)

class InlineSpinner:
    def __init__(self):
        self.chars, self.active, self.thread = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"], False, None

    def _spin(self):
        idx = 0
        while self.active:
            sys.stderr.write(f"\r\033[1;32m{self.chars[idx % 10]}\033[0m ")
            sys.stderr.flush(); idx, _ = idx + 1, time.sleep(0.08)
        sys.stderr.write("\r\x1b[2K\r"); sys.stderr.flush()

    def start(self):
        self.active, self.thread = True, threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        self.active = False

def sanitize_input(text):
    return re.sub(r"[`$]", "", text).strip() if text else ""

def tokenize(text):
    return [w for w in TOKEN_RE.sub(" ", text.lower()).split() if len(w) > 1 and w not in STOP_WORDS]

def ensure_mysys_exists():
    if not os.path.exists(MYSYS_FILE):
        p = os.path.join(CFG_DIR, "tools/generate-profile")
        if os.path.exists(p):
            try: subprocess.run([p], check=True)
            except Exception as e: sys.stderr.write(f"\033[1;31m[Warning] Failed to lazy-generate system profile: {e}\033[0m\n")

def find_skill_file(skills_dir, skill_name, max_depth=3):
    target = f"{skill_name.lower()}.md"
    for root, _, files in os.walk(skills_dir):
        if root.replace(skills_dir, "").count(os.sep) <= max_depth:
            if target in (f.lower() for f in files): return os.path.join(root, target)
    return None

def print_stock_error(cmd_name):
    shell = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    sys.stderr.write(f"zsh: command not found: {cmd_name}\n" if "zsh" in shell else f"bash: {cmd_name}: command not found\n")

def run_local_tool(cmd):
    cleaned = re.sub(r'\|\s*(leaf|mdcat|cat)\b.*$', '', cmd.strip()).strip()
    try:
        env_copy = os.environ.copy(); env_copy["AI_CONTEXT_RUN"] = "1"
        out = subprocess.check_output(cleaned, shell=True, text=True, timeout=15, env=env_copy).strip()
        return f"{out}\n" if out else "Action executed successfully.\n"
    except Exception as e:
        sys.stderr.write(f"\033[1;31mTool execution failed: {e}\033[0m\n")
        return f"[SYSTEM ERROR] Failed to run local tool: {e}\n"

def load_vector_index():
    if not os.path.exists(CONTEXT_FILE):
        sys.stderr.write(f"\n\033[1;31m[CRITICAL ERROR]: ai-context.md not found at: {CONTEXT_FILE}\033[0m\n"); return {}, []
    try:
        if os.path.exists(INDEX_FILE) and os.path.getmtime(CONTEXT_FILE) <= os.path.getmtime(INDEX_FILE):
            with open(INDEX_FILE) as f:
                data = json.load(f)
                return data.get("idfs", {}), data.get("entries", [])
    except: pass
    try:
        with open(CONTEXT_FILE) as f: lines = f.read().splitlines()
        index_data = []
        for line in [l.strip() for l in lines if l.strip() and not l.startswith("#") and "----->" not in l and "--->" in l]:
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
        sys.stderr.write(f"\033[1;31mError compiling index: {e}\033[0m\n"); return {}, []

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
            if len(top) == 5: break
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
        # Optimized: skip mdcat if standard cat is explicitly piped
        if "mdcat" not in cleaned and "cat" not in cleaned: cleaned = f"{cleaned} | {'mdcat' if has_mdcat else 'cat'}"
    elif "mdcat" in cleaned and not has_mdcat:
        cleaned = re.sub(r'\|\s*mdcat\b.*$', '', cleaned).strip()
    return cleaned

def get_system_context(query):
    context, q_tokens = "", tokenize(query)
    if not q_tokens or "\n" in query.strip(): return ""
    idfs, entries = load_vector_index()
    for entry in entries:
        ent_tokens = entry.get("tokens", [])
        if len(q_tokens) >= len(ent_tokens) and q_tokens[:len(ent_tokens)] == ent_tokens:
            matched_cmd, matched_intent = entry.get("cmd"), entry.get("intent")
            if matched_cmd and matched_cmd.startswith("[TOOL]"):
                tool_cmd = matched_cmd.replace("[TOOL]", "").strip()
                if "tools/agentic/" in tool_cmd: ensure_mysys_exists()
                intent_tokens = set(tokenize(matched_intent))
                args = " ".join([w for w in query.split() if tokenize(w) and tokenize(w)[0] not in intent_tokens])
                if args: tool_cmd = f"{tool_cmd} {args}"
                sys.stderr.write(f"\033[90m[sys] Executing: {tool_cmd}\033[0m\n"); sys.stderr.flush()
                return run_local_tool(tool_cmd)
    return ""

def run_interactive_selection(intent):
    if re.search(r'[\[\]{}()=\'"",;|<>#]', intent): print_stock_error(intent); sys.exit(127)
    matched_base = matrix_search(intent)
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
                sys.stderr.write(f"\r\x1b[K\033[1;30m[\033[1;32m{idx_str}\033[1;30m]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n\r\x1b[K\033[1;30m::\033[0m ↵ run  any skip: ")
            sys.stderr.flush()
            key = get_key()
            if key in ('\x03', '\x1b') or (not is_danger and key not in ('\r', '', '\x1b[A', '\x1b[B')):
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n"); sys.stderr.flush(); break
            if is_danger:
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K"); sys.stderr.flush()
                if key.lower() == 'y':
                    if "tools/agentic/" in cmd_to_show: ensure_mysys_exists()
                    sys.stdout.write(cmd_to_show); sys.stdout.flush()
                else: sys.stderr.write("Aborted safely.\n")
                break
            if key in ('\r', ''):
                sys.stderr.write("\n"); sys.stderr.flush()
                if "tools/agentic/" in cmd_to_show: ensure_mysys_exists()
                sys.stdout.write(cmd_to_show); sys.stdout.flush(); break
            elif key in ('\x1b[A', '\x1b[B'):
                current_idx = (current_idx + (1 if key == '\x1b[B' else -1) + num_opts) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
    except KeyboardInterrupt:
        sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n"); sys.stderr.flush(); sys.exit(130)
    finally: sys.stderr.write("\033[?25h"); sys.stderr.flush()

def stream_llm_response(messages, prefix="AI: "):
    configs, gkey, okey, ckey, curl = [], os.environ.get("GEMINI_API_KEY"), os.environ.get("OPENROUTER_API_KEY"), os.environ.get("CLOUD_API_KEY"), os.environ.get("CLOUD_API_URL")
    if gkey: configs.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {"Content-Type": "application/json", "Authorization": f"Bearer {gkey}"}, os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite"), {}))
    if okey:
        m = os.environ.get("OPENROUTER_MODEL", "poolside/laguna-m.1:free")
        configs.append(("https://openrouter.ai/api/v1/chat/completions", {"Content-Type": "application/json", "Authorization": f"Bearer {okey}", "HTTP-Referer": "https://github.com/j5onrf/ai-suggestion"}, m, {"models": [m, "qwen/qwen3-coder:free", "openrouter/free"]}))
    if ckey and curl: configs.append((curl, {"Content-Type": "application/json", "Authorization": f"Bearer {ckey}"}, os.environ.get("CLOUD_MODEL"), {}))
    configs.append(("http://localhost:8080/v1/chat/completions", {"Content-Type": "application/json"}, None, {}))
    spinner = InlineSpinner()
    try:
        for url, headers, model, extra in configs:
            body = {"messages": messages, "stream": True, **extra}
            if model: body["model"] = model
            req = urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
            retries, backoff = 2, 1.5
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
                                            sys.stdout.write("\r\x1b[2K\r\033[1;32m" + prefix + "\033[0m ")
                                            sys.stdout.flush()
                                        first = False
                                    print(content, end="", flush=True); acc.append(content)
                            except: pass
                        print("\n"); return "".join(acc)
                except urlerr.HTTPError as e:
                    spinner.stop()
                    if e.code == 429 and retries > 0:
                        time.sleep(backoff); retries, backoff = retries - 1, backoff * 2
                    elif e.code == 400:
                        try: sys.stderr.write(f"\n\033[1;31m[API 400 Error]: {e.read().decode('utf-8')}\033[0m\n")
                        except: sys.stderr.write("\n\033[1;31m[API 400 Error]: Bad Request syntax or payload limit.\033[0m\n")
                        break
                    else: break
                except Exception: spinner.stop(); break
    except KeyboardInterrupt:
        spinner.stop(); sys.stderr.write("\n\r\x1b[2K\rCancelled.\n"); sys.stderr.flush(); sys.exit(130)
    print("\033[1;31mError: All fallbacks/local servers are offline.\033[0m\n"); return None

try:
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        if len(sys.argv) >= 3: run_interactive_selection(" ".join(sys.argv[2:]))
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] in ("--talk", "--talk-chat"):
        is_agent = (sys.argv[1] == "--talk-chat")
        if is_agent or len(sys.argv) == 2:
            active_skill = os.environ.get("AI_ACTIVE_SKILL")
            if active_skill:
                skill_file = find_skill_file(SKILLS_DIR, active_skill.lstrip("-"))
                if skill_file and "skills/system/" in skill_file.replace("\\", "/"): ensure_mysys_exists()
            clean_name = active_skill.lstrip("-") if active_skill else ""
            print(f"\033[1;36mAI Agent Session Initialized | Context Loaded{f' [{clean_name}]' if clean_name else ''} | Ctrl+C to exit.\033[0m\n" if is_agent else "\033[1;34mLocal AI Conversation Mode. Ctrl+C to quit.\033[0m\n")
            pending_query, chat_history = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None, []
            try:
                while True:
                    if pending_query: query, pending_query = pending_query, None
                    else:
                        try: raw_query = input("\033[1;30m❯\033[0m ")
                        except EOFError: break
                        if not raw_query.strip(): continue
                        query = raw_query.strip()
                        if query.lower() in ("exit", "quit", "q"): print("\r\033[1;33mExiting conversation.\033[0m"); sys.exit(0)
                    system_context = get_system_context(query)
                    prompt = BASE_PROMPT + (f"### Real-time System Context:\n{system_context}\n\n" if system_context else "") + f"User Question: {query}"
                    chat_history.append({"role": "user", "content": prompt})
                    ans = stream_llm_response(chat_history, prefix="Agent:" if is_agent else "AI:")
                    if ans: chat_history.append({"role": "assistant", "content": ans})
                    else: chat_history.pop()
            except KeyboardInterrupt:
                print("\n\r\033[1;33mExiting conversation.\033[0m"); sys.exit(0)

        elif len(sys.argv) > 2:
            query_parts = sys.argv[2:]
            system_context = ""
            if query_parts and query_parts[-1].startswith("-"):
                skill_file = find_skill_file(SKILLS_DIR, query_parts[-1].lstrip("-").lower())
                if skill_file:
                    if "skills/system/" in skill_file.replace("\\", "/"): ensure_mysys_exists()
                    try:
                        with open(skill_file) as f: system_context = f.read().strip() + "\n\n"
                        query_parts = query_parts[:-1]
                    except Exception as e: sys.stderr.write(f"\033[1;31mError loading skill: {e}\033[0m\n")
            query = " ".join(query_parts)
            system_context += get_system_context(query)
            prompt = BASE_PROMPT + (f"### Real-time System Context:\n{system_context}\n\n" if system_context else "") + f"User Question: {query}"
            stream_llm_response([{"role": "user", "content": prompt}], prefix="AI:")
            sys.exit(0)

    user_input = sanitize_input(" ".join(sys.argv[1:])) if len(sys.argv) > 1 else ""
    if not user_input or sys.argv[1].startswith("--"): sys.exit(0)
    if re.search(r'[\[\]{}()=\'"",;|<>#]', user_input): print_stock_error(user_input); sys.exit(127)
    matched_base = matrix_search(user_input)
    if matched_base:
        out_lines = []
        for line in matched_base.split("\n"):
            intent, cmd = line.split("|||", 1)
            is_tool = cmd.startswith("[TOOL]")
            cleaned = cmd.replace('[TOOL]', '', 1).strip() if is_tool else cmd
            has_mdcat = bool(shutil.which("mdcat"))
            # Skip auto-appending mdcat if standard cat is explicitly piped in the command
            if is_tool and "mdcat" not in cleaned and "cat" not in cleaned: cleaned = f"{cleaned} | {'mdcat' if has_mdcat else 'cat'}"
            elif not is_tool and "mdcat" in cleaned and not has_mdcat: cleaned = re.sub(r'\|\s*mdcat\b.*$', '', cleaned).strip()
            out_lines.append(f"{intent}|||{cleaned}")
        print("\n".join(out_lines)); sys.exit(0)
    else: print_stock_error(user_input); sys.exit(127)
except KeyboardInterrupt:
    sys.stderr.write("\nCancelled.\n"); sys.exit(130)
