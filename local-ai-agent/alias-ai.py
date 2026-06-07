#!/usr/bin/env python3
# Local-Ai Agent v0.7.9.5 [j5onrf] [06-06-26]

import sys, re, os, json, threading, time
import urllib.request as urlreq, urllib.error as urlerr

# Enable standard terminal line editing and history features for input()
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

class InlineSpinner:
    """A lightweight modern Braille spinner for network latency feedback."""
    def __init__(self):
        # 10-step circular Braille sequence
        self.chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.active = False
        self.thread = None

    def _spin(self):
        idx = 0
        while self.active:
            # Render the animated Braille tick
            sys.stderr.write(f"\r\033[1;32m{self.chars[idx % 10]}\033[0m ")
            sys.stderr.flush()
            idx, _ = idx + 1, time.sleep(0.08)
        sys.stderr.write("\r\x1b[K")
        sys.stderr.flush()

    def start(self):
        self.active = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        self.active = False
        if self.thread:
            self.thread.join()

def sanitize_input(text):
    return re.sub(r"[`$]", "", text).strip() if text else ""

def tokenize(text):
    return [w for w in TOKEN_RE.sub(" ", text.lower()).split() if len(w) > 1 and w not in STOP_WORDS]

def run_local_tool(cmd):
    import subprocess
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, timeout=15).strip()
        return f"{out}\n" if out else "Action executed successfully.\n"
    except Exception as e:
        sys.stderr.write(f"\033[1;31mTool execution failed: {str(e)}\033[0m\n")
        return f"[SYSTEM ERROR] Failed to run local tool: {str(e)}\n"

def compile_vector_index():
    if not os.path.exists(CONTEXT_FILE):
        sys.stderr.write(f"\033[1;31mWarning: Configuration file not found at {CONTEXT_FILE}\033[0m\n")
        return False
    try:
        with open(CONTEXT_FILE, "r") as f:
            lines = f.read().splitlines()
        index_data = []
        for line in [l.strip() for l in lines if l.strip()]:
            if line.startswith("#") or "----->" in line or "--->" not in line:
                continue
            cmd, intents = line.split("--->", 1)
            for intent in [i.strip() for i in intents.split(",")]:
                tokens = tokenize(intent)
                if tokens:
                    index_data.append({"cmd": cmd.strip(), "intent": intent, "tokens": tokens, "len": len(tokens)})
        with open(INDEX_FILE, "w") as f:
            json.dump(index_data, f)
        return True
    except Exception as e:
        sys.stderr.write(f"\033[1;31mError compiling search index: {str(e)}\033[0m\n")
        return False

# Diagnostic checks and startup compilation
if not os.path.exists(CONTEXT_FILE):
    sys.stderr.write(f"\033[1;31mWarning: Context file is missing at {CONTEXT_FILE}\033[0m\n")
else:
    try:
        mtime_ctx = os.path.getmtime(CONTEXT_FILE)
        try:
            if mtime_ctx > os.path.getmtime(INDEX_FILE):
                compile_vector_index()
        except OSError:
            compile_vector_index()
    except OSError as e:
        sys.stderr.write(f"\033[1;31mError reading file metadata: {str(e)}\033[0m\n")

def check_danger(cmd):
    return f"DANGER_FLAGGED:{cmd}" if cmd and any(kw in cmd.lower() for kw in DESTRUCTIVE_KEYWORDS) else cmd

def matrix_search(query, threshold=0.50):
    query_tokens = tokenize(query)
    if not query_tokens:
        return None
    if not os.path.exists(INDEX_FILE):
        compile_vector_index()

    index_data = None
    try:
        with open(INDEX_FILE, "r") as f:
            index_data = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass

    if not index_data and os.path.exists(CONTEXT_FILE):
        compile_vector_index()
        try:
            with open(INDEX_FILE, "r") as f:
                index_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
    if not index_data:
        return None

    candidates, q_set, len_q = [], set(query_tokens), len(query_tokens)
    for entry in index_data:
        intersect = q_set & set(entry["tokens"])
        match_count = len(intersect)
        if match_count == 0:
            continue
        entry_len = entry.get("len", len(entry["tokens"]))
        score = (2.0 * match_count) / (len_q + entry_len)
        
        # Perfect subset bonus: Only applies if the matched words 
        # represent 50% or more of the active query tokens.
        if match_count == entry_len and (match_count / len_q >= 0.50):
            score += 0.20
            
        if score >= threshold:
            candidates.append((score, entry["cmd"], entry["intent"]))
            
    if not candidates:
        return None
    
    candidates.sort(key=lambda x: (-x[0], len(x[2])))
    seen, top = set(), []
    for _, cmd, intent in candidates:
        if cmd not in seen:
            seen.add(cmd)
            top.append(f"{intent}|||{check_danger(cmd)}")
            if len(top) == 3:
                break
    return "\n".join(top)

