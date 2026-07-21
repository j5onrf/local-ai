import os
import sys
import json
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
import agent_ui
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
            # Fallback if context is unavailable (e.g. rendering outside main thread context)
            current_theme = globals().get("app").theme
        except Exception:
            current_theme = "dark"

    backgrounds = {
        "grok": "#121212",      # Grok panel grey (stands out on pitch black #000000 background)
        "dark": "#242424",      # Dark panel grey (stands out on dark theme's #121212 background)
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

# Retrieve the exact classes used by Rich for parsing and rendering code blocks
fenced_code_class = Markdown.elements.get("fence")
code_block_class = Markdown.elements.get("code_block")

# Apply the patches directly to the active element class render loops
if fenced_code_class:
    fenced_code_class.__rich_console__ = custom_code_block_rich_console
if code_block_class:
    code_block_class.__rich_console__ = custom_code_block_rich_console

# Minimalist, high-performance pure black and carbon grey Grok theme
grok_theme = Theme(
    name="grok",
    primary="#444444",      # Muted grey border outlines
    secondary="#888888",    # Soft silver-grey metadata
    accent="#ffffff",       # Bright white highlights
    background="#000000",   # True pitch-black backdrop
    surface="#0d0d0d",      # Dark grey panels
    panel="#121212"
)

dracula_theme = Theme(
    name="dracula",
    primary="#555555",      # Charcoal borders
    secondary="#f8f8f2",    # Dim white accent
    accent="#ff79c6",       # Pink highlight
    background="#282a36",   # Midnight purple
    surface="#21222c",      # Subdued purple
    panel="#191a21"
)

nord_theme = Theme(
    name="nord",
    primary="#555555",      # Charcoal borders
    secondary="#d8dee9",    # Silver frost accent
    accent="#81a1c1",       # Subdued steel blue
    background="#2e3440",   # Dark slate background
    surface="#242933",      # Surface slate
    panel="#1c202a"
)

monokai_theme = Theme(
    name="monokai",
    primary="#f92672",      # Hot pink border accent
    secondary="#f8f8f2",    # Off white accent
    accent="#a6e22e",       # Lime green highlights
    background="#272822",   # Dark olive-charcoal background
    surface="#1e1f1c",      # Subdued charcoal
    panel="#141411"
)

dark_theme = Theme(
    name="dark",
    primary="#555555",      # Charcoal borders
    secondary="#b0b0b0",    # Soft silver accent
    accent="#ffffff",       # White text
    background="#121212",   # Matte black background
    surface="#1c1c1c",      # Standard dark surface
    panel="#242424"
)

class Message(Static):
    """
    A dynamic chat message widget. Isolates ... think ... blocks in real-time to render clean thinking process panels.
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
        # Dynamically sense the TUI's active spacing configuration state
        compact = getattr(self.app, "compact_mode", False)
        prefix = "" if compact else "\n"
        
        if self.sender == "User":
            display_text = self.content
            if isinstance(display_text, list):
                display_text = next((item["text"] for item in display_text if item.get("type") == "text"), "[Multimodal]")
            return Group(Text(f"{prefix}❯ USER: {display_text}", style="bold cyan"))
        
        # Agent Turn Rendering
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
                body_md = Markdown(think_parts[1].strip()) if think_parts[1].strip() else Text("")
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
            ("Set Reasoning Budget", "set_reasoning_budget", "Set a custom token budget for deep reasoning"),
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
    Mirrors x-build double-pane formatting with full dynamic theme support.
    """
    ENABLE_COMMAND_PALETTE = True

    @property
    def command_sources(self) -> Set[Any]:
        return {AgentCommandProvider}

    # Restored standard, comfortable padding by default
    CSS = """
    Screen { background: $background; }
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
        Binding("ctrl+q", "quit", "Exit TUI", show=False),      # Hides the exit button from footer
        Binding("escape", "quit", "Exit TUI", show=False),      # Hides the exit button from footer
    ]

    def __init__(self, workspace_path: str, model_name: str) -> None:
        super().__init__()
        self.workspace_path: str = workspace_path
        self.model_name: str = model_name
        self.compact_mode: bool = False
        self.reasoning_active: bool = False
        self.reasoning_budget: int = 500
        self.entering_reasoning_budget: bool = False
        self.active_image_url: Optional[str] = None
        self.entering_image_url: bool = False
        self.history: List[Dict[str, str]] = []
        
        # Generation control states
        self.generation_cancelled: bool = False
        self.active_response: Optional[Any] = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Static(Text(" ❖ LOCAL-AI AGENT ", style="bold bright_blue"))
                yield Static(Text("─" * 28, style="dim white"))
                
                yield Static("ACTIVE MODEL:", classes="sidebar-label")
                yield Static(self.model_name, id="lbl-model", classes="sidebar-val")
                yield Static("WORKSPACE DIR:", classes="sidebar-label")
                yield Static(self.workspace_path.replace(os.path.expanduser("~"), "~"), classes="sidebar-val")
                yield Static("REASONING BUDGET:", classes="sidebar-label")
                yield Static("Disabled", id="lbl-reasoning", classes="sidebar-val")
                yield Static("IMAGE ATTACHED:", classes="sidebar-label")
                yield Static("None", id="lbl-image", classes="sidebar-val")
                yield Static("DATABASE STATE:", classes="sidebar-label")
                yield Static("stateless", classes="sidebar-val")
                
            with Vertical(id="main-container"):
                with Vertical(id="chat-area"):
                    # Restored the beautiful original rounded welcome box
                    yield Static(Panel(
                        Markdown("# Workspace Loaded • Awaiting Instructions\nType your query and press `Enter`.\n`Ctrl+B` toggle sidebar • `Ctrl+T` cycle themes • `Ctrl+G` toggle compact • `Ctrl+R` toggle/configure reasoning."),
                        border_style="bright_blue",
                        box=ROUNDED
                    ), id="welcome-banner")
                with Container(id="input-pane"):
                    yield Input(placeholder="Ask your agent anything...", id="chat-input")
        yield Footer()

    def on_mount(self) -> None:
        # Register all custom themes into the theme manager
        self.register_theme(grok_theme)
        self.register_theme(dracula_theme)
        self.register_theme(nord_theme)
        self.register_theme(monokai_theme)
        self.register_theme(dark_theme)
        
        # Set dark as the initial default theme on startup
        self.theme = "dark"
        
        self.chat_area = self.query_one("#chat-area", Vertical)
        self.chat_input = self.query_one("#chat-input", Input)
        self.chat_input.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        self.chat_input.value = ""
        
        # 1. Custom unified reasoning budget input capture
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

        # 2. Check if the user is inputting a dynamic image URL
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
        
        # Format multi-modal payloads natively if an active image is attached
        if self.active_image_url:
            user_payload = {
                "role": "user",
                "content": [
                    {"type": "text", "text": query},
                    {"type": "image_url", "image_url": {"url": self.active_image_url}}
                ]
            }
            self.history.append(user_payload)
            self.active_image_url = None  # Consumed, reset state
            self.query_one("#lbl-image", Static).update("None")
        else:
            self.history.append({"role": "user", "content": query})
        
        # Uses Textual's high-performance synchronous worker thread wrapper (thread=True)
        self.run_worker(lambda: self.blocking_stream(assistant_message), thread=True)

    def blocking_stream(self, target_widget: Message) -> None:
        """Executes the network request and streams tokens safely inside a background thread."""
        self.call_from_thread(self.disable_input)
        self.generation_cancelled = False
        self.active_response = None
        accumulated = ""
        
        try:
            # Match standard CLI reasoning parameters dynamically from custom setting
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
                # Inject reasoning parameters to active cloud body
                url, headers, body, timeout = configs[0]
                if thinking_budget > 0:
                    body["thinking_budget_tokens"] = thinking_budget
            else:
                # Dynamic GGUF/Local Fallback Cascade with identical local-model logic
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
            
            # Replicating agent_core's highly stable urllib request pipeline
            req = urlreq.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", **headers},
                method="POST"
            )
            
            with urlreq.urlopen(req, timeout=timeout) as response:
                self.active_response = response
                # Catch API Key validation errors / bad requests immediately
                if response.status != 200:
                    err_text = response.read().decode("utf-8", errors="ignore")[:200]
                    raise Exception(f"HTTP {response.status}: {err_text}")

                for line in response:
                    if self.generation_cancelled:
                        break
                    if not line.startswith(b"data:"):
                        continue
                    
                    content = core.extract_stream_content(line)
                    if content:
                        accumulated += content
                        # Safely update the widget state on the main thread
                        self.call_from_thread(target_widget.update_content, accumulated)
                        self.call_from_thread(self.chat_area.scroll_end, animate=False)
            
            self.history.append({"role": "assistant", "content": accumulated})
            
        except Exception as e:
            if self.generation_cancelled:
                self.call_from_thread(target_widget.update_content, accumulated + " [dim yellow](stopped)[/dim yellow]")
                self.history.append({"role": "assistant", "content": accumulated})
            else:
                self.call_from_thread(target_widget.update_content, f"[red][sys] Error: {e}[/red]")
        finally:
            self.active_response = None
            self.call_from_thread(self.enable_input)

    def disable_input(self) -> None:
        """Locks the input widget to prevent turn collisons during execution."""
        self.chat_input.disabled = True

    def enable_input(self) -> None:
        """Helper callback executed from thread to restore input capabilities."""
        self.chat_input.disabled = False
        self.chat_input.focus()

    def action_stop_generation(self) -> None:
        """Interrupts and stops the active streaming model output cleanly, or clears input if idle."""
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

    def action_set_reasoning_budget(self) -> None:
        """Puts the main input widget into 'Reasoning Budget input' state, or toggles it off."""
        if self.entering_reasoning_budget:
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "Ask your agent anything..."
            self.chat_input.value = ""
            info_banner = Static("[dim yellow][sys] Reasoning budget setting cancelled.[/dim yellow]")
            self.chat_area.mount(info_banner)
            self.chat_area.scroll_end(animate=False)
        else:
            self.entering_reasoning_budget = True
            self.entering_image_url = False
            self.chat_input.placeholder = "Enter Reasoning Budget (positive number, e.g., 2500):"
            self.chat_input.focus()

    def action_attach_image_url(self) -> None:
        """Puts the main input widget into 'Image URL input' state, or toggles it off."""
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
        """Toggles the visibility of the left sidebar metadata pane."""
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display

    def action_toggle_maximized(self) -> None:
        """Completely disables Textual's default F10 maximize layout-breaking action."""
        pass

    def action_toggle_compact(self) -> None:
        """Toggle between compact (dense) and standard (spacious) chat layout on-demand."""
        self.compact_mode = not self.compact_mode
        
        # Explicitly force every mounted message child to repaint and re-evaluate compact spacing
        for child in self.chat_area.children:
            if isinstance(child, Message):
                child.refresh()
        
        status = "enabled" if self.compact_mode else "disabled"
        info_banner = Static(f"[dim yellow][sys] Compact spacing mode {status}.[/dim yellow]")
        self.chat_area.mount(info_banner)
        self.chat_area.scroll_end(animate=False)

    def action_cycle_theme(self) -> None:
        """Cycle through registered styling themes dynamically inside the running session."""
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
        """Consolidated reasoning action: toggles reasoning OFF if active, prompts for budget if inactive, or cancels prompt."""
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

    # Resolve active model name on startup matching standard CLI logic
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
