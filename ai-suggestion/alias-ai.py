#!/usr/bin/env python3
# AI Suggestion v0.7.7.4 [j5onrf] [06-03-26]

import sys, re, os, json, threading, time
import urllib.request as urlreq, urllib.error as urlerr

# Enable standard terminal line editing and history features for input()
try:
    import readline
except ImportError:
    pass

sys.argv = [arg for arg in sys.argv if arg != ""]

CONTEXT_FILE = os.path.expanduser("~/.config/local-ai/ai-suggestion/ai-context.txt")
INDEX_FILE = os.path.expanduser("~/.config/local-ai/ai-suggestion/ai-context.idx")
DESTRUCTIVE_KEYWORDS = ["rm ", "dd ", "mkfs", "shred", "chmod -R 777", "> /dev/sda"]
TOKEN_RE = re.compile(r"[^\w\s]")

STOP_WORDS = {
    "is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", 
    "for", "me", "you", "my", "your", "we", "us", "show", "get", "run", "check",
    "please", "can", "could", "would", "tell", "find", "list", "are", "about", 
    "in", "next", "few", "days", "going", "soon", "anytime", "day", "week"
}

class InlineSpinner:
    """A lightweight standard-library terminal spinner for network latency feedback."""
    def __init__(self):
        self.chars, self.active, self.thread = ["|", "/", "-", "\\"], False, None

    def _spin(self):
        idx = 0
        while self.active:
            sys.stdout.write(f"\r\033[1;32m{self.chars[idx % 4]}\033[0m ")
            sys.stdout.flush()
            idx, _ = idx + 1, time.sleep(0.08)
        sys.stdout.write("\r\x1b[K")
        sys.stdout.flush()

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

    # Recompile on empty or corrupted index
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
        if match_count == entry_len:
            score += 0.20
        if score >= threshold:
            candidates.append((score, entry["cmd"], entry["intent"]))
            
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda x: (x[0], len(x[2])))
    
    seen, top = set(), []
    for _, cmd, intent in candidates:
        if cmd not in seen:
            seen.add(cmd)
            top.append(f"{intent}|||{check_danger(cmd)}")
            if len(top) == 3:
                break
    return "\n".join(top)

def get_api_config():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        return "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {
            "Content-Type": "application/json", "Authorization": f"Bearer {gemini_key}"
        }, os.environ.get("CLOUD_MODEL", "gemini-1.5-flash")
    ckey, curl = os.environ.get("CLOUD_API_KEY"), os.environ.get("CLOUD_API_URL")
    if ckey and curl:
        return curl, {"Content-Type": "application/json", "Authorization": f"Bearer {ckey}"}, os.environ.get("CLOUD_MODEL")
    return "http://localhost:8080/v1/chat/completions", {"Content-Type": "application/json"}, None

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

if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
    if len(sys.argv) >= 3:
        run_interactive_selection(" ".join(sys.argv[2:]))
    sys.exit(0)

