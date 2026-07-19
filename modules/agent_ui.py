# File: ~/.config/local-ai/modules/agent_ui.py
import os
import sys
import threading
import time
import select
import re
from typing import Optional, Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import DOUBLE, ROUNDED

try:
    import tty
    import termios
except ImportError:
    pass

# Direct shared console instance for standardized UI output
_console = Console()
_console_err = Console(stderr=True)


class InlineSpinner:
    """A lightweight, thread-safe on-demand ANSI terminal spinner for CLI operations with elapsed timer"""
    def __init__(self, chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        self.chars: str = chars
        self.active: bool = False
        self.thread: Optional[threading.Thread] = None
        self.message: str = "Thinking..."
        self.start_time: float = 0.0

    def _spin(self) -> None:
        idx: int = 0
        char_len: int = len(self.chars)
        while self.active:
            try:
                char = self.chars[idx % char_len]
                elapsed = time.time() - self.start_time
                # Renders styled spinner coupled with an active timer
                sys.stderr.write(f"\r\033[1;32m{char}\033[0m \033[36m{self.message}\033[0m \033[2m{elapsed:.1f}s\033[0m ")
                sys.stderr.flush()
            except Exception:
                pass
            idx += 1
            time.sleep(0.08)
        sys.stderr.write("\r\x1b[2K\r")
        sys.stderr.flush()

    def start(self, message: str = "Thinking...") -> None:
        if not self.active:
            self.active = True
            self.message = message
            self.start_time = time.time()
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()

    def stop(self) -> None:
        if self.active:
            self.active = False
            if self.thread:
                self.thread.join()
                self.thread = None


def get_key() -> str:
    """Reads a single key or escape sequence from /dev/tty directly or falls back to stdin.
    
    Uses read-only access on /dev/tty to ensure compatibility inside piped subprocesses.
    """
    try:
        with open("/dev/tty", "r") as tty_file:
            fd = tty_file.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                termios.tcflush(fd, termios.TCIFLUSH)
                char_bytes = os.read(fd, 1)
                if char_bytes == b'\x1b' and select.select([fd], [], [], 0.05)[0]:
                    char_bytes += os.read(fd, 2)
                return char_bytes.decode("utf-8", errors="ignore")
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                termios.tcflush(fd, termios.TCIFLUSH)
                char_bytes = os.read(fd, 1)
                if char_bytes == b'\x1b' and select.select([fd], [], [], 0.05)[0]:
                    char_bytes += os.read(fd, 2)
                return char_bytes.decode("utf-8", errors="ignore")
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            try:
                char_bytes = os.read(fd, 1)
                return char_bytes.decode("utf-8", errors="ignore")
            except Exception:
                return ""


def get_local_model_name() -> str:
    """Queries the running llama-server to extract the actual loaded GGUF filename."""
    import urllib.request as urlreq
    import json
    try:
        with urlreq.urlopen("http://localhost:8080/v1/models", timeout=0.5) as r:
            data = json.loads(r.read().decode("utf-8"))
            model_path = data["data"][0]["id"]
            return os.path.basename(model_path)
    except Exception:
        return "local-model"


def draw_session_box(
    workspace_path: str,
    home_dir: str,
    is_agent: bool,
    db_turns: int,
    tpm_count: int,
    memory_active: bool,
    active_system_prompt: str,
    clean_name: str,
    sub_id: Optional[int] = None
) -> None:
    """Draws a styled system status and metadata information frame using Rich panels."""
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

    gkey = os.environ.get("GEMINI_API_KEY")
    okey = os.environ.get("OPENROUTER_API_KEY")
    clakey = os.environ.get("CLAUDE_API_KEY")
    opakey = os.environ.get("OPENAI_API_KEY")

    if clakey:
        model_name = os.environ.get("CLAUDE_MODEL", "claude-fable-5")
    elif opakey:
        model_name = os.environ.get("OPENAI_MODEL", "gpt-5.5")
    elif gkey:
        model_name = os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite")
    elif okey:
        model_name = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
    else:
        model_name = get_local_model_name()

    # Build the internal key-value layout table
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column("Key", style="dim cyan", justify="right")
    table.add_column("Value", style="green")

    table.add_row("model:", model_name)
    table.add_row("directory:", display_dir)
    table.add_row("skill:", clean_name if clean_name else "default")

    if is_agent:
        mem_status = f"active ({tpm_count} facts, {db_turns} turns)" if memory_active else "disabled"
    else:
        mem_status = "stateless"
    table.add_row("database:", mem_status)

    if sub_id:
        title_text = f" ❖ Local-AI Agent [sub-agent #{sub_id}] "
    else:
        title_text = f" ❖ Local-AI Agent ({version}) " if version else " ❖ Local-AI Agent "

    panel = Panel(
        table,
        title=Text(title_text, style="bold bright_blue"),
        title_align="left",
        border_style="bright_blue",
        box=DOUBLE,
        expand=False,
        subtitle="[dim]Ctrl+C to exit[/dim]",
        subtitle_align="right"
    )

    _console.print(panel)
    
    approx_tokens = len(active_system_prompt) // 4
    _console.print(f"[dim][sys] Startup context: {approx_tokens:,} tokens[/dim]\n")


def confirm_tool(tool: str) -> bool:
    """Prompt user to authorize executing a dynamic tool, defaulting to Yes on Enter."""
    _console_err.print(f"[bold yellow]▲ [sys] Authorize tool:[/bold yellow] [cyan]{tool}[/cyan] [bold yellow]? [Y/n]: [/bold yellow]", end="")
    try:
        char = get_key()
    except Exception:
        char = ""
    is_yes = char.lower() == 'y' or char in ('\r', '\n', '')
    if char in ('\r', '\n', ''):
        sys.stderr.write("y\n")
    elif char.startswith('\x1b') or char == '\x03':
        sys.stderr.write("n\n")
    else:
        sys.stderr.write(f"{char}\n")
    sys.stderr.flush()
    return is_yes


def run_interactive_selection(
    intent: str,
    jaccard_search_fn: Callable[[str], Optional[str]],
    clean_tool_prefix_fn: Callable[[str], str],
    print_stock_error_fn: Callable[[str], None],
    ensure_mysys_exists_fn: Callable[[], None]
) -> None:
    """Displays a menu overlay allowing arrow-selection and execution of mapped tools."""
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
