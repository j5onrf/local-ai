#!/usr/bin/env python3
# Local-Ai Agent v0.8.1.4 [j5onrf] [06-12-26]

import sys, re, os, json, threading, time, math, subprocess, shutil
import urllib.request as urlreq

try:
    import readline
except ImportError:
    pass

sys.argv = [arg for arg in sys.argv if arg != ""]

CONTEXT_FILE = os.path.expanduser("~/.config/local-ai/local-ai-agent/ai-context.txt")
INDEX_FILE = os.path.expanduser("~/.config/local-ai/local-ai-agent/ai-context.idx")
DESTRUCTIVE_KEYWORDS = ["rm ", "dd ", "mkfs", "shred", "chmod -R 777", "> /dev/sda"]
TOKEN_RE = re.compile(r"[^\w\s]")

STOP_WORDS = {
    "is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", 
    "for", "me", "you", "my", "your", "we", "us", "show", "get", "run", "check",
    "please", "can", "could", "would", "tell", "find", "list", "are", "about", 
    "in", "next", "few", "days", "going", "soon", "anytime", "day", "week"
}

# Strictly universal system keywords applicable to any operating system
UNIVERSAL_SYSTEM_KEYWORDS = {
    "system", "sys", "os", "linux", "kernel", "cpu", "gpu", "hardware", "motherboard", "memory", "ram", "storage", "disk",
    "drive", "nvme", "port", "network", "wifi", "ip", "dns", "log", "error", "specs", "hostname",
    "crash", "slow", "performance", "driver", "package", "status", "health", "window", "manager", "sddm", "gdm", "bootloader", "grub"
}

class InlineSpinner:
    def __init__(self):
        self.chars, self.active, self.thread = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"], False, None

    def _spin(self):
        idx = 0
        while self.active:
            sys.stderr.write(f"\r\033[1;32m{self.chars[idx % 10]}\033[0m ")
            sys.stderr.flush()
            idx, _ = idx + 1, time.sleep(0.08)
        sys.stderr.write("\r\x1b[2K\r")
        sys.stderr.flush()

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
    p_path = os.path.expanduser("~/.config/local-ai/local-ai-agent/tools/skills/mysys.md")
    if os.path.exists(p_path):
        try:
            with open(p_path, "r") as f:
                keywords.update(t for t in tokenize(f.read()) if len(t) > 2)
        except: pass
    return keywords

def run_local_tool(cmd):
    cmd_stripped = cmd.strip()
    # Strip any formatting pipe to guarantee the AI gets clean raw Markdown
    cleaned_cmd = re.sub(r'\|\s*leaf\b.*$', '', cmd_stripped).strip()
    try:
        out = subprocess.check_output(cleaned_cmd, shell=True, text=True, timeout=15).strip()
        return f"{out}\n" if out else "Action executed successfully.\n"
    except Exception as e:
        sys.stderr.write(f"\033[1;31mTool execution failed: {str(e)}\033[0m\n")
        return f"[SYSTEM ERROR] Failed to run local tool: {str(e)}\n"

def compile_vector_index():
    if not os.path.exists(CONTEXT_FILE): return False
    try:
        with open(CONTEXT_FILE, "r") as f: lines = f.read().splitlines()
        index_data = []
        for line in [l.strip() for l in lines if l.strip()]:
            if line.startswith("#") or "----->" in line or "--->" not in line: continue
            cmd, intents = line.split("--->", 1)
            for intent in [i.strip() for i in intents.split(",")]:
                tokens = tokenize(intent)
                if tokens: index_data.append({"cmd": cmd.strip(), "intent": intent, "tokens": tokens, "len": len(tokens)})
        
        from collections import defaultdict
        df = defaultdict(int)
        for entry in index_data:
            for t in set(entry["tokens"]): df[t] += 1
        
        N, idfs = len(index_data), {}
        for t, count in df.items():
            idfs[t] = math.log(1.0 + (N / count))
            
        with open(INDEX_FILE, "w") as f: json.dump({"idfs": idfs, "entries": index_data}, f)
        return True
    except Exception as e:
        sys.stderr.write(f"\033[1;31mError compiling index: {str(e)}\033[0m\n")
        return False

# Diagnostic checks, auto-bootstrapping, and startup compilation
if not os.path.exists(CONTEXT_FILE):
    sys.stderr.write(f"\033[1;31mWarning: Context file is missing at {CONTEXT_FILE}\033[0m\n")
else:
    PROFILE_PATH = os.path.expanduser("~/.config/local-ai/local-ai-agent/tools/skills/mysys.md")
    if not os.path.exists(PROFILE_PATH):
        generator_script = os.path.expanduser("~/.config/local-ai/local-ai-agent/tools/generate-profile")
        if os.path.exists(generator_script):
            subprocess.run([sys.executable, generator_script])

    try:
        mtime_ctx = os.path.getmtime(CONTEXT_FILE)
        try:
            if mtime_ctx > os.path.getmtime(INDEX_FILE): compile_vector_index()
        except OSError: compile_vector_index()
    except OSError as e:
        sys.stderr.write(f"\033[1;31mError reading file metadata: {str(e)}\033[0m\n")

