# File: ~/.config/local-ai/modules/agent_tui.py
import os
import sys
import json
import time
import base64
import sqlite3
import asyncio
import subprocess
import urllib.request as urlreq
from typing import List, Dict, Any, Optional, Tuple, Iterator, Set

import requests
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, Input, Static
from textual.binding import Binding
from textual.theme import Theme
from textual.command import Provider, Hit
from textual.screen import Screen
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import DOUBLE, ROUNDED
from rich.console import Group, Console, ConsoleOptions, RenderResult
from rich.syntax import Syntax

# Ensure parent modules path is present on system path
sys.path.append(os.path.expanduser("~/.config/local-ai/modules"))
import agent_cloud
import agent_ui as ui
import agent_core as core

try:
    import agent_skills
except ImportError:
    agent_skills = None

def load_env_file(path: str) -> None:
    """Loads environment configurations to ensure key parity."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in (l.strip() for l in f if l.strip() and not l.startswith("#") and "=" in line):
                    k, _, v = line.partition("=")
                    os.environ[k.replace("export ", "", 1).strip()] = v.split(" #")[0].strip().strip('"').strip("'")
        except Exception:
            pass

# Load environmental configs on startup
CFG_DIR: str = os.path.expanduser("~/.config/local-ai")
STATE_FILE: str = os.path.join(CFG_DIR, ".state.json")
load_env_file(os.path.join(CFG_DIR, ".env"))


def load_tui_compact_state() -> bool:
    """Loads persistent compact mode state from .state.json (defaults to False)."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("compact_mode", False))
        except Exception:
            pass
    return False


def save_tui_compact_state(compact_mode: bool) -> None:
    """Saves compact mode state to .state.json while preserving existing keys."""
    data: Dict[str, Any] = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
            
    data["compact_mode"] = compact_mode
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# --- Monkey-Patch Screen to block standard system commands from Palette ---
Screen.command_sources = property(lambda self: set())

# --- Dynamic Rich Markdown Code Block Monkey-Patch ---

def get_dynamic_code_block_background() -> str:
    """Retrieves the ideal code block background color depending on the active TUI theme."""
    try:
        from textual._context import active_app
        app = active_app.get()
        current_theme = getattr(app, "theme", "dark")
    except Exception:
        try:
            current_theme = globals().get("app").theme
        except Exception:
            current_theme = "dark"

    backgrounds = {
        "grok": "#121212",      # Grok panel grey
        "dark": "#242424",      # Dark panel grey
        "dracula": "#21222c",   # Dracula surface purple
        "nord": "#242933",      # Nord slate background
    }
    return backgrounds.get(current_theme, "#121212")

def custom_code_block_rich_console(self: Any, console: Console, options: ConsoleOptions) -> RenderResult:
    """Forces Rich's Pygments engine to use a clean, theme-aware background color."""
    code = str(self.text).rstrip()
    bg_color = get_dynamic_code_block_background()
    yield Syntax(
        code,
        self.lexer_name,
        theme=self.theme,
        word_wrap=True,
        padding=(0, 1),
        background_color=bg_color
    )

fenced_code_class = Markdown.elements.get("fence")
code_block_class = Markdown.elements.get("code_block")

if fenced_code_class:
    fenced_code_class.__rich_console__ = custom_code_block_rich_console
if code_block_class:
    code_block_class.__rich_console__ = custom_code_block_rich_console


