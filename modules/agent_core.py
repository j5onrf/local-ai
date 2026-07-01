#!/usr/bin/env python3
# Local-Ai Agent Core Module [j5onrf] [v0.8.9.11]

import os
import sys
import re
import json
import time
import threading
import tty
import termios
import select
import subprocess
import shutil
import urllib.request as urlreq
import urllib.parse as urlparse
import urllib.error as urlerr
import requests
from typing import List, Dict, Callable, Optional

try:
    import speed_test
except ImportError:
    speed_test = None

# --- FAST-PATH BYTE EXTRACTOR ---
def extract_stream_content(line_bytes: bytes) -> str:
    """Performs raw byte-level searching to extract streaming tokens."""
    idx = line_bytes.find(b'"content":"')
    start = (idx + 11) if idx != -1 else (line_bytes.find(b'"text":"') + 8)
    if start < 11: return ""
    end, length = start, len(line_bytes)
    while end < length:
        if line_bytes[end] == 34: break
        end += 2 if line_bytes[end] == 92 else 1
    try:
        return json.loads((b'"' + line_bytes[start:end] + b'"').decode("utf-8", errors="ignore"))
    except Exception:
        return line_bytes[start:end].decode("utf-8", errors="ignore")


# --- TERMINAL & USER INTERFACE UTILITIES ---
class InlineSpinner:
    def __init__(self, chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        self.chars, self.active, self.thread = chars, False, None

    def _spin(self) -> None:
        idx, char_len = 0, len(self.chars)
        while self.active:
            try:
                sys.stderr.write(f"\r\033[1;32m{self.chars[idx % char_len]}\033[0m ")
                sys.stderr.flush()
            except Exception: pass
            idx += 1
            time.sleep(0.08)
        sys.stderr.write("\r\x1b[2K\r")
        sys.stderr.flush()

    def start(self) -> None:
        if not self.active:
            self.active = True
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()

    def stop(self) -> None:
        if self.active:
            self.active = False
            if self.thread:
                self.thread.join()
                self.thread = None


def get_key() -> str:
    tty_file = None
    try:
        tty_file = open("/dev/tty", "r+")
        fd = tty_file.fileno()
    except Exception:
        fd = sys.stdin.fileno()
    try:
        import fcntl
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
    except Exception: pass
    try:
        old = termios.tcgetattr(fd)
    except Exception:
        try: return os.read(fd, 1).decode("utf-8", errors="ignore")
        except Exception: return ""
        finally:
            if tty_file: tty_file.close()
    try:
        tty.setraw(fd)
        try: termios.tcflush(fd, termios.TCIFLUSH)
        except Exception: pass
        char_bytes = os.read(fd, 1)
        if char_bytes == b'\x1b' and select.select([fd], [], [], 0.05)[0]:
            char_bytes += os.read(fd, 2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        if tty_file: tty_file.close()
    return char_bytes.decode("utf-8", errors="ignore")


def prune_history(history: List[Dict[str, str]], max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
    if len(history) <= 1: return history
    try:
        limit = int(os.environ.get("AI_MAX_TOKENS", 8192)) if max_tokens is None else max_tokens
    except Exception:
        limit = 8192
    sys_prompt = history[0]
    curr_tokens = len(sys_prompt["content"]) // 4
    selected = []
    for msg in reversed(history[1:]):
        approx = len(msg["content"]) // 4
        if not selected or (curr_tokens + approx <= limit):
            selected.append(msg)
            curr_tokens += approx
        else: break
    return [sys_prompt] + list(reversed(selected))


def draw_session_box(workspace_path: str, home_dir: str, is_agent: bool, db_turns: int, active_system_prompt: str, clean_name: str) -> None:
    version = ""
    main_path = os.path.join(home_dir, ".config", "local-ai", "ai-agent.py")
    if os.path.exists(main_path):
        try:
            with open(main_path, "r", encoding="utf-8") as f:
                for line in f:
                    if match := re.search(r"Local-Ai Agent\s+(v[0-9.]+)", line, re.I):
                        version = match.group(1)
                        break
        except Exception: pass
    disp = workspace_path.replace(home_dir, "~", 1) if workspace_path.startswith(home_dir) else workspace_path
    if len(disp) > 28: disp = "..." + disp[-25:]
    model = os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite") if os.environ.get("GEMINI_API_KEY") else os.environ.get("OPENROUTER_MODEL", "openrouter/free") if os.environ.get("OPENROUTER_API_KEY") else "local-model"
    box_w = 46
    lines = [
        f" >_ Local-AI Agent ({version})" if version else " >_ Local-AI Agent",
        "",
        f" model:     {model}",
        f" directory: {disp}",
        f" skill:     {clean_name}" if clean_name else " skill:     default",
        f" database:  {db_turns} turns (asleep)" if is_agent else " database:  stateless"
    ]
    print("\033[1;36m╭" + "─" * box_w + "╮\033[0m")
    for i, l in enumerate(lines):
        if i == 1:
            print(f"\033[1;36m│\033[0m{' ':<{box_w}}\033[1;36m│\033[0m")
        else:
            style = "\033[1;37m" if i == 0 else "\033[2m"
            print(f"\033[1;36m│\033[0m {style}{l:<{box_w-1}}\033[0m\033[1;36m│\033[0m")
    print("\033[1;36m╰" + "─" * box_w + "╯\033[0m")
    print(f"\033[2m[sys] Startup context: {len(active_system_prompt)//4:,} tokens | Ctrl+C to exit.\033[0m\n")


def run_interactive_selection(intent: str, jaccard_search_fn: Callable[[str], Optional[str]], clean_tool_prefix_fn: Callable[[str], str], print_stock_error_fn: Callable[[str], None], ensure_mysys_exists_fn: Callable[[], None]) -> None:
    if re.search(r'[\[\]{}()=\'"",;|<>#]', intent) or not (matched_base := jaccard_search_fn(intent)):
        print_stock_error_fn(intent)
        sys.exit(127)
    opts = matched_base.split("\n")
    num_opts, cur_idx = len(opts), 0
    sys.stderr.write("\033[?25l")
    sys.stderr.flush()
    try:
        while True:
            cur_intent, cur_cmd = opts[cur_idx].split("|||", 1)
            cur_cmd = clean_tool_prefix_fn(cur_cmd)
            is_danger = cur_cmd.startswith("DANGER_FLAGGED:")
            cmd_show = cur_cmd.replace("DANGER_FLAGGED:", "")
            disp = cmd_show.replace(" >/dev/null 2>&1", "").replace(os.path.expanduser("~"), "~").replace("/.config/local-ai/projects/", "/")
            idx_str = f"{cur_idx+1:02d}/{num_opts:02d}"
            if is_danger:
                sys.stderr.write(f"\r\x1b[K\033[1;31m▲ WARNING: Destructive payload detected\033[0m\n\r\x1b[K\033[1;31m[{idx_str}]\033[0m ❯ \x1b[1;36m[{cur_intent}]\x1b[0m {disp}\n\r\x1b[K\033[2m::\033[0m execute payload? [y/N]: ")
            else:
                sys.stderr.write(f"\r\x1b[K\033[1;32m[{idx_str}]\033[0m ❯ \x1b[1;36m[{cur_intent}]\x1b[0m {disp}\n\r\x1b[K\033[2m::\033[0m ↵ run  Esc: ")
            sys.stderr.flush()
            key = get_key()
            if key in ('\x03', '\x1b') or (not is_danger and key not in ('\r', '', '\x1b[A', '\x1b[B')):
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n")
                sys.stderr.flush()
                break
            if is_danger:
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K")
                sys.stderr.flush()
                if key.lower() == 'y':
                    if "system" in cmd_show: ensure_mysys_exists_fn()
                    sys.stdout.write(cmd_show)
                else:
                    sys.stderr.write("Aborted safely.\n")
                sys.stdout.flush()
                break
            if key in ('\r', ''):
                sys.stderr.write("\n")
                sys.stderr.flush()
                if "system" in cmd_show: ensure_mysys_exists_fn()
                sys.stdout.write(cmd_show)
                sys.stdout.flush()
                break
            elif key in ('\x1b[A', '\x1b[B'):
                cur_idx = (cur_idx + (1 if key == '\x1b[B' else -1) + num_opts) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
        sys.exit(0)
    except KeyboardInterrupt:
        sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n")
        sys.stderr.flush()
        sys.exit(130)
    finally:
        sys.stderr.write("\033[?25h")
        sys.stderr.flush()


def confirm_tool(tool: str) -> bool:
    sys.stderr.write(f"\033[1;33m[sys] Authorize tool: {tool}? [Y/n]: \033[0m")
    sys.stderr.flush()
    try: char = get_key()
    except Exception: char = ""
    is_yes = char.lower() == 'y' or char in ('\r', '\n', '')
    if char in ('\r', '\n', ''): sys.stderr.write("y\n")
    elif char.startswith('\x1b') or char == '\x03': sys.stderr.write("n\n")
    else: sys.stderr.write(f"{char}\n")
    sys.stderr.flush()
    return is_yes


# --- SPELLING & GRAMMAR HEURISTICS ---
TYPO_OVERRIDES = {
    "hellow": "hello", "helow": "hello", "helo": "hello",
    "howre": "how are", "wru": "where are you", "hru": "how are you",
    "youa": "you", "trainted": "trained"
}
PROTECTED_WORDS = {"hello", "hi", "hey", "how", "here", "you", "who", "there"}

def load_system_dictionary():
    embedded = set("the be to of and a in that have i it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way even new want because any these give day most us lazy quick brown fox jumps dog cat mat sit sits book read reads spelling grammar here there where why when how who what which whose am is are was were been being have has had having do does did doing write writes written writing code coder coding program programming python script sentence errors error correct correction spelled spelling hello hi hey".split())
    for path in ["/usr/share/dict/words", "/etc/dictionaries-common/words", "/usr/dict/words"]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    words = {w.strip().lower() for w in f if w.strip().isalpha()}
                    words.update(embedded)
                    return words
            except Exception: pass
    return embedded

DICT_WORDS = load_system_dictionary()
DICT_WORDS.update({"auth", "git", "bash", "zsh", "cli", "tui", "yaml", "json", "ast", "llm", "api", "url", "cmd", "args", "uuid", "md", "txt", "db", "sqlite", "epoxy", "wttr"})

def edits1(word):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    return set([L + R[1:] for L, R in splits if R] +
               [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1] +
               [L + c + R[1:] for L, R in splits if R for c in 'abcdefghijklmnopqrstuvwxyz'] +
               [L + c + R for L, R in splits for c in 'abcdefghijklmnopqrstuvwxyz'])


def correct_word(word):
    if not DICT_WORDS or not word.isalpha() or len(word) < 3: return word
    w_lower = word.lower()
    if w_lower in DICT_WORDS: return word
    candidates = edits1(w_lower) & DICT_WORDS
    if candidates:
        def edit_prio(c):
            return (1 if sorted(c) == sorted(w_lower) else 2 if len(c) - len(w_lower) == 1 else 3 if len(c) - len(w_lower) == 0 else 4, c)
        best = min(candidates, key=edit_prio)
        return best.upper() if word.isupper() else best.capitalize() if word[0].isupper() else best
    return word


def apply_static_overrides(query: str) -> tuple:
    words, changed = re.split(r'(\b[a-zA-Z]+\b)', query), False
    for i, chunk in enumerate(words):
        if chunk.isalpha() and chunk.lower() in TYPO_OVERRIDES:
            corr = TYPO_OVERRIDES[chunk.lower()]
            words[i] = corr.upper() if chunk.isupper() else corr.capitalize() if chunk[0].isupper() else corr
            changed = True
    return "".join(words), changed


def check_query_spelling_offline(query: str) -> tuple:
    words, changed = re.split(r'(\b[a-zA-Z]+\b)', query), False
    for i, chunk in enumerate(words):
        if chunk.isalpha():
            corr = correct_word(chunk)
            if corr != chunk:
                words[i], changed = corr, True
    return "".join(words), changed


def check_query_spelling(query, get_key_fn):
    original_input = query
    query, changed_static = apply_static_overrides(query)
    corrected_query, changed, used_grammar_server = query, changed_static, False
    endpoints = ["http://localhost:8010/v2/check", "http://localhost:8081/v2/check", "https://api.languagetool.org/v2/check"]
    response_data = None
    for url in endpoints:
        form_data = urlparse.urlencode({'text': query, 'language': 'en-US'}).encode('utf-8')
        req = urlreq.Request(url, data=form_data, method='POST')
        try:
            with urlreq.urlopen(req, timeout=1.2) as r:
                response_data = json.loads(r.read().decode('utf-8'))
                used_grammar_server = True
                break
        except Exception: pass
    if response_data and "matches" in response_data:
        matches = response_data["matches"]
        if matches:
            matches.sort(key=lambda m: m.get("offset", 0), reverse=True)
            chars = list(query)
            for match in matches:
                offset, length = match.get("offset"), match.get("length")
                replacements = match.get("replacements", [])
                if replacements and offset is not None and length is not None:
                    best_correction = replacements[0].get("value")
                    if best_correction is not None:
                        original_word = query[offset : offset + length]
                        if original_word.lower() in PROTECTED_WORDS: continue
                        if original_word and best_correction and original_word.isalpha():
                            local_cand = correct_word(original_word)
                            if local_cand != original_word and local_cand.lower() != best_correction.lower():
                                def get_prio(w):
                                    w_low, orig_low = w.lower(), original_word.lower()
                                    return 1 if (sorted(w_low) == sorted(orig_low)) else 2 if len(w_low) - len(orig_low) == 1 else 3 if len(w_low) - len(orig_low) == 0 else 4
                                if get_prio(local_cand) < get_prio(best_correction) or (best_correction[0].lower() != original_word[0].lower() and local_cand[0].lower() == original_word[0].lower()):
                                    best_correction = local_cand
                        chars[offset : offset + length] = list(best_correction)
                        changed = True
            corrected_query = "".join(chars)
    if not used_grammar_server and not changed_static:
        corrected_query, changed = check_query_spelling_offline(query)
    if changed and corrected_query.strip().lower() != original_input.strip().lower():
        sys.stderr.write(f"\n\033[2m[sys] Typos detected. Correct query to:\033[0m\n\033[3m   \"{corrected_query}\"\033[0m\n\033[2m   [↵ accept  Tab: edit  d: disable  Esc: skip]: \033[0m")
        sys.stderr.flush()
        key = get_key_fn()
        cols = shutil.get_terminal_size().columns or 80
        total_lines = 1 + ((len("[sys] Typos detected. Correct query to:") + cols - 1) // cols) + ((3 + len(corrected_query) + 1 + cols - 1) // cols) + ((len("   [↵ accept  Tab: edit  d: disable  Esc: skip]: ") + cols - 1) // cols)
        clear_prompt = "\r\x1b[K" + "\x1b[1A\r\x1b[K" * (total_lines - 1)
        if key in ('\r', '\n', ''):
            sys.stderr.write(f"{clear_prompt}\033[2;32m[sys] Corrected.\033[0m\n")
            sys.stderr.flush()
            return "RUN", corrected_query
        elif key in ('\t', 'e', 'E'):
            sys.stderr.write(f"{clear_prompt}\033[2;33m[sys] Returning to editor...\033[0m\n")
            sys.stderr.flush()
            return "EDIT", original_input
        elif key in ('d', 'D'):
            sys.stderr.write(f"{clear_prompt}\033[2;31m[sys] Spellchecker disabled. (Type /e to re-enable)\033[0m\n")
            sys.stderr.flush()
            return "DISABLE", original_input
        else:
            sys.stderr.write(clear_prompt)
            sys.stderr.flush()
    return "RUN", original_input


# --- JACCARD CONTEXT MAPPINGS ---
_CACHED_ENTRIES = None
_LAST_M_TIME = 0
TOKEN_RE = re.compile(r"[^\w\s]")

def tokenize(text: str, stop_words: set) -> list:
    return [w for w in TOKEN_RE.sub(" ", text.lower()).split() if len(w) > 1 and w not in stop_words] if text else []


def load_context_entries(context_file: str, stop_words: set) -> list:
    global _CACHED_ENTRIES, _LAST_M_TIME
    if not os.path.exists(context_file): return []
    try:
        cur_m = os.path.getmtime(context_file)
        if _CACHED_ENTRIES is not None and cur_m <= _LAST_M_TIME:
            return _CACHED_ENTRIES
        with open(context_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.read().splitlines() if l.strip() and not l.strip().startswith("#") and "--->" in l]
        parsed = []
        for line in lines:
            cmd, intents_str = line.split("--->", 1)
            intents = [i.strip() for i in intents_str.split(",") if i.strip()]
            for intent in intents:
                if tokens := tokenize(intent, stop_words):
                    parsed.append({"cmd": cmd.strip(), "intent": intent, "primary": intents[0], "tokens": tokens})
        _CACHED_ENTRIES, _LAST_M_TIME = parsed, cur_m
        return parsed
    except Exception as e:
        sys.stderr.write(f"\033[1;31m[sys] Error parsing context metadata: {e}\033[0m\n")
        return []


def jaccard_search(query: str, context_file: str, stop_words: set, threshold: float = 0.45) -> str or None:
    q_clean, q_toks = query.strip().lower(), set(tokenize(query, stop_words))
    if not q_toks: return None
    entries = load_context_entries(context_file, stop_words)
    if not entries: return None
    candidates = []
    for entry in entries:
        ent_toks, ent_clean = set(entry["tokens"]), entry["intent"].strip().lower()
        union = q_toks | ent_toks
        score = len(q_toks & ent_toks) / len(union) if union else 0.0
        if q_clean in ent_clean: score = max(score, 0.8)
        if q_clean == ent_clean: score = 3.0
        if score >= threshold:
            candidates.append((score, entry["cmd"], entry.get("primary", entry["intent"])))
    if not candidates: return None
    candidates.sort(key=lambda x: (-x[0], len(x[2])))
    seen, top = set(), []
    for _, cmd, primary in candidates:
        if cmd not in seen and len(top) < 5:
            seen.add(cmd)
            top.append(f"{primary}|||{clean_tool_prefix(cmd)}")
    return "\n".join(top) if top else None


def clean_tool_prefix(cmd: str) -> str:
    is_tool = cmd.startswith("[TOOL]")
    cl = cmd.replace("[TOOL]", "", 1).strip() if is_tool else cmd
    if cl.startswith("DANGER_FLAGGED:"):
        cl = f"DANGER_FLAGGED:{cl.replace('DANGER_FLAGGED:', '').replace('[TOOL]', '').strip()}"
    cl = cl.replace(" --s", "").strip()
    pager = ""
    for flag, pg in [(" --leaf", "leaf"), (" --glow", "glow"), (" --cat", "cat"), (" --mdcat", "mdcat")]:
        if cl.endswith(flag):
            cl, pager = cl[:-len(flag)].strip(), pg
            break
    if not pager and is_tool:
        pager = "mdcat" if shutil.which("mdcat") else "cat"
    return f"{cl} | {pager}" if pager and (pager != "mdcat" or shutil.which("mdcat")) else cl


# --- STATEFUL & CASCADING COMPLETION ENGINES ---
def stream(messages, prefix, gkey, spinner_class, show_stats: bool = True):
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    sf = os.path.join(workspace, ".agent", "session.json")
    saved_id = None
    if os.path.exists(sf):
        try:
            with open(sf, "r", encoding="utf-8") as f:
                saved_id = json.load(f).get("last_interaction_id")
        except Exception: pass
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
                with open(os.path.join(os.path.expanduser("~/.config/local-ai"), ".request_log"), "a", encoding="utf-8") as f:
                    f.write(f"{int(time.time())}|gemini-interactions\n")
            except Exception: pass
            first, acc, resolved_id = True, [], None
            for line in response:
                dec = line.decode("utf-8").strip()
                if not dec: continue
                if dec.startswith("data:"): dec = dec[5:].strip()
                if dec == "[DONE]": continue
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
                            if speed_test and show_stats: speed_test.start()
                        print(content, end="", flush=True)
                        acc.append(content)
                        if speed_test and show_stats: speed_test.count_token(content)
                except Exception: pass
            print("")
            if speed_test and show_stats: speed_test.end()
            if resolved_id:
                try:
                    os.makedirs(os.path.dirname(sf), exist_ok=True)
                    with open(sf, "w", encoding="utf-8") as f:
                        json.dump({"last_interaction_id": resolved_id}, f)
                except Exception: pass
            return "".join(acc)
    except urlerr.HTTPError as e:
        spinner.stop()
        if saved_id and e.code in (400, 404):
            try: os.remove(sf)
            except Exception: pass
        return None
    except Exception:
        spinner.stop()
        return None


def stream_response(messages: list, prefix: str = "AI: ", cfg_dir: str = "", show_stats: bool = False) -> str or None:
    acc, spinner = [], InlineSpinner()
    try:
        gkey = os.environ.get("GEMINI_API_KEY")
        if gkey:
            try:
                ans = stream(messages, prefix, gkey, InlineSpinner, show_stats)
                if ans is not None: return ans
            except Exception: pass
        configs = []
        okey = os.environ.get("OPENROUTER_API_KEY")
        if gkey:
            configs.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {"Authorization": f"Bearer {gkey}"}, os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite"), {}, 30))
        if okey:
            configs.append(("https://openrouter.ai/api/v1/chat/completions", {"Authorization": f"Bearer {okey}", "HTTP-Referer": "https://github.com/j5onrf/local-ai"}, os.environ.get("OPENROUTER_MODEL", "openrouter/free"), {}, 180))
        configs.append(("http://localhost:8080/v1/chat/completions", {}, "local-model", {}, 180))
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
                            if p and cfg_dir:
                                with open(os.path.join(cfg_dir, ".request_log"), "a", encoding="utf-8") as lf:
                                    lf.write(f"{int(time.time())}|{p}\n")
                        except Exception: pass
                        first, resolved_model = True, None
                        for line in response:
                            if not line.startswith(b"data:"): continue
                            content = extract_stream_content(line)
                            if content:
                                if first:
                                    spinner.stop()
                                    if sys.stdout.isatty():
                                        sys.stdout.write(f"\r\x1b[2K\r\033[1;32m{prefix}\033[0m ")
                                        sys.stdout.flush()
                                    first = False
                                    if speed_test and show_stats: speed_test.start()
                                print(content, end="", flush=True)
                                acc.append(content)
                                if speed_test and show_stats: speed_test.count_token(content)
                            else:
                                try:
                                    dec = line.decode("utf-8").strip()
                                    if dec.startswith("data:"): dec = dec[5:].strip()
                                    if dec == "[DONE]" or not dec: continue
                                    data = json.loads(dec)
                                    if "model" in data and not resolved_model:
                                        resolved_model = data["model"]
                                except Exception: pass
                        print("")
                        if speed_test and show_stats: speed_test.end()
                        if resolved_model and resolved_model != model and sys.stdout.isatty():
                            target = os.path.join(os.path.expanduser("~"), "ollama_backup") + "/"
                            disp = resolved_model.replace(target, ".../") if resolved_model.startswith(target) else resolved_model
                            sys.stdout.write(f"\033[90m[via {disp}]\033[0m\n")
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
                        sys.stderr.write(f"\033[90m[sys] {url.split('/')[2]} failed: HTTP {e.code}\033[0m\n")
                        break
                except Exception as e:
                    spinner.stop()
                    sys.stderr.write(f"\033[90m[sys] {url.split('/')[2]} failed: {e}\033[0m\n")
                    break
        sys.stderr.write("\033[1;31mError: All fallbacks/local servers are offline.\033[0m\n\n")
    except KeyboardInterrupt:
        try: spinner.stop()
        except Exception: pass
        sys.stderr.write("\n\r\x1b[2K\r[sys] Interrupted.\n")
        sys.stderr.flush()
        return "".join(acc) if 'acc' in locals() else None
    return None


def get_accurate_token_count(text: str, server_url: str = "http://localhost:8080") -> int:
    try:
        return len(requests.post(f"{server_url}/tokenize", json={"content": text}, timeout=3).json().get("tokens", []))
    except Exception:
        return len(text) // 4


def show_memory_status(messages: list, max_context: int = 8192, server_url: str = "http://localhost:8080") -> None:
    # Resolve max_context dynamically from environment if it was left at the default 8192
    if max_context == 8192:
        try:
            max_context = int(os.environ.get("AI_MAX_TOKENS", 8192))
        except Exception:
            pass

    tot = sum(get_accurate_token_count(m.get("content", ""), server_url) for m in messages)
    pct = (tot / max_context) * 100
    filled = int((tot / max_context) * 20)
    bar = "█" * filled + "░" * (20 - filled)
    sys.stderr.write(f"\n\033[2m[sys] Context Window: {tot}/{max_context} tokens\033[0m\n\033[2m[sys] Usage: [{bar}] {pct:.1f}%\033[0m\n\033[2m[sys] Remaining: {max_context - tot} tokens\033[0m\n\n")
    sys.stderr.flush()