def check_danger(cmd):
    return f"DANGER_FLAGGED:{cmd}" if cmd and any(kw in cmd.lower() for kw in DESTRUCTIVE_KEYWORDS) else cmd

def matrix_search(query, threshold=0.45):
    query_tokens = tokenize(query)
    if not query_tokens: return None
    if not os.path.exists(INDEX_FILE): compile_vector_index()
    try:
        with open(INDEX_FILE, "r") as f: data = json.load(f)
    except:
        compile_vector_index()
        try:
            with open(INDEX_FILE, "r") as f: data = json.load(f)
        except: return None

    idfs, entries = data.get("idfs", {}), data.get("entries", [])
    candidates, q_set = [], set(query_tokens)
    for entry in entries:
        intersect = q_set & set(entry["tokens"])
        if not intersect: continue
            
        match_weight = sum(idfs.get(t, 1.0) for t in intersect)
        q_weight = sum(idfs.get(t, 1.0) for t in q_set)
        entry_weight = sum(idfs.get(t, 1.0) for t in entry["tokens"])
        score = (2.0 * match_weight) / (q_weight + entry_weight) if (q_weight + entry_weight) > 0 else 0.0
        
        if len(intersect) == len(entry["tokens"]) and (len(intersect) / len(q_set) >= 0.50):
            score += 0.20
            
        if score >= threshold: candidates.append((score, entry["cmd"], entry["intent"]))
            
    if not candidates: return None
    candidates.sort(key=lambda x: (-x[0], len(x[2])))
    seen, top = set(), []
    for _, cmd, intent in candidates:
        if cmd not in seen:
            seen.add(cmd); top.append(f"{intent}|||{check_danger(cmd)}")
            if len(top) == 3: break
    return "\n".join(top)

def get_key():
    import tty, termios, select
    fd = sys.stdin.fileno()
    try:
        old = termios.tcgetattr(fd)
    except termios.error:
        try: return os.read(fd, 1).decode("utf-8", errors="ignore")
        except: return ""
    try:
        tty.setraw(fd)
        r = os.read(fd, 1)
        if r == b'\x1b' and select.select([fd], [], [], 0.05)[0]: r += os.read(fd, 2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return r.decode("utf-8", errors="ignore")

def clean_tool_prefix(cmd):
    is_tool = cmd.startswith("[TOOL]")
    cleaned = cmd.replace("[TOOL]", "", 1).strip() if is_tool else cmd
    if cleaned.startswith("DANGER_FLAGGED:"):
        inner = cleaned.replace("DANGER_FLAGGED:", "", 1)
        is_tool = inner.startswith("[TOOL]")
        cleaned = f"DANGER_FLAGGED:{inner.replace('[TOOL]', '', 1).strip()}" if is_tool else cleaned
    
    # Safe fallback to cat if leaf is not installed on the system
    has_leaf = bool(shutil.which("leaf"))
    if is_tool:
        # If it's a dynamic context tool, automatically pipe to leaf 
        if "leaf" not in cleaned:
            cleaned = f"{cleaned} | {'leaf --inline' if has_leaf else 'cat'}"
    else:
        if "leaf" in cleaned and not has_leaf:
            cleaned = re.sub(r'\|\s*leaf\b.*$', '', cleaned).strip()
    return cleaned

def learn_command_from_response(query, ans):
    if not query or not ans: return
    cmds = re.findall(r"```(?:bash|sh|zsh)?\n([^\n]+)\n```", ans)
    if not cmds: cmds = re.findall(r"`([^`\n]+)`", ans)
    valid = [c.strip() for c in cmds if 2 < len(c.strip()) < 80 and not c.strip().startswith("#") and "://" not in c]
    if not valid: return
    suggested = valid[0]
    
    if os.path.exists(CONTEXT_FILE):
        try:
            with open(CONTEXT_FILE, "r") as f:
                if suggested in f.read(): return
        except: pass

    sys.stderr.write(f"\n\033[1;32m[Learn shortcut]\033[0m Map \"\033[1;36m{query.lower()}\033[0m\" ---> \033[1;33m{suggested}\033[0m? (y/N): ")
    sys.stderr.flush()
    if get_key().lower() == 'y':
        sys.stderr.write("Saved!\n"); sys.stderr.flush()
        try:
            with open(CONTEXT_FILE, "a") as f: f.write(f"\n{suggested} ---> {query.lower()}\n")
            if os.path.exists(INDEX_FILE): os.remove(INDEX_FILE)
        except Exception as e:
            sys.stderr.write(f"\033[1;31mFailed to save: {str(e)}\033[0m\n")
    else:
        sys.stderr.write("Skipped.\n"); sys.stderr.flush()

def get_system_context(query):
    context = ""
    tool_match = matrix_search(query, threshold=0.65)
    if tool_match:
        first_match = tool_match.split("\n")[0]
        if "|||" in first_match:
            intent, cmd = first_match.split("|||", 1)
            if cmd.startswith("DANGER_FLAGGED:"):
                cmd = cmd.replace("DANGER_FLAGGED:", "", 1)
            if cmd.startswith("[TOOL]"):
                tool_cmd = cmd.replace("[TOOL]", "").strip()
                sys.stderr.write(f"\033[90m[sys] Executing: {tool_cmd}\033[0m\n"); sys.stderr.flush()
                context = run_local_tool(tool_cmd)
                
    q_tokens = tokenize(query)
    if set(q_tokens) & get_active_system_keywords():
        profile_path = os.path.expanduser("~/.config/local-ai/local-ai-agent/tools/skills/mysys.md")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "r") as f:
                    context = f.read().strip() + "\n\n" + context
            except: pass
    return context