def get_key():
    import tty, termios, select
    fd = sys.stdin.fileno()
    try:
        old = termios.tcgetattr(fd)
    except termios.error:
        try:
            return os.read(fd, 1).decode("utf-8", errors="ignore")
        except Exception: return ""
    try:
        tty.setraw(fd)
        r = os.read(fd, 1)
        if r == b'\x1b' and select.select([fd], [], [], 0.05)[0]:
            r += os.read(fd, 2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return r.decode("utf-8", errors="ignore")

def clean_tool_prefix(cmd):
    if cmd.startswith("DANGER_FLAGGED:"):
        inner = cmd.replace("DANGER_FLAGGED:", "", 1)
        return f"DANGER_FLAGGED:{inner.replace('[TOOL]', '', 1).strip()}" if inner.startswith("[TOOL]") else cmd
    return cmd.replace("[TOOL]", "", 1).strip() if cmd.startswith("[TOOL]") else cmd

def run_interactive_selection(intent):
    matched_base = matrix_search(intent)
    if not matched_base:
        sys.stderr.write(f"\033[1;33mℹ \"{intent}\" is not mapping to a known automation.\033[0m\n")
        return

    options = matched_base.split("\n")
    num_opts, current_idx = len(options), 0
    sys.stderr.write("\033[?25l")
    sys.stderr.flush()

    try:
        while True:
            entry = options[current_idx]
            current_intent, current_cmd = entry.split("|||", 1)
            display_idx, current_cmd = current_idx + 1, clean_tool_prefix(current_cmd)
            is_danger = current_cmd.startswith("DANGER_FLAGGED:")
            cmd_to_show = current_cmd.replace("DANGER_FLAGGED:", "") if is_danger else current_cmd
            display_cmd = cmd_to_show.replace(" >/dev/null 2>&1", "").replace(os.path.expanduser("~"), "~")

            if is_danger:
                sys.stderr.write("\r\x1b[K\x1b[1;31m⚠️ WARNING: Potentially destructive suggestion detected!\x1b[0m\n")
                sys.stderr.write(f"\r\x1b[K\x1b[1;33mAI Suggestion ({display_idx}/{num_opts}):\x1b[0m \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n")
                sys.stderr.write("\r\x1b[KAre you absolutely sure you want to run this? (y/N): ")
            else:
                label = f"AI Suggestion ({display_idx}/{num_opts}) [Up/Down]:" if num_opts > 1 else "AI Suggestion:"
                sys.stderr.write(f"\r\x1b[K\x1b[1;32m{label}\x1b[0m \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n")
                sys.stderr.write("\r\x1b[K[Enter] Execute / [Any Key] Cancel: ")
            
            sys.stderr.flush()
            key = get_key()

            if key in ('\x03', '\x1b') or (not is_danger and key not in ('\r', '', '\x1b[A', '\x1b[B')):
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n"); sys.stderr.flush(); break
            if is_danger:
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K"); sys.stderr.flush()
                if key.lower() == 'y':
                    sys.stdout.write(cmd_to_show); sys.stdout.flush()
                else:
                    sys.stderr.write("Aborted safely.\n")
                break
            if key in ('\r', ''):
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K"); sys.stderr.flush()
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
    """Cascades dynamically through available API configurations with minimal overhead."""
    configs = []
    gkey, okey = os.environ.get("GEMINI_API_KEY"), os.environ.get("OPENROUTER_API_KEY")
    if gkey:
        configs.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {"Content-Type": "application/json", "Authorization": f"Bearer {gkey}"}, os.environ.get("CLOUD_MODEL", "gemini-1.5-flash"), {}))
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
            with urlreq.urlopen(req) as response:
                first, acc = True, []
                for line in response:
                    dec = line.decode("utf-8").strip()
                    if dec.startswith("data: "): dec = dec[6:].strip()
                    if not dec or dec == "[DONE]": continue
                    try:
                        data = json.loads(dec)
                        content = ""
                        if "choices" in data and data["choices"]:
                            content = data["choices"][0].get("delta", {}).get("content", "")
                        elif "candidates" in data and data["candidates"]:
                            parts = data["candidates"][0].get("content", {}).get("parts", [])
                            content = parts[0].get("text", "") if parts else ""
                        if content:
                            if first:
                                spinner.stop()
                                # Only print the colored prompt prefix if outputting to an interactive terminal
                                if sys.stdout.isatty():
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
                if pending_query:
                    query, pending_query = pending_query, None
                else:
                    try: raw_query = input("\033[1;30m❯\033[0m ")
                    except EOFError: break
                    if not raw_query.strip(): continue
                    query = raw_query.strip()
                    if query.lower() in ("exit", "quit", "q"):
                        print("\033[1;33mExiting conversation.\033[0m"); sys.exit(0)

                system_context, tool_match = "", matrix_search(query, threshold=0.65)
                if tool_match:
                    first_match = tool_match.split("\n")[0]
                    if "|||" in first_match:
                        intent, cmd = first_match.split("|||", 1)
                        if cmd.startswith("[TOOL]"):
                            tool_cmd = cmd.replace("[TOOL]", "").strip()
                            sys.stderr.write(f"\033[90m[sys] Executing: {tool_cmd}\033[0m\n")
                            sys.stderr.flush()
                            system_context = run_local_tool(tool_cmd)

                prompt = (
                    "You are a helpful, conversational local AI shell assistant with read-only terminal access.\n"
                    "Use the provided real-time system context (if available) to answer the user's question clearly, concisely, and directly.\n"
                    "Do not state that you cannot access their system, as the data has already been provided to you.\n\n"
                )
                if system_context:
                    prompt += f"### Real-time System Context:\n{system_context}\n\n"
                prompt += f"User Question: {query}"
                chat_history.append({"role": "user", "content": prompt})

                ans = stream_llm_response(chat_history, prefix="Agent:" if is_agent else "AI:")
                if ans: chat_history.append({"role": "assistant", "content": ans})
                else: chat_history.pop()
        except KeyboardInterrupt:
            print("\n\033[1;33mExiting conversation.\033[0m"); sys.exit(0)

    elif len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        system_context, tool_match = "", matrix_search(query, threshold=0.65)
        if tool_match:
            first_match = tool_match.split("\n")[0]
            if "|||" in first_match:
                intent, cmd = first_match.split("|||", 1)
                if cmd.startswith("[TOOL]"):
                    tool_cmd = cmd.replace("[TOOL]", "").strip()
                    system_context = run_local_tool(tool_cmd)

        prompt = (
            "You are a helpful, conversational local AI shell assistant with read-only terminal access.\n"
            "Use the provided real-time system context (if available) to answer the user's question clearly, concisely, and directly.\n"
            "Do not state that you cannot access their system, as the data has already been provided to you.\n\n"
        )
        if system_context:
            prompt += f"### Real-time System Context:\n{system_context}\n\n"
        prompt += f"User Question: {query}"

        stream_llm_response([{"role": "user", "content": prompt}], prefix="AI:")
        sys.exit(0)

user_input = sanitize_input(" ".join(sys.argv[1:])) if len(sys.argv) > 1 else ""
if not user_input or sys.argv[1].startswith("--"):
    sys.exit(0)

matched_base = matrix_search(user_input)
if matched_base:
    out_lines = []
    for line in matched_base.split("\n"):
        intent, cmd = line.split("|||", 1)
        out_lines.append(f"{intent}|||{cmd.replace('[TOOL]', '', 1).strip() if cmd.startswith('[TOOL]') else cmd}")
    print("\n".join(out_lines)); sys.exit(0)
else:
    print("Command Not Found"); sys.exit(1)
