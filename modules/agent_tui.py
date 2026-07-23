# File: ~/.config/local-ai/modules/agent_tui.py
import os
import sys
import json
import time
import sqlite3
import asyncio
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
from rich.text import Text
from rich.box import DOUBLE, ROUNDED
from rich.console import Group, Console, ConsoleOptions, RenderResult
from rich.syntax import Syntax

# Ensure parent modules path is present on system path
sys.path.append(os.path.expanduser("~/.config/local-ai/modules"))
import agent_cloud
import agent_ui as ui
import agent_core as core

def load_env_file(path: str) -> None:
    """Loads environment configurations dynamically to ensure key parity."""
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
load_env_file(os.path.join(CFG_DIR, ".env"))

# --- Monkey-Patch Screen to completely block standard system commands from Palette ---
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
        "monokai": "#1e1f1c",   # Monokai dark olive-charcoal
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


def inspect_workspace_db(workspace_path: str) -> Tuple[bool, int, int]:
    """Scans workspace and project database store for active memory state."""
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
                        # Match project specific database files
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
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0].lower() for row in cursor.fetchall()]
            
            if not tables:
                conn.close()
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
            
            conn.close()
        except Exception:
            pass
            
    if found_db:
        return True, total_turns, total_facts

    # Project fallback check
    if "/projects/" in workspace_path or os.path.exists(os.path.join(workspace_path, ".git")):
        return True, 0, 0

    return False, 0, 0


# Minimalist themes
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
    primary="#555555",
    secondary="#f8f8f2",
    accent="#ff79c6",
    background="#282a36",
    surface="#21222c",
    panel="#191a21"
)

nord_theme = Theme(
    name="nord",
    primary="#555555",
    secondary="#d8dee9",
    accent="#81a1c1",
    background="#2e3440",
    surface="#242933",
    panel="#1c202a"
)

monokai_theme = Theme(
    name="monokai",
    primary="#f92672",
    secondary="#f8f8f2",
    accent="#a6e22e",
    background="#272822",
    surface="#1e1f1c",
    panel="#141411"
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
    A dynamic chat message widget isolating thinking blocks in real-time.
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
        prefix = "" if compact else "\n"
        
        if self.sender == "User":
            display_text = self.content
            if isinstance(display_text, list):
                display_text = next((item["text"] for item in display_text if item.get("type") == "text"), "[Multimodal]")
            return Group(Text(f"{prefix}❯ USER: {display_text}", style="bold cyan"))
        
        header = Text(f"{prefix}❖ AGENT:", style="bold green")
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
                    title="⚙ Thinking Process...", title_align="left", border_style="yellow", box=ROUNDED, expand=True
                )
                return Group(header, thinking_panel)
        else:
            return Group(header, Markdown(text))