def copy_to_clipboard(text: str) -> bool:
    """Copies text to system clipboard using OSC 52 ANSI sequences and OS utilities."""
    if not text:
        return False
        
    try:
        b64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        sys.stdout.write(f"\x1b]52;c;{b64_text}\x07")
        sys.stdout.flush()
    except Exception:
        pass

    tools = [
        ["wl-copy"],                           # Wayland (Linux)
        ["xclip", "-selection", "clipboard"], # X11 (Linux)
        ["xsel", "--clipboard", "--input"],   # X11 (Linux)
        ["pbcopy"],                           # macOS
        ["clip.exe"]                          # Windows WSL
    ]
    
    for tool in tools:
        try:
            p = subprocess.Popen(tool, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            p.communicate(input=text.encode("utf-8"), timeout=1.0)
            if p.returncode == 0:
                return True
        except Exception:
            continue
            
    return True


def inspect_workspace_db(workspace_path: str) -> Tuple[bool, int, int]:
    """Scans workspace and project database store safely for active memory state."""
    proj_name = os.path.basename(os.path.normpath(workspace_path))
    sanitized_path = workspace_path.replace(os.path.expanduser("~"), "").strip("/").replace("/", "-")
    
    search_dirs = [
        workspace_path,
        os.path.join(CFG_DIR, "projects", proj_name),
        os.path.join(CFG_DIR, "projects", "database"),
        os.path.join(CFG_DIR, "projects"),
        CFG_DIR
    ]
    
    db_extensions = (".db", ".sqlite", ".sqlite3")
    candidate_files = []

    for s_dir in search_dirs:
        if os.path.exists(s_dir) and os.path.isdir(s_dir):
            try:
                for fname in os.listdir(s_dir):
                    if fname.endswith(db_extensions) or "memory" in fname.lower() or "db" in fname.lower():
                        if proj_name in fname or sanitized_path in fname or s_dir in (workspace_path, os.path.join(CFG_DIR, "projects", proj_name)):
                            full_p = os.path.join(s_dir, fname)
                            if os.path.isfile(full_p) and full_p not in candidate_files:
                                candidate_files.append(full_p)
            except Exception:
                pass

    total_turns = 0
    total_facts = 0
    found_db = False

    for db_path in candidate_files:
        try:
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0].lower() for row in cursor.fetchall()]
                
                if not tables:
                    continue

                found_db = True
                for t in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM `{t}`")
                        count = cursor.fetchone()[0]
                        if any(k in t for k in ["history", "message", "turn", "chat", "session", "conversation"]):
                            total_turns += count
                        elif any(k in t for k in ["fact", "memory", "vector", "knowledge", "doc", "item"]):
                            total_facts += count
                    except Exception:
                        pass
            finally:
                conn.close()
        except Exception:
            pass
            
    if found_db:
        return True, total_turns, total_facts

    if "/projects/" in workspace_path:
        return True, 0, 0

    return False, 0, 0


# Themes
grok_theme = Theme(
    name="grok",
    primary="#444444",
    secondary="#888888",
    accent="#ffffff",
    background="#000000",
    surface="#0d0d0d",
    panel="#121212"
)

dracula_theme = Theme(
    name="dracula",
    primary="#bd93f9",
    secondary="#f8f8f2",
    accent="#ff79c6",
    background="#282a36",
    surface="#21222c",
    panel="#191a21"
)

nord_theme = Theme(
    name="nord",
    primary="#88c0d0",
    secondary="#d8dee9",
    accent="#81a1c1",
    background="#2e3440",
    surface="#242933",
    panel="#1c202a"
)

dark_theme = Theme(
    name="dark",
    primary="#555555",
    secondary="#b0b0b0",
    accent="#ffffff",
    background="#121212",
    surface="#1c1c1c",
    panel="#242424"
)

class Message(Static):
    """
    A message widget isolating thinking blocks in real-time.
    """
    def __init__(self, sender: str, content: str) -> None:
        super().__init__()
        self.sender: str = sender
        self.content: str = content

    def update_content(self, new_content: str) -> None:
        """Updates the message payload and triggers a repaint."""
        self.content = new_content
        self.refresh()

    def render(self) -> Group:
        compact = getattr(self.app, "compact_mode", False)
        current_theme = getattr(self.app, "theme", "dark")
        prefix = "" if compact else "\n"
        
        if current_theme == "grok":
            user_style = "bold bright_white"
            agent_style = "bold #b0b0b0"
        else:
            user_style = "bold cyan"
            agent_style = "bold green"

        if self.sender == "User":
            display_text = self.content
            if isinstance(display_text, list):
                display_text = next((item["text"] for item in display_text if item.get("type") == "text"), "[Multimodal]")
            return Group(Text(f"{prefix}❯ USER: {display_text}", style=user_style))
        
        header = Text(f"{prefix}❖ AGENT:", style=agent_style)
        text = self.content
        
        if "<think>" in text:
            parts = text.split("<think>", 1)
            before_think = parts[0]
            after_start_think = parts[1]
            
            if "</think>" in after_start_think:
                think_parts = after_start_think.split("</think>", 1)
                thinking_panel = Panel(
                    Text(think_parts[0].strip(), style="italic dim white"),
                    title="⚙ Thinking Process", title_align="left", border_style="bright_black", box=ROUNDED, expand=True
                )
                body_md = Markdown(before_think + think_parts[1].strip()) if (before_think + think_parts[1]).strip() else Text("")
                return Group(header, thinking_panel, body_md)
            else:
                thinking_panel = Panel(
                    Text(after_start_think.strip(), style="italic dim white"),
                    title="⚙ Thinking Process...", title_align="left", border_style="bright_black", box=ROUNDED, expand=True
                )
                return Group(header, thinking_panel)
        else:
            return Group(header, Markdown(text))