def run_interactive_selection(intent):
    matched_base = matrix_search(intent)
    if not matched_base:
        sys.stderr.write(f"\033[1;33mInfo: \"{intent}\" is not mapping to a known automation.\033[0m\n")
        return
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
                sys.stdout.write(cmd_to_show); sys.stdout.flush(); break
            elif key == '\x1b[A':
                current_idx = (current_idx - 1 + num_opts) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
            elif key == '\x1b[B':
                current_idx = (current_idx + 1) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
    finally:
        sys.stderr.write("\033[?25h"); sys.stderr.flush()

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
        body = {"messages": messages, "stream": True, **extra}
        if model: body["model"] = model
        req = urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
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
        except Exception:
            spinner.stop()
            if url == configs[-1][0]:
                print("\033[1;31mError: All fallbacks/local servers are offline.\033[0m\n")
    return None

if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
    if len(sys.argv) >= 3:
        run_interactive_selection(" ".join(sys.argv[2:]))
    sys.exit(0)

if len(sys.argv) > 1 and sys.argv[1] in ("--talk", "--talk-chat"):
    if sys.argv[1] == "--talk-chat" or len(sys.argv) == 2:
        is_agent = (sys.argv[1] == "--talk-chat")
        if is_agent:
            active_skill = os.environ.get("AI_ACTIVE_SKILL")
            skill_tag = f" [{active_skill}]" if active_skill else ""
            print(f"\033[1;36mAI Agent Session Initialized | Context Loaded{skill_tag} | Ctrl+C to exit.\033[0m\n")
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
                if ans: 
                    chat_history.append({"role": "assistant", "content": ans})
                    if sys.stdout.isatty(): learn_command_from_response(query, ans)
                else: chat_history.pop()
        except KeyboardInterrupt:
            print("\n\r\033[1;33mExiting conversation.\033[0m"); sys.exit(0)

    elif len(sys.argv) > 2:
        query_parts = sys.argv[2:]
        system_context = ""

        SKILLS_DIR = os.path.expanduser("~/.config/local-ai/local-ai-agent/tools/skills")
        if query_parts:
            first_word = query_parts[0].lower()
            skill_file = os.path.join(SKILLS_DIR, f"{first_word}.md")
            if os.path.exists(skill_file):
                try:
                    with open(skill_file, "r") as f: system_context = f.read().strip() + "\n\n"
                    query_parts = query_parts[1:]
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

        ans = stream_llm_response([{"role": "user", "content": prompt}], prefix="AI:")
        if ans and sys.stdout.isatty(): learn_command_from_response(query, ans)
        sys.exit(0)

user_input = sanitize_input(" ".join(sys.argv[1:])) if len(sys.argv) > 1 else ""
if not user_input or sys.argv[1].startswith("--"): sys.exit(0)

matched_base = matrix_search(user_input)
if matched_base:
    out_lines = []
    for line in matched_base.split("\n"):
        intent, cmd = line.split("|||", 1)
        is_tool = cmd.startswith("[TOOL]")
        cleaned_cmd = cmd.replace('[TOOL]', '', 1).strip() if is_tool else cmd
        has_leaf = bool(shutil.which("leaf"))
        
        # Check if the command should be piped to leaf automatically
        if is_tool:
            if "leaf" not in cleaned_cmd:
                cleaned_cmd = f"{cleaned_cmd} | {'leaf --inline' if has_leaf else 'cat'}"
        else:
            if "leaf" in cleaned_cmd and not has_leaf:
                cleaned_cmd = re.sub(r'\bleaf\b.*$', 'cat', cleaned_cmd)
        
        out_lines.append(f"{intent}|||{cleaned_cmd}")
    print("\n".join(out_lines)); sys.exit(0)
else:
    print("Command Not Found"); sys.exit(1)