class AgentCommandProvider(Provider):
    """A clean command provider filtering out redundant system commands."""
    async def search(self, query: str) -> Iterator[Hit]:
        matcher = self.matcher(query)
        commands = [
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
    Screen { background: $background; }
    #layout { height: 1fr; }
    #sidebar { width: 32; height: 100%; background: $surface; border-right: double $primary; padding: 1 2; }
    #main-container { height: 100%; width: 1fr; background: transparent; }
    #chat-area { height: 1fr; background: transparent; overflow-y: scroll; padding: 1 2; }
    #input-pane { height: 3; border-top: solid $primary; background: $surface; padding: 0 1; }
    Input { border: none; background: transparent; height: 3; color: $text; }
    Message { margin: 0; height: auto; }
    .sidebar-label { color: $primary; text-style: bold; margin-top: 1; }
    .sidebar-val { color: $secondary; margin-bottom: 1; }
    """

    THEMES: List[str] = ["dark", "grok", "dracula", "nord", "monokai"]

    BINDINGS = [
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=True),
        Binding("ctrl+g", "toggle_compact", "Compact", show=True),
        Binding("ctrl+r", "toggle_reasoning", "Reasoning", show=True),
        Binding("ctrl+t", "cycle_theme", "Theme", show=True),
        Binding("ctrl+y", "attach_image_url", "Image", show=True),
        Binding("ctrl+c", "stop_generation", "Stop Out", show=True),
        Binding("ctrl+q", "quit", "Exit TUI", show=False),      
        Binding("escape", "quit", "Exit TUI", show=False),      
    ]

    def __init__(
        self,
        workspace_path: str,
        model_name: str,
        is_agent: bool = True,
        memory_active: Optional[bool] = None,
        db_turns: int = 0,
        tpm_count: int = 0
    ) -> None:
        super().__init__()
        self.workspace_path: str = workspace_path
        self.model_name: str = model_name
        self.is_agent: bool = is_agent
        
        if memory_active is None:
            active, detected_turns, detected_facts = inspect_workspace_db(workspace_path)
            self.memory_active: bool = active
            self.db_turns: int = detected_turns
            self.tpm_count: int = detected_facts
        else:
            self.memory_active: bool = memory_active
            self.db_turns: int = db_turns
            self.tpm_count: int = tpm_count

        self.compact_mode: bool = False
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
        """Constructs the formatted database status string for the sidebar."""
        if self.is_agent and self.memory_active:
            return f"active ({self.tpm_count} facts, {self.db_turns} turns)"
        return "stateless"

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Static(Text(" ❖ LOCAL-AI AGENT ", style="bold bright_blue"))
                yield Static(Text("─" * 24, style="dim white"))
                
                yield Static("ACTIVE MODEL:", classes="sidebar-label")
                yield Static(self.model_name, id="lbl-model", classes="sidebar-val")
                
                yield Static("WORKSPACE DIR:", classes="sidebar-label")
                yield Static(self.workspace_path.replace(os.path.expanduser("~"), "~"), classes="sidebar-val")
                
                yield Static("REASONING BUDGET:", classes="sidebar-label")
                yield Static("Disabled", id="lbl-reasoning", classes="sidebar-val")
                
                yield Static("IMAGE ATTACHED:", classes="sidebar-label")
                yield Static("None", id="lbl-image", classes="sidebar-val")
                
                yield Static("DATABASE STATE:", classes="sidebar-label")
                yield Static(self.get_db_status_string(), id="lbl-database", classes="sidebar-val")

                yield Static("SESSION STATS:", classes="sidebar-label")
                yield Static("Turns: 0\nSpeed: -- t/s\nElapsed: 0.0s", id="lbl-stats", classes="sidebar-val")
                
            with Vertical(id="main-container"):
                with Vertical(id="chat-area"):
                    yield Static(Panel(
                        Markdown("# Workspace Loaded • Awaiting Instructions\nType your query and press `Enter`.\n`Ctrl+B` toggle sidebar • `Ctrl+T` cycle themes • `Ctrl+G` toggle compact • `Ctrl+R` toggle/configure reasoning."),
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
        self.register_theme(monokai_theme)
        self.register_theme(dark_theme)
        
        self.theme = "dark"
        
        self.chat_area = self.query_one("#chat-area", Vertical)
        self.chat_input = self.query_one("#chat-input", Input)
        self.chat_input.focus()

    def update_stats_ui(self, turns: int, tps: float, elapsed: float) -> None:
        """Updates the sidebar session stats display dynamically."""
        stats_text = f"Turns: {turns}\nSpeed: {tps:.1f} t/s\nElapsed: {elapsed:.1f}s"
        self.query_one("#lbl-stats", Static).update(stats_text)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        self.chat_input.value = ""
        
        if self.entering_reasoning_budget:
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "Ask your agent anything..."
            
            if not query:
                self.reasoning_budget = 500
                self.reasoning_active = True
                self.query_one("#lbl-reasoning", Static).update("500 tokens")
                self.chat_area.mount(Static("[dim yellow][sys] Deep reasoning enabled with default budget: [bold]500 tokens[/bold]"))
            else:
                try:
                    val = int(query)
                    if val > 0:
                        self.reasoning_budget = val
                        self.reasoning_active = True
                        self.query_one("#lbl-reasoning", Static).update(f"{val} tokens")
                        self.chat_area.mount(Static(f"[dim yellow][sys] Deep reasoning enabled with custom budget: [bold]{val} tokens[/bold]"))
                    else:
                        raise ValueError
                except ValueError:
                    self.reasoning_active = False
                    self.query_one("#lbl-reasoning", Static).update("Disabled")
                    self.chat_area.mount(Static("[bold red][sys] Invalid budget. Deep reasoning remains disabled.[/bold red]"))
                
            self.chat_area.scroll_end(animate=False)
            return

        if self.entering_image_url:
            if not query:
                return
            self.entering_image_url = False
            self.active_image_url = query
            self.chat_input.placeholder = "Ask your agent anything..."
            
            filename = query.split("/")[-1].split("?")[0][:25]
            self.query_one("#lbl-image", Static).update(filename or "image_attached")
            
            info_banner = Static(f"[dim yellow][sys] Attached image URL: [bold]{query}[/bold]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
            return

        if not query:
            return

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

    def blocking_stream(self, target_widget: Message) -> None:
        """Executes the network request and streams tokens safely inside a background thread."""
        self.call_from_thread(self.disable_input)
        self.generation_cancelled = False
        self.active_response = None
        accumulated = ""
        in_thinking = False
        
        start_time = time.time()
        
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
            
            elapsed = max(0.01, time.time() - start_time)
            est_tokens = max(1, len(accumulated) // 4)
            tps = est_tokens / elapsed
            self.stats_turns += 1
            self.call_from_thread(self.update_stats_ui, self.stats_turns, tps, elapsed)
            
        except Exception as e:
            if self.generation_cancelled:
                self.call_from_thread(target_widget.update_content, accumulated + " [dim yellow](stopped)[/dim yellow]")
                self.history.append({"role": "assistant", "content": accumulated})
                
                elapsed = max(0.01, time.time() - start_time)
                est_tokens = max(1, len(accumulated) // 4)
                tps = est_tokens / elapsed
                self.stats_turns += 1
                self.call_from_thread(self.update_stats_ui, self.stats_turns, tps, elapsed)
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
            self.chat_area.mount(Static("[dim yellow][sys] Generation stopped by user.[/dim yellow]"))
            self.chat_area.scroll_end(animate=False)
        else:
            self.chat_input.value = ""

    def action_attach_image_url(self) -> None:
        if self.entering_image_url:
            self.entering_image_url = False
            self.chat_input.placeholder = "Ask your agent anything..."
            self.chat_input.value = ""
            info_banner = Static("[dim yellow][sys] Image attachment cancelled.[/dim yellow]")
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
        
        for child in self.chat_area.children:
            if isinstance(child, Message):
                child.refresh()
        
        status = "enabled" if self.compact_mode else "disabled"
        info_banner = Static(f"[dim yellow][sys] Compact spacing mode {status}.[/dim yellow]")
        self.chat_area.mount(info_banner)
        self.chat_area.scroll_end(animate=False)

    def action_cycle_theme(self) -> None:
        try:
            current_idx = self.THEMES.index(self.theme)
            next_idx = (current_idx + 1) % len(self.THEMES)
            self.theme = self.THEMES[next_idx]
            
            info_banner = Static(f"[dim yellow][sys] Theme changed dynamically to: [bold]{self.theme}[/bold]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
        except Exception:
            pass

    def action_toggle_reasoning(self) -> None:
        if self.entering_reasoning_budget:
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "Ask your agent anything..."
            self.chat_input.value = ""
            info_banner = Static("[dim yellow][sys] Reasoning budget setup cancelled.[/dim yellow]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
        elif self.reasoning_active:
            self.reasoning_active = False
            self.query_one("#lbl-reasoning", Static).update("Disabled")
            info_banner = Static("[dim yellow][sys] Deep reasoning disabled.[/dim yellow]")
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
