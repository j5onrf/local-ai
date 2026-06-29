# File: /home/j5/.config/local-ai/tools/modules/ux.py [v0.8.9.8]
# Description: On-demand terminal UI, input handlers, and layout helpers

import sys
import re
import os
import json
import threading
import time
import tty
import termios
import select
from typing import List, Dict, Callable, Optional


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
                # Dynamic modulo prevents IndexErrors and resolves screen stutter
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
        # Open /dev/tty directly to bypass redirected standard input streams
        tty_file = open("/dev/tty", "r+")
        fd = tty_file.fileno()
    except Exception:
        fd = sys.stdin.fileno()

    # Clear O_NONBLOCK flag to guarantee blocking keyboard reads
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
            # Fallback for non-TTY or unconfigurable terminals
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
        # Check for multi-byte escape sequences (e.g., arrow keys)
        if char_bytes == b'\x1b' and select.select([fd], [], [], 0.05)[0]:
            char_bytes += os.read(fd, 2)
    finally:
        # Guarantee restoration of the old terminal state under any failure
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
    # Heuristic to approximate token usage: characters divided by 4
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
    jaccard_search: Callable[[str], Optional[str]],
    clean_tool_prefix: Callable[[str], str],
    print_stock_error: Callable[[str], None],
    ensure_mysys_exists: Callable[[], None]
) -> None:
    """Displays an menu overlay allowing arrow-selection and execution of mapped tools."""
    if re.search(r'[\[\]{}()=\'"",;|<>#]', intent):
        print_stock_error(intent)
        sys.exit(127)

    matched_base = jaccard_search(intent)
    if not matched_base:
        print_stock_error(intent)
        sys.exit(127)

    options = matched_base.split("\n")
    num_opts = len(options)
    current_idx = 0
    
    # Hide the terminal cursor
    sys.stderr.write("\033[?25l")
    sys.stderr.flush()

    try:
        while True:
            current_intent, current_cmd = options[current_idx].split("|||", 1)
            current_cmd = clean_tool_prefix(current_cmd)
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
                        ensure_mysys_exists()
                    sys.stdout.write(cmd_to_show)
                else:
                    sys.stderr.write("Aborted safely.\n")
                sys.stdout.flush()
                break

            if key in ('\r', ''):
                sys.stderr.write("\n")
                sys.stderr.flush()
                if "system" in cmd_to_show:
                    ensure_mysys_exists()
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
        # Always restore terminal cursor state
        sys.stderr.write("\033[?25h")
        sys.stderr.flush()


def confirm_tool(tool: str) -> bool:
    """Prompt user to authorize executing a dynamic tool, defaulting to Yes on Enter and Esc/Arrows to No."""
    sys.stderr.write(f"\033[1;33m[sys] Authorize tool: {tool}? [Y/n]: \033[0m")
    sys.stderr.flush()
    try:
        char = get_key()
    except Exception:
        char = ""

    # Return key or empty input defaults to Yes (Enter)
    is_yes = char.lower() == 'y' or char in ('\r', '\n', '')

    # Clean terminal feedback: if they hit Enter, write 'y'.
    if char in ('\r', '\n', ''):
        sys.stderr.write("y\n")
    # If they press Esc, an Arrow key, or Ctrl+C, print 'n' cleanly and decline the tool
    elif char.startswith('\x1b') or char == '\x03':
        sys.stderr.write("n\n")
    else:
        sys.stderr.write(f"{char}\n")
    sys.stderr.flush()
    
    return is_yes
