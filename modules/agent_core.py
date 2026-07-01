#!/usr/bin/env python3
# Local-Ai Agent Core Module [j5onrf] [v0.8.9.9] - Consolidates UI, grammar, Jaccard RAG, and cascading completion streams

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

# --- SECTION 1: TERMINAL & USER INTERFACE UTILITIES ---

class InlineSpinner:
    """A lightweight, thread-safe on-demand ANSI terminal spinner for CLI operations."""

    def __init__(self, chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        self.chars: str = chars
        self.active: bool = False
        self.thread: Optional[threading.Thread] = None

    def _spin(self) -> None:
        idx: int = 0
        char_len: int = len(self.chars)
        while self.active:
            try:
                char = self.chars[idx % char_len]
                sys.stderr.write(f"\r\033[1;32m{char}\033[0m ")
                sys.stderr.flush()
            except Exception:
                pass
            idx += 1
            time.sleep(0.08)
        sys.stderr.write("\r\x1b[2K\r")
        sys.stderr.flush()

    def start(self) -> None:
        """Starts the spinner thread."""
        if not self.active:
            self.active = True
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()

    def stop(self) -> None:
        """Safely stops the spinner thread and joins execution."""
        if self.active:
            self.active = False
            if self.thread:
                self.thread.join()
                self.thread = None


def get_key() -> str:
    """Reads a single key or escape sequence from /dev/tty directly or falls back to stdin."""
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
    except Exception:
        pass

    try:
        old_settings = termios.tcgetattr(fd)
    except Exception:
        try:
            char_bytes = os.read(fd, 1)
            return char_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""
        finally:
            if tty_file:
                tty_file.close()

    try:
        tty.setraw(fd)
        try:
            termios.tcflush(fd, termios.TCIFLUSH)
        except Exception:
            pass
            
        char_bytes = os.read(fd, 1)
        if char_bytes == b'\x1b' and select.select([fd], [], [], 0.05)[0]:
            char_bytes += os.read(fd, 2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        if tty_file:
            tty_file.close()

    return char_bytes.decode("utf-8", errors="ignore")


def prune_history(history: List[Dict[str, str]], max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
    """Prunes old messages from conversation history to stay within context windows."""
    if len(history) <= 1:
        return history

    try:
        target_limit = int(os.environ.get("AI_MAX_TOKENS", 8192)) if max_tokens is None else max_tokens
    except Exception:
        target_limit = 8192

    sys_prompt = history[0]
    current_tokens = len(sys_prompt["content"]) // 4
    selected_messages = []

    for msg in reversed(history[1:]):
        approx_tokens = len(msg["content"]) // 4
        if not selected_messages or (current_tokens + approx_tokens <= target_limit):
            selected_messages.append(msg)
            current_tokens += approx_tokens
        else:
            break

    return [sys_prompt] + list(reversed(selected_messages))


def draw_session_box(
    workspace_path: str,
    home_dir: str,
    is_agent: bool,
    db_turns: int,
    active_system_prompt: str,
    clean_name: str
) -> None:
    """Draws a clean system status and information frame in the console."""
    version = ""
    main_script_path = os.path.join(home_dir, ".config", "local-ai", "ai-agent.py")
    
    if os.path.exists(main_script_path):
        try:
            with open(main_script_path, "r", encoding="utf-8") as f:
                for line in f:
                    match = re.search(r"Local-Ai Agent\s+(v[0-9.]+)", line, re.I)
                    if match:
                        version = match.group(1)
                        break
        except Exception:
            pass

    display_dir = workspace_path
    if display_dir.startswith(home_dir):
        display_dir = display_dir.replace(home_dir, "~", 1)
    if len(display_dir) > 28:
        display_dir = "..." + display_dir[-25:]

    gkey = os.environ.get("GEMINI_API_KEY")
    okey = os.environ.get("OPENROUTER_API_KEY")
    if gkey:
        model_name = os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite")
    elif okey:
        model_name = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
    else:
        model_name = "local-model"

    box_width = 46
    title_line = f" >_ Local-AI Agent ({version})" if version else " >_ Local-AI Agent"
    model_line = f" model:     {model_name}"
    dir_line   = f" directory: {display_dir}"
    skill_line = f" skill:     {clean_name}" if clean_name else " skill:     default"
    mem_line   = f" database:  {db_turns} turns (asleep)" if is_agent else " database:  stateless"
    
    print("\033[1;36m╭" + "─" * box_width + "╮\033[0m")
    print(f"\033[1;36m│\033[0m \033[1;37m{title_line:<{box_width-1}}\033[0m\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m{' ':<{box_width}}\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[2m{model_line:<{box_width-1}}\033[0m\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[2m{dir_line:<{box_width-1}}\033[0m\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[2m{skill_line:<{box_width-1}}\033[0m\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[2m{mem_line:<{box_width-1}}\033[0m\033[1;36m│\033[0m")
    print("\033[1;36m╰" + "─" * box_width + "╯\033[0m")
    
    approx_tokens = len(active_system_prompt) // 4
    print(f"\033[2m[sys] Startup context: {approx_tokens:,} tokens | Ctrl+C to exit.\033[0m\n")


def run_interactive_selection(
    intent: str,
    jaccard_search_fn: Callable[[str], Optional[str]],
    clean_tool_prefix_fn: Callable[[str], str],
    print_stock_error_fn: Callable[[str], None],
    ensure_mysys_exists_fn: Callable[[], None]
) -> None:
    """Displays an menu overlay allowing arrow-selection and execution of mapped tools."""
    if re.search(r'[\[\]{}()=\'"",;|<>#]', intent):
        print_stock_error_fn(intent)
        sys.exit(127)

    matched_base = jaccard_search_fn(intent)
    if not matched_base:
        print_stock_error_fn(intent)
        sys.exit(127)

    options = matched_base.split("\n")
    num_opts = len(options)
    current_idx = 0
    
    sys.stderr.write("\033[?25l")
    sys.stderr.flush()

    try:
        while True:
            current_intent, current_cmd = options[current_idx].split("|||", 1)
            current_cmd = clean_tool_prefix_fn(current_cmd)
            is_danger = current_cmd.startswith("DANGER_FLAGGED:")
            cmd_to_show = current_cmd.replace("DANGER_FLAGGED:", "")
            display_cmd = cmd_to_show.replace(" >/dev/null 2>&1", "").replace(os.path.expanduser("~"), "~")
            
            if "/.config/local-ai/projects/" in display_cmd:
                display_cmd = display_cmd.replace("/.config/local-ai/projects/", "/")

            idx_str = f"{current_idx + 1:02d}/{num_opts:02d}"
            
            if is_danger:
                sys.stderr.write(
                    f"\r\x1b[K\033[1;31m▲ WARNING: Destructive payload detected\033[0m\n"
                    f"\r\x1b[K\033[1;31m[{idx_str}]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n"
                    f"\r\x1b[K\033[2m::\033[0m execute payload? [y/N]: "
                )
            else:
                sys.stderr.write(
                    f"\r\x1b[K\033[1;32m[{idx_str}]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n"
                    f"\r\x1b[K\033[2m::\033[0m ↵ run  Esc: "
                )
            sys.stderr.flush()
            
            key = get_key()
            
            # Non-dangerous selection exits cleanly on any unhandled keypress
            if key in ('\x03', '\x1b') or (not is_danger and key not in ('\r', '', '\x1b[A', '\x1b[B')):
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n")
                sys.stderr.flush()
                break

            if is_danger:
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K")
                sys.stderr.flush()
                if key.lower() == 'y':
                    if "system" in cmd_to_show:
                        ensure_mysys_exists_fn()
                    sys.stdout.write(cmd_to_show)
                else:
                    sys.stderr.write("Aborted safely.\n")
                sys.stdout.flush()
                break

            if key in ('\r', ''):
                sys.stderr.write("\n")
                sys.stderr.flush()
                if "system" in cmd_to_show:
                    ensure_mysys_exists_fn()
                sys.stdout.write(cmd_to_show)
                sys.stdout.flush()
                break
            elif key in ('\x1b[A', '\x1b[B'):
                current_idx = (current_idx + (1 if key == '\x1b[B' else -1) + num_opts) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
        sys.exit(0)
    except KeyboardInterrupt:
        sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n")
        sys.stderr.flush()
        sys.exit(130)
    finally:
        sys.stderr.write("\033[?25h")
        sys.stderr.flush()

    try:
        while True:
            current_intent, current_cmd = options[current_idx].split("|||", 1)
            current_cmd = clean_tool_prefix_fn(current_cmd)
            is_danger = current_cmd.startswith("DANGER_FLAGGED:")
            cmd_to_show = current_cmd.replace("DANGER_FLAGGED:", "")
            display_cmd = cmd_to_show.replace(" >/dev/null 2>&1", "").replace(os.path.expanduser("~"), "~")
            
            if "/.config/local-ai/projects/" in display_cmd:
                display_cmd = display_cmd.replace("/.config/local-ai/projects/", "/")

            idx_str = f"{current_idx + 1:02d}/{num_opts:02d}"
            
            if is_danger:
                sys.stderr.write(
                    f"\r\x1b[K\033[1;31m▲ WARNING: Destructive payload detected\033[0m\n"
                    f"\r\x1b[K\033[1;31m[{idx_str}]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n"
                    f"\r\x1b[K\033[2m::\033[0m execute payload? [y/N]: "
                )
            else:
                sys.stderr.write(
                    f"\r\x1b[K\033[1;32m[{idx_str}]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n"
                    f"\r\x1b[K\033[2m::\033[0m ↵ run  Esc: "
                )
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
                    if "system" in cmd_to_show:
                        ensure_mysys_exists_fn()
                    sys.stdout.write(cmd_to_show)
                else:
                    sys.stderr.write("Aborted safely.\n")
                sys.stdout.flush()
                break

            if key in ('\r', ''):
                sys.stderr.write("\n")
                sys.stderr.flush()
                if "system" in cmd_to_show:
                    ensure_mysys_exists_fn()
                sys.stdout.write(cmd_to_show)
                sys.stdout.flush()
                break
            elif key in ('\x1b[A', '\x1b[B'):
                current_idx = (current_idx + (1 if key == '\x1b[B' else -1) + num_opts) % num_opts
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
    """Prompt user to authorize executing a dynamic tool, defaulting to Yes on Enter."""
    sys.stderr.write(f"\033[1;33m[sys] Authorize tool: {tool}? [Y/n]: \033[0m")
    sys.stderr.flush()
    try:
        char = get_key()
    except Exception:
        char = ""

    is_yes = char.lower() == 'y' or char in ('\r', '\n', '')
    clear_prompt = "\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K"

    if char in ('\r', '\n', ''):
        sys.stderr.write("y\n")
    elif char.startswith('\x1b') or char == '\x03':
        sys.stderr.write("n\n")
    else:
        sys.stderr.write(f"{char}\n")
    sys.stderr.flush()
    
    return is_yes

# --- SECTION 2: SPELLING & GRAMMAR HEURISTICS ---

TYPO_OVERRIDES = {
    "hellow": "hello", "helow": "hello", "helo": "hello",
    "howre": "how are", "wru": "where are you", "hru": "how are you",
    "youa": "you", "trainted": "trained"
}
PROTECTED_WORDS = {"hello", "hi", "hey", "how", "here", "you", "who", "there"}

def load_system_dictionary():
    embedded = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with", "he", "as", "you", 
        "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", 
        "all", "would", "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", "when", 
        "make", "can", "like", "time", "no", "just", "him", "know", "take", "people", "into", "year", "your", "good", "some", 
        "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", 
        "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these", 
        "give", "day", "most", "us", "lazy", "quick", "brown", "fox", "jumps", "dog", "cat", "mat", "sit", "sits", "book", 
        "read", "reads", "spelling", "grammar", "here", "there", "where", "why", "when", "how", "who", "what", "which", "whose",
        "am", "is", "are", "was", "were", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing",
        "write", "writes", "written", "writing", "code", "coder", "coding", "program", "programming", "python", "script",
        "sentence", "errors", "error", "correct", "correction", "spelled", "spelling", "hello", "hi", "hey"
    }
    paths = ["/usr/share/dict/words", "/etc/dictionaries-common/words", "/usr/dict/words"]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    words = {word.strip().lower() for word in f if word.strip().isalpha()}
                    words.update(embedded)
                    return words
            except Exception:
                pass
    return embedded

DICT_WORDS = load_system_dictionary()
DEV_TERMS = {
    "auth", "git", "bash", "zsh", "cli", "tui", "yaml", "json", "ast", "llm", 
    "api", "url", "cmd", "args", "uuid", "md", "txt", "db", "sqlite", "epoxy", "wttr"
}
if DICT_WORDS:
    DICT_WORDS.update(DEV_TERMS)


def edits1(word):
    letters    = 'abcdefghijklmnopqrstuvwxyz'
    splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
    deletes    = [L + R[1:]               for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
    inserts    = [L + c + R               for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)


def correct_word(word):
    if not DICT_WORDS or not word.isalpha() or len(word) < 3:
        return word
    w_lower = word.lower()
    if w_lower in DICT_WORDS:
        return word
    candidates = edits1(w_lower) & DICT_WORDS
    if candidates:
        def edit_priority(cand):
            is_trans = (sorted(cand) == sorted(w_lower))
            diff = len(cand) - len(w_lower)
            prio = 1 if is_trans else 2 if diff == 1 else 3 if diff == 0 else 4
            return (prio, cand)
        
        best = min(candidates, key=edit_priority)
        return best.upper() if word.isupper() else best.capitalize() if word[0].isupper() else best
    return word


def apply_static_overrides(query: str) -> tuple:
    words = re.split(r'(\b[a-zA-Z]+\b)', query)
    corrected_words = []
    changed = False
    for chunk in words:
        if chunk.isalpha():
            w_lower = chunk.lower()
            if w_lower in TYPO_OVERRIDES:
                corrected = TYPO_OVERRIDES[w_lower]
                if chunk.isupper():
                    corrected = corrected.upper()
                elif chunk[0].isupper():
                    corrected = corrected.capitalize()
                corrected_words.append(corrected)
                changed = True
            else:
                corrected_words.append(chunk)
        else:
            corrected_words.append(chunk)
    return "".join(corrected_words), changed


def check_query_spelling_offline(query: str) -> tuple:
    words = re.split(r'(\b[a-zA-Z]+\b)', query)
    corrected_words = []
    changed = False
    for chunk in words:
        if chunk.isalpha():
            corrected = correct_word(chunk)
            if corrected != chunk:
                changed = True
            corrected_words.append(corrected)
        else:
            corrected_words.append(chunk)
    return "".join(corrected_words), changed


def check_query_spelling(query, get_key_fn):
    """Main verification interface. Intercepts typos with static, neural, and TTY fallbacks."""
    original_input = query  # Store the raw original input to compare against at the end
    
    # Layer 1: Apply ultra-fast static overrides first
    query, changed_static = apply_static_overrides(query)
    
    corrected_query = query
    changed = changed_static
    used_grammar_server = False

    # Cascading service list (Local Docker, Local OS package, Public Free Cloud)
    endpoints = [
        "http://localhost:8010/v2/check",
        "http://localhost:8081/v2/check",
        "https://api.languagetool.org/v2/check"
    ]
    
    response_data = None
    for url in endpoints:
        form_data = urlparse.urlencode({'text': query, 'language': 'en-US'}).encode('utf-8')
        req = urlreq.Request(url, data=form_data, method='POST')
        try:
            with urlreq.urlopen(req, timeout=1.2) as r:
                response_data = json.loads(r.read().decode('utf-8'))
                used_grammar_server = True
                break
        except Exception:
            continue

    # Layer 2 & 3: Apply grammar suggestions with First-Letter and Priority safeguards
    if response_data and "matches" in response_data:
        matches = response_data["matches"]
        if matches:
            matches.sort(key=lambda m: m.get("offset", 0), reverse=True)
            chars = list(query)
            for match in matches:
                offset = match.get("offset")
                length = match.get("length")
                replacements = match.get("replacements", [])
                
                if replacements and offset is not None and length is not None:
                    best_correction = replacements[0].get("value")
                    if best_correction is not None:
                        original_word = query[offset : offset + length]
                        
                        # Layer 3 Safeguard A: Don't let grammar engines rewrite valid conversational words
                        if original_word.lower() in PROTECTED_WORDS:
                            continue
                        
                        # Layer 3 Safeguard B: Leverage edit-priority to override weak API substitutions
                        if original_word and best_correction and original_word.isalpha():
                            local_cand = correct_word(original_word)
                            if local_cand != original_word and local_cand.lower() != best_correction.lower():
                                def get_prio(w):
                                    w_low = w.lower()
                                    orig_low = original_word.lower()
                                    return 1 if (sorted(w_low) == sorted(orig_low)) else 2 if len(w_low) - len(orig_low) == 1 else 3 if len(w_low) - len(orig_low) == 0 else 4
                                
                                local_prio = get_prio(local_cand)
                                api_prio = get_prio(best_correction)
                                
                                orig_first = original_word[0].lower()
                                api_first = best_correction[0].lower()
                                local_first = local_cand[0].lower()
                                
                                # Prefer local if it has higher edit priority or preserves first letter
                                if local_prio < api_prio or (api_first != orig_first and local_first == orig_first):
                                    best_correction = local_cand
                        
                        chars[offset : offset + length] = list(best_correction)
                        changed = True
            corrected_query = "".join(chars)

    # Layer 4: Air-gapped fallback to edit-distance checks if servers are completely down
    if not used_grammar_server and not changed_static:
        corrected_query, changed = check_query_spelling_offline(query)

    # Prompt user on change detection, ignoring case-only differences (like lowercase starting words)
    if changed and corrected_query.strip().lower() != original_input.strip().lower():
        sys.stderr.write(
            f"\n\033[2m[sys] Typos detected. Correct query to:\033[0m\n"
            f"\033[3m   \"{corrected_query}\"\033[0m\n"
            f"\033[2m   [↵ accept  Tab: edit  d: disable  Esc: skip]: \033[0m"
        )
        sys.stderr.flush()
        
        key = get_key_fn()
        
        # ANSI Cursor Rollback Sequence: Moves up and clears all 4 printed prompt lines
        clear_prompt = "\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K"

        if key in ('\r', '\n', ''):
            sys.stderr.write(clear_prompt)
            sys.stderr.write("\033[2;32m[sys] Corrected.\033[0m\n")
            sys.stderr.flush()
            return "RUN", corrected_query
        elif key in ('\t', 'e', 'E'):
            sys.stderr.write(clear_prompt)
            sys.stderr.write("\033[2;33m[sys] Returning to editor...\033[0m\n")
            sys.stderr.flush()
            return "EDIT", original_input  # Return the original input for editing
        elif key in ('d', 'D'):
            sys.stderr.write(clear_prompt)
            sys.stderr.write("\033[2;31m[sys] Spellchecker disabled. (Type /e to re-enable)\033[0m\n")
            sys.stderr.flush()
            return "DISABLE", original_input
        else:
            # Erase prompt lines completely, leaving the user's screen pristine
            sys.stderr.write(clear_prompt)
            sys.stderr.flush()
            
    # Default fallback: return original_input to guarantee that skipping (Esc/Arrows) keeps original spelling
    return "RUN", original_input

# --- SECTION 3: JACCARD CONTEXT MAPPINGS ---
_CACHED_ENTRIES = None
_LAST_M_TIME = 0

TOKEN_RE = re.compile(r"[^\w\s]")

def tokenize(text: str, stop_words: set) -> list:
    if not text:
        return []
    cleaned = TOKEN_RE.sub(" ", text.lower())
    return [w for w in cleaned.split() if len(w) > 1 and w not in stop_words]


def load_context_entries(context_file: str, stop_words: set) -> list:
    global _CACHED_ENTRIES, _LAST_M_TIME
    if not os.path.exists(context_file):
        return []
    try:
        current_mtime = os.path.getmtime(context_file)
        if _CACHED_ENTRIES is not None and current_mtime <= _LAST_M_TIME:
            return _CACHED_ENTRIES
            
        with open(context_file, "r", encoding="utf-8") as f:
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
                tokens = tokenize(intent, stop_words)
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
        sys.stderr.write(f"\033[1;31m[sys] Error parsing context metadata: {e}\033[0m\n")
        return []


def jaccard_search(query: str, context_file: str, stop_words: set, threshold: float = 0.45) -> str or None:
    q_clean = query.strip().lower()
    q_tokens = set(tokenize(query, stop_words))
    if not q_tokens:
        return None
        
    entries = load_context_entries(context_file, stop_words)
    if not entries:
        return None
        
    candidates = []
    for entry in entries:
        ent_tokens = set(entry["tokens"])
        ent_clean = entry["intent"].strip().lower()
        
        intersection = q_tokens & ent_tokens
        union = q_tokens | ent_tokens
        score = len(intersection) / len(union) if union else 0.0
        
        if q_clean in ent_clean:
            score = max(score, 0.8)
        if q_clean == ent_clean:
            score = 3.0
            
        if score >= threshold:
            candidates.append((score, entry["cmd"], entry.get("primary", entry["intent"])))
            
    if not candidates:
        return None
        
    candidates.sort(key=lambda x: (-x[0], len(x[2])))
    
    seen = set()
    top_entries = []
    for _, cmd, primary in candidates:
        if cmd not in seen and len(top_entries) < 5:
            seen.add(cmd)
            top_entries.append(f"{primary}|||{clean_tool_prefix(cmd)}")
            
    return "\n".join(top_entries)


def clean_tool_prefix(cmd: str) -> str:
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

# --- SECTION 4: STATEFUL & CASCADING COMPLETION ENGINES ---

def stream(messages, prefix, gkey, spinner_class):
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    sf = os.path.join(workspace, ".agent", "session.json")
    
    saved_id = None
    if os.path.exists(sf):
        try:
            with open(sf, "r", encoding="utf-8") as f:
                saved_id = json.load(f).get("last_interaction_id")
        except Exception:
            pass

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
                cfg_dir = os.path.expanduser("~/.config/local-ai")
                with open(os.path.join(cfg_dir, ".request_log"), "a", encoding="utf-8") as f:
                    f.write(f"{int(time.time())}|gemini-interactions\n")
            except Exception:
                pass
            
            first, acc, resolved_id = True, [], None
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
                        print(content, end="", flush=True)
                        acc.append(content)
                except Exception:
                    pass
            print("")
            
            if resolved_id:
                try:
                    os.makedirs(os.path.dirname(sf), exist_ok=True)
                    with open(sf, "w", encoding="utf-8") as f:
                        json.dump({"last_interaction_id": resolved_id}, f)
                except Exception:
                    pass
            return "".join(acc)
            
    except urlerr.HTTPError as e:
        spinner.stop()
        if saved_id and e.code in (400, 404):
            try:
                os.remove(sf)
            except Exception:
                pass
        return None
    except Exception:
        spinner.stop()
        return None


def stream_response(messages: list, prefix: str = "AI: ", cfg_dir: str = "") -> str or None:
    acc = []
    spinner = InlineSpinner()
    
    try:
        gkey = os.environ.get("GEMINI_API_KEY")
        if gkey:
            try:
                ans = stream(messages, prefix, gkey, InlineSpinner)
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
                            if p and cfg_dir:
                                log_file = os.path.join(cfg_dir, ".request_log")
                                with open(log_file, "a", encoding="utf-8") as lf:
                                    lf.write(f"{int(time.time())}|{p}\n")
                        except Exception:
                            pass
                            
                        first = True
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
        try:
            spinner.stop()
        except Exception:
            pass
        sys.stderr.write("\n\r\x1b[2K\r[sys] Interrupted.\n")
        sys.stderr.flush()
        return "".join(acc) if 'acc' in locals() else None
    return None


def get_accurate_token_count(text: str, server_url: str = "http://localhost:8080") -> int:
    """Queries local llama.cpp / ollama server to get precise token length."""
    try:
        res = requests.post(f"{server_url}/tokenize", json={"content": text}, timeout=3)
        return len(res.json().get("tokens", []))
    except Exception:
        # Fallback to character-count heuristic
        return len(text) // 4


def show_memory_status(messages: list, max_context: int = 8192, server_url: str = "http://localhost:8080") -> None:
    """Visualizes contextual window metrics in the console."""
    total_toks = 0
    for m in messages:
        total_toks += get_accurate_token_count(m.get("content", ""), server_url)
    
    pct = (total_toks / max_context) * 100
    bar_len = 20
    filled = int((total_toks / max_context) * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    
    sys.stderr.write(f"\n\033[2m[sys] Context Window: {total_toks}/{max_context} tokens\033[0m\n")
    sys.stderr.write(f"\033[2m[sys] Usage: [{bar}] {pct:.1f}%\033[0m\n")
    sys.stderr.write(f"\033[2m[sys] Remaining: {max_context - total_toks} tokens\033[0m\n\n")
    sys.stderr.flush()