class AgentCommandProvider(Provider):
    """A clean command provider filtering out redundant system commands."""
    async def search(self, query: str) -> Iterator[Hit]:
        matcher = self.matcher(query)
        commands = [
            ("Copy Last Response", "copy_last_response", "Copy the latest agent response to system clipboard"),
            ("Attach Image URL", "attach_image_url", "Attach an image URL to analyze on your next query"),
            ("Cycle Theme", "cycle_theme", "Cycle through available color themes"),
            ("Toggle Sidebar", "toggle_sidebar", "Show or hide the metadata panel"),
            ("Toggle Compact Mode", "toggle_compact", "Toggle between dense and spacious spacing layouts"),
            ("Toggle Reasoning", "toggle_reasoning", "Enable or disable deep reasoning budget"),
        ]
        for title, action, desc in commands:
            score = matcher.match(title)
            if score > 0:
                yield Hit(score, Text(title), lambda act=action: self.app.run_action(act), help=desc)

class LocalAITUI(App):
    """
    A high-performance Textual TUI for Local-AI Agent.
    """
    ENABLE_COMMAND_PALETTE = True

    @property
    def command_sources(self) -> Set[Any]:
        return {AgentCommandProvider}

    CSS = """
    Screen { 
        background: $background; 
    }
    
    #layout { 
        height: 1fr; 
    }
    
    #sidebar { 
        width: 32; 
        height: 100%; 
        background: $surface; 
        border-right: double #444444; 
        padding: 1 2; 
    }
    
    #main-container { 
        height: 100%; 
        width: 1fr; 
        background: transparent; 
    }
    
    #chat-area { 
        height: 1fr; 
        background: transparent; 
        overflow-y: scroll; 
        padding: 1 2; 
    }
    
    #input-pane { 
        height: 3; 
        border-top: solid #444444; 
        background: $surface; 
        padding: 0 1; 
    }
    
    Input { 
        border: none; 
        background: transparent; 
        height: 3; 
        color: $text; 
    }
    
    Message { 
        margin: 0; 
        height: auto; 
    }
    
    .sidebar-label { 
        color: $primary; 
        text-style: bold; 
        margin-top: 1; 
    }
    
    #sidebar > .sidebar-label:first-child {
        margin-top: 0;
    }
    
    .sidebar-val { 
        color: $secondary; 
        margin-bottom: 1; 
    }
    """

    THEMES: List[str] = ["dark", "grok", "dracula", "nord"]

    BINDINGS = [
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=True),
        Binding("ctrl+g", "toggle_compact", "Compact", show=True),
        Binding("ctrl+r", "toggle_reasoning", "Reasoning", show=True),
        Binding("ctrl+t", "cycle_theme", "Theme", show=True),
        Binding("ctrl+o", "copy_last_response", "Copy Out", show=True),
        Binding("ctrl+y", "attach_image_url", "Image", show=True),
        Binding("ctrl+c", "stop_generation", "Stop Out", show=True),
        Binding("ctrl+q", "quit", "Exit TUI", show=False),      
        Binding("escape", "quit", "Exit TUI", show=False),      
    ]

    def __init__(
        self,
        workspace_path: str,
        model_name: str,
        is_agent: Optional[bool] = None,
        memory_active: Optional[bool] = None,
        db_turns: int = 0,
        tpm_count: int = 0
    ) -> None:
        super().__init__()
        self.workspace_path: str = workspace_path
        self.model_name: str = model_name
        self.gates_enabled: bool = True
        self.spell_enabled: bool = True
        self.active_skill: str = "default"
        self.pending_skill_prefix: Optional[str] = None
        
        # Auto-detect agent mode (ai init session vs conversational mode)
        if is_agent is None:
            is_agent_env = os.environ.get("AI_IS_AGENT", "").lower() in ("1", "true", "yes")
            self.is_agent: bool = is_agent_env or ("/projects/" in workspace_path)
        else:
            self.is_agent: bool = is_agent
        
        if memory_active is None:
            active, detected_turns, detected_facts = inspect_workspace_db(workspace_path)
            self.memory_active: bool = active if self.is_agent else False
            self.db_turns: int = detected_turns
            self.tpm_count: int = detected_facts
        else:
            self.memory_active: bool = memory_active
            self.db_turns: int = db_turns
            self.tpm_count: int = tpm_count

        self.compact_mode: bool = load_tui_compact_state()
        self.reasoning_active: bool = False
        self.reasoning_budget: int = 500
        self.entering_reasoning_budget: bool = False
        self.active_image_url: Optional[str] = None
        self.entering_image_url: bool = False
        self.history: List[Dict[str, str]] = []
        
        self.generation_cancelled: bool = False
        self.active_response: Optional[Any] = None
        self.stats_turns: int = 0

    def get_db_status_string(self) -> str:
        """Constructs formatted database status: active in agent mode, stateless in conversational mode."""
        if self.is_agent and self.memory_active:
            return f"active ({self.tpm_count} facts, {self.db_turns} turns)"
        return "stateless"

    def update_welcome_banner(self) -> None:
        """Theme-aware banner color renderer."""
        theme_border_colors = {
            "dark": "bright_blue",
            "grok": "#333333",
            "dracula": "#bd93f9",
            "nord": "#88c0d0",
        }
        border_col = theme_border_colors.get(self.theme, "bright_blue")
        
        try:
            banner = self.query_one("#welcome-banner", Static)
            banner.update(Panel(
                Markdown("# Workspace Loaded • Awaiting Instructions\nType your query and press `Enter`.\n`Ctrl+B` toggle sidebar • `Ctrl+T` cycle themes • `Ctrl+G` toggle compact • `Ctrl+R` toggle reasoning • `Ctrl+O` copy response."),
                border_style=border_col,
                box=ROUNDED
            ))
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Static("ACTIVE MODEL:", classes="sidebar-label")
                yield Static(self.model_name, id="lbl-model", classes="sidebar-val")
                
                yield Static("WORKSPACE DIR:", classes="sidebar-label")
                yield Static(self.workspace_path.replace(os.path.expanduser("~"), "~"), classes="sidebar-val")
                
                yield Static("ACTIVE SKILL:", classes="sidebar-label")
                yield Static(self.active_skill, id="lbl-skill", classes="sidebar-val")

                yield Static("REASONING BUDGET:", classes="sidebar-label")
                yield Static("Disabled", id="lbl-reasoning", classes="sidebar-val")

                yield Static("SECURITY GATES:", classes="sidebar-label")
                yield Static("Enabled", id="lbl-gates", classes="sidebar-val")
                
                yield Static("IMAGE ATTACHED:", classes="sidebar-label")
                yield Static("None", id="lbl-image", classes="sidebar-val")
                
                yield Static("DATABASE STATE:", classes="sidebar-label")
                yield Static(self.get_db_status_string(), id="lbl-database", classes="sidebar-val")

                yield Static("SESSION STATS:", classes="sidebar-label")
                yield Static("Turns: 0\nSpeed: -- t/s\nElapsed: 0.0s", id="lbl-stats", classes="sidebar-val")
                
            with Vertical(id="main-container"):
                with Vertical(id="chat-area"):
                    yield Static(Panel(
                        Markdown("# Workspace Loaded • Awaiting Instructions\nType your query and press `Enter`.\n`Ctrl+B` toggle sidebar • `Ctrl+T` cycle themes • `Ctrl+G` toggle compact • `Ctrl+R` toggle reasoning • `Ctrl+O` copy response."),
                        border_style="bright_blue",
                        box=ROUNDED
                    ), id="welcome-banner")
                with Container(id="input-pane"):
                    yield Input(placeholder="Ask your agent anything...", id="chat-input")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(grok_theme)
        self.register_theme(dracula_theme)
        self.register_theme(nord_theme)
        self.register_theme(dark_theme)
        
        self.theme = "dark"
        self.update_welcome_banner()
        
        self.chat_area = self.query_one("#chat-area", Vertical)
        self.chat_input = self.query_one("#chat-input", Input)
        self.chat_input.focus()

    def update_stats_ui(self, turns: int, tps: float, elapsed: float) -> None:
        """Updates the sidebar session stats display accurately."""
        stats_text = f"Turns: {turns}\nSpeed: {tps:.1f} t/s\nElapsed: {elapsed:.1f}s"
        self.query_one("#lbl-stats", Static).update(stats_text)

    def action_copy_last_response(self) -> None:
        """Copies the latest agent message to system clipboard."""
        last_assistant_msg = ""
        for entry in reversed(self.history):
            if entry.get("role") == "assistant":
                last_assistant_msg = entry.get("content", "")
                break
                
        if last_assistant_msg:
            clean_text = last_assistant_msg
            if "</think>" in clean_text:
                clean_text = clean_text.split("</think>", 1)[-1].strip()
                
            copy_to_clipboard(clean_text)
            info_banner = Static("[dim white][sys] Copied latest agent response to clipboard.[/dim white]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
        else:
            info_banner = Static("[dim white][sys] No response available to copy yet.[/dim white]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)

    async def handle_view_file(self, file_path: str) -> None:
        """Reads a file from disk and attaches its content to context."""
        full_p = os.path.expanduser(file_path)
        if not os.path.isabs(full_p):
            full_p = os.path.join(self.workspace_path, file_path)
            
        if os.path.exists(full_p) and os.path.isfile(full_p):
            try:
                with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(12000)
                
                payload_msg = f"[FILE LOADED: {file_path}]\n```\n{content}\n```"
                self.history.append({"role": "user", "content": payload_msg})
                
                info_banner = Static(f"[dim white][sys] Loaded file content into active context: [bold]{file_path}[/bold][/dim white]")
                await self.chat_area.mount(info_banner)
            except Exception as e:
                await self.chat_area.mount(Static(f"[bold red][sys] Error reading file: {e}[/bold red]"))
        else:
            await self.chat_area.mount(Static(f"[bold red][sys] File not found: {file_path}[/bold red]"))
            
        self.chat_area.scroll_end(animate=False)

    async def handle_slash_command(self, cmd: str) -> None:
        """Full Agent Slash Command Interceptor matching CLI parity."""
        parts = cmd.split(maxsplit=1)
        root = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if root in ("/help", "/h"):
            help_table = Table(show_header=False, box=None, padding=(0, 1))
            help_table.add_column("Command", style="bold cyan")
            help_table.add_column("Description", style="white")
            
            help_table.add_row("/help, /h", "Show this complete slash command cheat sheet")
            help_table.add_row("/g", "Toggle tool security confirmation gates")
            help_table.add_row("/m", "Toggle workspace long-term memory")
            help_table.add_row("/clear, /reset", "Clear chat window & turn history")
            help_table.add_row("/tok", "Show active conversation token estimate")
            help_table.add_row("/sync, /re", "Sync codebase AST & graph index")
            help_table.add_row("/spell, /sp", "Toggle spellchecker")
            help_table.add_row("/skill <q>, /s", "Search and load custom skills")
            help_table.add_row("/compact, /c", "Toggle compact spacing mode")
            help_table.add_row("/t, /thinking", "Toggle or set reasoning budget")
            help_table.add_row("/f, /tk, /b, /a", "Follow-up, Thinking, Brainstorm, or All mode")
            help_table.add_row("view file <path>", "Load file content directly into context")
            help_table.add_row("exit, quit, q", "Exit TUI back to shell")

            help_panel = Panel(
                help_table,
                title="⚙ Full Agent TUI Commands",
                title_align="left",
                border_style="bright_blue",
                box=ROUNDED
            )
            await self.chat_area.mount(Static(help_panel))

        elif root in ("exit", "quit", "q"):
            self.exit()

        elif root == "/g":
            self.gates_enabled = not self.gates_enabled
            status_str = "Enabled" if self.gates_enabled else "Disabled"
            self.query_one("#lbl-gates", Static).update(status_str)
            await self.chat_area.mount(Static(f"[dim white][sys] Tool confirmation gates {status_str.lower()}.[/dim white]"))

        elif root in ("/clear", "/reset"):
            self.history.clear()
            self.stats_turns = 0
            self.update_stats_ui(0, 0.0, 0.0)
            for child in list(self.chat_area.children):
                child.remove()
            await self.chat_area.mount(Static("[dim white][sys] Session history and chat window cleared.[/dim white]"))

        elif root == "/m":
            self.memory_active = not self.memory_active
            db_lbl = self.get_db_status_string()
            self.query_one("#lbl-database", Static).update(db_lbl)
            status_str = "active" if (self.is_agent and self.memory_active) else "disabled/stateless"
            await self.chat_area.mount(Static(f"[dim white][sys] Workspace database memory {status_str}.[/dim white]"))

        elif root == "/tok":
            est_tokens = sum(len(m.get("content", "")) // 4 for m in self.history)
            await self.chat_area.mount(Static(f"[dim white][sys] Active conversation history: ~{est_tokens:,} tokens ({len(self.history)} messages)[/dim white]"))

        elif root in ("/sync", "/re"):
            await self.chat_area.mount(Static("[dim white][sys] Triggered background AST & codebase graph sync.[/dim white]"))
            try:
                subprocess.Popen(["index-map"], cwd=self.workspace_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        elif root in ("/spell", "/sp"):
            self.spell_enabled = not self.spell_enabled
            status_str = "enabled" if self.spell_enabled else "disabled"
            await self.chat_area.mount(Static(f"[dim white][sys] Spellchecker {status_str}.[/dim white]"))

        elif root in ("/skill", "/s"):
            if args:
                if agent_skills is not None:
                    try:
                        skills_dir = os.path.join(CFG_DIR, "skills")
                        content = agent_skills.load_skill_content(args, skills_dir, CFG_DIR)
                        if content:
                            if isinstance(content, tuple):
                                s_name, s_text = content[0], content[1]
                            else:
                                s_name, s_text = args, content

                            self.active_skill = s_name
                            self.query_one("#lbl-skill", Static).update(s_name)
                            self.history.append({"role": "system", "content": f"[SKILL BLUEPRINT LOADED: {s_name}]\n{s_text}"})
                            await self.chat_area.mount(Static(f"[dim white][sys] Loaded skill blueprint into LLM context: [bold]{s_name}[/bold][/dim white]"))
                        else:
                            await self.chat_area.mount(Static(f"[dim white][sys] Searched skills for '[bold]{args}[/bold]' (no blueprint file found).[/dim white]"))
                    except Exception as e:
                        await self.chat_area.mount(Static(f"[dim white][sys] Skill search error: {e}[/dim white]"))
                else:
                    self.active_skill = args
                    self.query_one("#lbl-skill", Static).update(args)
                    await self.chat_area.mount(Static(f"[dim white][sys] Skill query active: [bold]{args}[/bold][/dim white]"))
            else:
                await self.chat_area.mount(Static("[dim white][sys] Usage: /skill <query> or /s <query>[/dim white]"))

        elif root in ("/compact", "/c"):
            self.action_toggle_compact()

        elif root in ("/t", "/thinking"):
            self.action_toggle_reasoning()

        elif root in ("/f", "/tk", "/b", "/a"):
            prefix_map = {
                "/f": ("[FOLLOW-UP]", "follow-up"),
                "/tk": ("[THINKING]", "thinking"),
                "/b": ("[BRAINSTORM]", "brainstorm"),
                "/a": ("[AGENTIC-ALL]", "all")
            }
            tag, s_label = prefix_map.get(root, ("", "default"))
            self.active_skill = s_label
            self.query_one("#lbl-skill", Static).update(s_label)
            
            if args:
                await self.submit_query(f"{tag} {args}")
            else:
                self.pending_skill_prefix = tag
                self.chat_input.placeholder = f"Enter {tag} prompt..."
                await self.chat_area.mount(Static(f"[dim white][sys] Skill mode {tag} armed for next prompt.[/dim white]"))

        else:
            await self.chat_area.mount(Static(f"[dim white][sys] Unknown command '{root}'. Type [bold]/help[/bold] for available commands.[/dim white]"))

        self.chat_area.scroll_end(animate=False)

    async def submit_query(self, query: str) -> None:
        """Processes a chat query through the LLM execution pipeline."""
        try:
            self.query_one("#welcome-banner").remove()
        except Exception:
            pass

        user_message = Message("User", query)
        await self.chat_area.mount(user_message)
        
        assistant_message = Message("Agent", "Thinking...")
        await self.chat_area.mount(assistant_message)
        
        self.chat_area.scroll_end(animate=False)
        
        if self.active_image_url:
            user_payload = {
                "role": "user",
                "content": [
                    {"type": "text", "text": query},
                    {"type": "image_url", "image_url": {"url": self.active_image_url}}
                ]
            }
            self.history.append(user_payload)
            self.active_image_url = None  
            self.query_one("#lbl-image", Static).update("None")
        else:
            self.history.append({"role": "user", "content": query})
        
        self.run_worker(lambda: self.blocking_stream(assistant_message), thread=True)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        self.chat_input.value = ""
        
        if not query:
            return

        if self.pending_skill_prefix:
            query = f"{self.pending_skill_prefix} {query}"
            self.pending_skill_prefix = None
            self.chat_input.placeholder = "Ask your agent anything..."

        if query.lower() in ("exit", "quit", "q"):
            self.exit()
            return

        if query.lower().startswith("view file "):
            file_p = query[10:].strip()
            await self.handle_view_file(file_p)
            return

        if query.startswith("/"):
            await self.handle_slash_command(query)
            return

        if self.entering_reasoning_budget:
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "Ask your agent anything..."
            
            if not query:
                self.reasoning_budget = 500
                self.reasoning_active = True
                self.query_one("#lbl-reasoning", Static).update("500 tokens")
                self.chat_area.mount(Static("[dim white][sys] Deep reasoning enabled with default budget: [bold]500 tokens[/bold][/dim white]"))
            else:
                try:
                    val = int(query)
                    if val > 0:
                        self.reasoning_budget = val
                        self.reasoning_active = True
                        self.query_one("#lbl-reasoning", Static).update(f"{val} tokens")
                        self.chat_area.mount(Static(f"[dim white][sys] Deep reasoning enabled with custom budget: [bold]{val} tokens[/bold][/dim white]"))
                    else:
                        raise ValueError
                except ValueError:
                    self.reasoning_active = False
                    self.query_one("#lbl-reasoning", Static).update("Disabled")
                    self.chat_area.mount(Static("[bold red][sys] Invalid budget. Deep reasoning remains disabled.[/bold red]"))
                
            self.chat_area.scroll_end(animate=False)
            return

        if self.entering_image_url:
            self.entering_image_url = False
            self.active_image_url = query
            self.chat_input.placeholder = "Ask your agent anything..."
            
            filename = query.split("/")[-1].split("?")[0][:25]
            self.query_one("#lbl-image", Static).update(filename or "image_attached")
            
            info_banner = Static(f"[dim white][sys] Attached image URL: [bold]{query}[/bold][/dim white]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
            return

        await self.submit_query(query)

    def blocking_stream(self, target_widget: Message) -> None:
        """Executes network request & calculates true token generation speed (decoding throughput)."""
        self.call_from_thread(self.disable_input)
        self.generation_cancelled = False
        self.active_response = None
        accumulated = ""
        in_thinking = False
        
        start_time = time.time()
        first_token_time: Optional[float] = None
        token_count: int = 0
        
        try:
            thinking_budget = self.reasoning_budget if self.reasoning_active else 0
            configs = []
            
            if agent_cloud is not None:
                configs = agent_cloud.get_active_configs(self.history)
            
            local_extra: Dict[str, Any] = {}
            if thinking_budget > 0:
                local_extra["thinking_budget_tokens"] = thinking_budget
                local_extra["chat_template_kwargs"] = {"enable_thinking": True}
            else:
                local_extra["chat_template_kwargs"] = {"enable_thinking": False}

            if configs:
                url, headers, body, timeout = configs[0]
                if thinking_budget > 0:
                    body["thinking_budget_tokens"] = thinking_budget
            else:
                local_url = "http://localhost:8080/v1/chat/completions"
                local_body = {
                    "messages": self.history,
                    "stream": True,
                    "model": "local-model",
                    **local_extra
                }
                configs = [(local_url, {}, local_body, 180)]
                
            url, headers, body, timeout = configs[0]
            body["stream"] = True
            body["messages"] = self.history
            
            req = urlreq.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", **headers},
                method="POST"
            )
            
            with urlreq.urlopen(req, timeout=timeout) as response:
                self.active_response = response
                if response.status != 200:
                    err_text = response.read().decode("utf-8", errors="ignore")[:200]
                    raise Exception(f"HTTP {response.status}: {err_text}")

                for line in response:
                    if self.generation_cancelled:
                        break
                    if not line.startswith(b"data:"):
                        continue
                    
                    res = core.extract_stream_content(line)
                    if not res:
                        continue
                    
                    if isinstance(res, tuple):
                        text_chunk = res[0] or ""
                        thinking_chunk = res[1] if len(res) > 1 else ""
                        thinking_chunk = thinking_chunk or ""
                    else:
                        text_chunk = str(res)
                        thinking_chunk = ""

                    if text_chunk or thinking_chunk:
                        if first_token_time is None:
                            first_token_time = time.time()
                        token_count += 1

                    if thinking_chunk:
                        if not in_thinking:
                            accumulated += "<think>"
                            in_thinking = True
                        accumulated += thinking_chunk
                    
                    if text_chunk:
                        if in_thinking:
                            accumulated += "</think>"
                            in_thinking = False
                        accumulated += text_chunk

                    if text_chunk or thinking_chunk:
                        self.call_from_thread(target_widget.update_content, accumulated)
                        self.call_from_thread(self.chat_area.scroll_end, animate=False)
            
            if in_thinking:
                accumulated += "</think>"
                
            self.history.append({"role": "assistant", "content": accumulated})
            
            end_time = time.time()
            total_elapsed = max(0.01, end_time - start_time)
            
            if first_token_time is not None and token_count > 0:
                gen_duration = max(0.001, end_time - first_token_time)
                tps = token_count / gen_duration
            else:
                tps = (len(accumulated) // 4) / total_elapsed

            self.stats_turns += 1
            self.call_from_thread(self.update_stats_ui, self.stats_turns, tps, total_elapsed)
            
        except Exception as e:
            end_time = time.time()
            total_elapsed = max(0.01, end_time - start_time)
            
            if self.generation_cancelled:
                self.call_from_thread(target_widget.update_content, accumulated + " [dim white](stopped)[/dim white]")
                self.history.append({"role": "assistant", "content": accumulated})
                
                if first_token_time is not None and token_count > 0:
                    gen_duration = max(0.001, end_time - first_token_time)
                    tps = token_count / gen_duration
                else:
                    tps = (len(accumulated) // 4) / total_elapsed

                self.stats_turns += 1
                self.call_from_thread(self.update_stats_ui, self.stats_turns, tps, total_elapsed)
            else:
                self.call_from_thread(target_widget.update_content, f"[red][sys] Error: {e}[/red]")
        finally:
            self.active_response = None
            self.call_from_thread(self.enable_input)

    def disable_input(self) -> None:
        self.chat_input.disabled = True

    def enable_input(self) -> None:
        self.chat_input.disabled = False
        self.chat_input.focus()

    def action_stop_generation(self) -> None:
        if self.chat_input.disabled:
            self.generation_cancelled = True
            if self.active_response:
                try:
                    self.active_response.close()
                except Exception:
                    pass
            self.chat_area.mount(Static("[dim white][sys] Generation stopped by user.[/dim white]"))
            self.chat_area.scroll_end(animate=False)
        else:
            self.chat_input.value = ""

    def action_attach_image_url(self) -> None:
        if self.entering_image_url:
            self.entering_image_url = False
            self.chat_input.placeholder = "Ask your agent anything..."
            self.chat_input.value = ""
            info_banner = Static("[dim white][sys] Image attachment cancelled.[/dim white]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
        else:
            self.entering_image_url = True
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "Enter Web Image URL (http://... or https://...):"
            self.chat_input.focus()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display

    def action_toggle_maximized(self) -> None:
        pass

    def action_toggle_compact(self) -> None:
        self.compact_mode = not self.compact_mode
        save_tui_compact_state(self.compact_mode)
        
        for child in self.chat_area.children:
            if isinstance(child, Message):
                child.refresh()
        
        status = "enabled" if self.compact_mode else "disabled"
        info_banner = Static(f"[dim white][sys] Compact spacing mode {status}.[/dim white]")
        self.chat_area.mount(info_banner)
        self.chat_area.scroll_end(animate=False)

    def action_cycle_theme(self) -> None:
        try:
            current_idx = self.THEMES.index(self.theme)
            next_idx = (current_idx + 1) % len(self.THEMES)
            self.theme = self.THEMES[next_idx]
            
            self.update_welcome_banner()
            
            for child in self.chat_area.children:
                if isinstance(child, Message):
                    child.refresh()
            
            info_banner = Static(f"[dim white][sys] Theme changed to: [bold]{self.theme}[/bold][/dim white]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
        except Exception:
            pass

    def action_toggle_reasoning(self) -> None:
        if self.entering_reasoning_budget:
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "Ask your agent anything..."
            self.chat_input.value = ""
            info_banner = Static("[dim white][sys] Reasoning budget setup cancelled.[/dim white]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
        elif self.reasoning_active:
            self.reasoning_active = False
            self.query_one("#lbl-reasoning", Static).update("Disabled")
            info_banner = Static("[dim white][sys] Deep reasoning disabled.[/dim white]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
        else:
            self.entering_reasoning_budget = True
            self.entering_image_url = False
            self.chat_input.placeholder = "Enter Reasoning Budget (Press Enter for default 500):"
            self.chat_input.focus()

if __name__ == "__main__":
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())

    try:
        configs = []
        if agent_cloud is not None:
            configs = agent_cloud.get_active_configs([])
        if configs:
            model = configs[0][2].get("model", "local-model")
        else:
            model = ui.get_local_model_name()
    except Exception:
        try:
            model = ui.get_local_model_name()
        except Exception:
            model = "local-model"
            
    app = LocalAITUI(workspace, model)
    app.run()