if len(sys.argv) > 1 and sys.argv[1] in ("--talk", "--talk-chat"):
    url, headers, model = get_api_config()
    if sys.argv[1] == "--talk-chat" or len(sys.argv) == 2:
        is_agent = (sys.argv[1] == "--talk-chat")
        print(f"\033[1;36mAI Agent Session Initialized | Context Loaded | Ctrl+C to exit.\033[0m\n" if is_agent else "\033[1;34mLocal AI Conversation Mode. Ctrl+C to quit.\033[0m\n")
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
                    
                    # Compacted Markdown Session Backup Interceptor (11 Lines)
                    if query.lower() in ("backup", "save"):
                        try:
                            fn = os.path.expanduser(f"~/ai-session-{time.strftime('%Y-%m-%d_%H%M%S')}.md")
                            with open(fn, "w") as f:
                                f.write(f"# Session Backup — {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n" + "".join(
                                    f"### ❯ {m['content'].split('User Question: ', 1)[-1]}\n\n" if m["role"] == "user"
                                    else f"**{'Agent' if is_agent else 'AI'}:** {m['content']}\n\n---\n\n" for m in chat_history
                                ))
                            print(f"\033[1;32mSession successfully backed up to: {fn}\033[0m\n")
                        except Exception as e:
                            print(f"\033[1;31mError writing backup: {str(e)}\033[0m\n")
                        continue

                system_context, tool_match = "", matrix_search(query)
                if tool_match:
                    first_match = tool_match.split("\n")[0]
                    if "|||" in first_match:
                        intent, cmd = first_match.split("|||", 1)
                        if cmd.startswith("[TOOL]"):
                            system_context = run_local_tool(cmd.replace("[TOOL]", "").strip())

                prompt = (
                    "You are a helpful, conversational local AI shell assistant with read-only terminal access.\n"
                    "Use the provided real-time system context (if available) to answer the user's question clearly, concisely, and directly.\n"
                    "Do not state that you cannot access their system, as the data has already been provided to you.\n\n"
                )
                if system_context:
                    prompt += f"### Real-time System Context:\n{system_context}\n\n"
                prompt += f"User Question: {query}"
                chat_history.append({"role": "user", "content": prompt})

                req = urlreq.Request(url, data=json.dumps({"messages": chat_history, "stream": True, **({"model": model} if model else {})}).encode("utf-8"), headers=headers, method="POST")
                spinner = InlineSpinner()
                try:
                    spinner.start()
                    with urlreq.urlopen(req) as response:
                        first_chunk, assistant_response_accumulator = True, []
                        for line in response:
                            decoded = line.decode("utf-8").strip()
                            if not decoded or decoded == "[DONE]": continue
                            if decoded.startswith("data: "): decoded = decoded[6:].strip()
                            try:
                                data = json.loads(decoded)
                                if "choices" in data and len(data["choices"]) > 0:
                                    content = data["choices"][0]["delta"].get("content", "")
                                elif "candidates" in data and len(data["candidates"]) > 0:
                                    parts = data["candidates"][0].get("content", {}).get("parts", [])
                                    content = parts[0].get("text", "") if parts else ""
                                else: content = ""
                                
                                if content:
                                    if first_chunk:
                                        spinner.stop()
                                        print("\033[1;32mAgent:\033[0m " if is_agent else "\033[1;32mAI:\033[0m ", end="", flush=True)
                                        first_chunk = False
                                    print(content, end="", flush=True)
                                    assistant_response_accumulator.append(content)
                            except Exception: pass
                        chat_history.append({"role": "assistant", "content": "".join(assistant_response_accumulator)})
                        print("\n")
                except urlerr.HTTPError as e:
                    spinner.stop(); chat_history.pop()
                    try:
                        error_body = e.read().decode("utf-8")
                        msg = json.loads(error_body).get("error", {}).get("message", error_body)
                        print(f"\033[1;31mError: API returned status code {e.code}: {msg}\033[0m\n")
                    except Exception:
                        print(f"\033[1;31mError: API returned status code {e.code}\033[0m\n")
                except urlerr.URLError as e:
                    spinner.stop(); chat_history.pop()
                    print(f"\033[1;31mError: Cloud AI API request failed: {e.reason}\033[0m\n" if os.environ.get("GEMINI_API_KEY") or os.environ.get("CLOUD_API_KEY") else "\033[1;31mError: Local AI server is offline. Please start your server.\033[0m\n")
                except KeyboardInterrupt:
                    spinner.stop(); print("\n\033[1;33mExiting conversation.\033[0m"); sys.exit(0)
        except KeyboardInterrupt:
            print("\n\033[1;33mExiting conversation.\033[0m"); sys.exit(0)

    # Standard single-turn conversation logic
    elif len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        system_context, tool_match = "", matrix_search(query)
        if tool_match:
            first_match = tool_match.split("\n")[0]
            if "|||" in first_match:
                intent, cmd = first_match.split("|||", 1)
                if cmd.startswith("[TOOL]"):
                    system_context = run_local_tool(cmd.replace("[TOOL]", "").strip())

        prompt = (
            "You are a helpful, conversational local AI shell assistant with read-only terminal access.\n"
            "Use the provided real-time system context (if available) to answer the user's question clearly, concisely, and directly.\n"
            "Do not state that you cannot access their system, as the data has already been provided to you.\n\n"
        )
        if system_context:
            prompt += f"### Real-time System Context:\n{system_context}\n\n"
        prompt += f"User Question: {query}"

        req = urlreq.Request(url, data=json.dumps({"messages": [{"role": "user", "content": prompt}], "stream": True, **({"model": model} if model else {})}).encode("utf-8"), headers=headers, method="POST")
        spinner = InlineSpinner()
        try:
            spinner.start()
            with urlreq.urlopen(req) as response:
                first_chunk = True
                for line in response:
                    decoded = line.decode("utf-8").strip()
                    if not decoded or decoded == "[DONE]": continue
                    if decoded.startswith("data: "): decoded = decoded[6:].strip()
                    try:
                        data = json.loads(decoded)
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0]["delta"].get("content", "")
                        elif "candidates" in data and len(data["candidates"]) > 0:
                            parts = data["candidates"][0].get("content", {}).get("parts", [])
                            content = parts[0].get("text", "") if parts else ""
                        else: content = ""
                        
                        if content:
                            if first_chunk:
                                spinner.stop()
                                print("\033[1;32mAI:\033[0m ", end="", flush=True)
                                first_chunk = False
                            print(content, end="", flush=True)
                    except Exception: pass
            print()
        except urlerr.HTTPError as e:
            spinner.stop()
            try:
                error_body = e.read().decode("utf-8")
                msg = json.loads(error_body).get("error", {}).get("message", error_body)
                print(f"\033[1;31mError: API returned status code {e.code}: {msg}\033[0m")
            except Exception:
                print(f"\033[1;31mError: API returned status code {e.code}\033[0m")
        except urlerr.URLError as e:
            spinner.stop()
            print(f"\033[1;31mError: Cloud AI API request failed: {e.reason}\033[0m" if os.environ.get("GEMINI_API_KEY") or os.environ.get("CLOUD_API_KEY") else "\033[1;31mError: Local AI server is offline. Please start your server.\033[0m")
        except KeyboardInterrupt:
            spinner.stop(); print("\n\033[1;33mInterrupted.\033[0m")
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
