# File: ~/.config/local-ai/modules/agent_tui.py
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
from rich.console import Group

# Ensure parent modules path is present on system path
sys.path.append(os.path.expanduser("~/.config/local-ai/modules"))
try:
    import agent_cloud
    import agent_ui
    import agent_core as core
except ImportError as e:
    # Fallback placeholders for standalone testing
    agent_cloud = None
    core = None


def load_env_file(path: str) -> None:
    """Loads environment configurations dynamically to ensure key parity."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        k = k.replace("export ", "", 1).strip()
                        if not v.startswith(('"', "'")):
                            v = v.split(" #")[0]
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

# Load environmental configs on startup
CFG_DIR: str = os.path.expanduser("~/.config/local-ai")
load_env_file(os.path.join(CFG_DIR, ".env"))


# --- Themes ---
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
    A dynamic chat message widget.
    Isolates <think>...</think> blocks in real-time to render clean thinking process panels.
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
                display_text = next((item["text"] for item in display_text if item.get("type") == "text"), "[Multimodal Payload]")
            return Group(Text(f"{prefix}❯ USER: {display_text}", style="bold cyan"))
        
        header = Text(f"{prefix}❖ AGENT:", style="bold green")
        text = self.content
        
        if "<think>" in text:
            parts = text.split("<think>", 1)
            before_think = parts[0]
            after_start_think = parts[1]
            
            if "</think>" in after_start_think:
                think_parts = after_start_think.split("</think>", 1)
                thinking_text = think_parts[0]
                answer_text = before_think + think_parts[1]
                
                thinking_panel = Panel(
                    Text(thinking_text.strip(), style="italic dim white"),
                    title="⚙ Thinking Process",
                    title_align="left",
                    border_style="bright_black",
                    box=ROUNDED,
                    expand=True
                )
                
                body_md = Markdown(answer_text.strip()) if answer_text.strip() else Text("")
                return Group(header, thinking_panel, body_md)
            else:
                thinking_text = after_start_think
                thinking_panel = Panel(
                    Text(thinking_text.strip(), style="italic dim white"),
                    title="⚙ Thinking Process...",
                    title_align="left",
                    border_style="yellow",
                    box=ROUNDED,
                    expand=True
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
            ("Toggle Reasoning Mode", "toggle_reasoning", "Enable deep reasoning budget, prompt for tokens, or disable it"),
            ("Cycle Theme", "cycle_theme", "Cycle through available color themes"),
            ("Toggle Sidebar", "toggle_sidebar", "Show or hide the metadata panel"),
            ("Toggle Compact Mode", "toggle_compact", "Toggle between dense and spacious spacing layouts"),
            ("Exit", "quit", "Close the Local-AI Agent session")
        ]
        
        for title, action, desc in commands:
            score = matcher.match(title)
            if score > 0:
                yield Hit(
                    score,
                    Text(title),
                    lambda act=action: self.app.run_action(act),
                    help=desc
                )


class LocalAITUI(App):
    """
    A Textual TUI for Local-AI Agent.
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
        border-right: double $primary;
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
        border-top: solid $primary;
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
    
    .sidebar-val {
        color: $secondary;
        margin-bottom: 1;
    }
    """

    THEMES: List[str] = ["dark", "grok", "dracula", "nord", "monokai"]

    # Remapped toggle_compact to ctrl+g to prevent text-input shadowing conflicts
    BINDINGS = [
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=True),
        Binding("ctrl+g", "toggle_compact", "Compact", show=True),
        Binding("ctrl+r", "toggle_reasoning", "Reasoning", show=True),
        Binding("ctrl+t", "cycle_theme", "Theme", show=True),
        Binding("ctrl+y", "attach_image_url", "Image", show=True),
        Binding("ctrl+c", "quit", "Exit", show=True),
    ]

    def __init__(self, workspace_path: str, model_name: str) -> None:
        super().__init__()
        self.workspace_path: str = workspace_path
        self.model_name: str = model_name
        
        self.compact_mode: bool = False
        
        # Deep Reasoning states
        self.reasoning_active: bool = False
        self.reasoning_budget: int = 500
        self.entering_reasoning_budget: bool = False
        
        self.active_image_url: Optional[str] = None
        self.entering_image_url: bool = False
        
        self.history: List[Dict[str, str]] = []

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
                info_banner = Static("[dim yellow][sys] Deep reasoning enabled with default budget: [bold]500 tokens[/bold][/dim yellow]")
                self.chat_area.mount(info_banner)
            else:
                try:
                    val = int(query)
                    if val > 0:
                        self.reasoning_budget = val
                        self.reasoning_active = True
                        self.query_one("#lbl-reasoning", Static).update(f"{val} tokens")
                        info_banner = Static(f"[dim yellow][sys] Deep reasoning enabled with custom budget: [bold]{val} tokens[/bold][/dim yellow]")
                        self.chat_area.mount(info_banner)
                    else:
                        raise ValueError
                except ValueError:
                    self.reasoning_active = False
                    self.query_one("#lbl-reasoning", Static).update("Disabled")
                    info_banner = Static("[bold red][sys] Invalid budget. Deep reasoning remains disabled.[/bold red]")
                    self.chat_area.mount(info_banner)
                
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
            
            info_banner = Static(f"[dim yellow][sys] Attached image URL: [bold]{query}[/bold][/dim yellow]")
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
                if response.status != 200:
                    err_text = response.read().decode("utf-8", errors="ignore")[:200]
                    raise Exception(f"HTTP {response.status}: {err_text}")

                accumulated = ""
                for line in response:
                    if not line.startswith(b"data:"):
                        continue
                    
                    content = ""
                    if core is not None:
                        content = core.extract_stream_content(line)
                    else:
                        line_str = line.decode("utf-8", errors="ignore").strip()
                        if line_str.startswith("data: "):
                            data_content = line_str[6:]
                            if data_content != "[DONE]":
                                try:
                                    parsed = json.loads(data_content)
                                    content = parsed["choices"][0]["delta"].get("content", "")
                                except Exception:
                                    pass
                    
                    if content:
                        accumulated += content
                        self.call_from_thread(target_widget.update_content, accumulated)
                        self.call_from_thread(self.chat_area.scroll_end, animate=False)
            
            self.history.append({"role": "assistant", "content": accumulated})
            
        except Exception as e:
            self.call_from_thread(target_widget.update_content, f"[red][sys] Error: {e}[/red]")
        finally:
            self.call_from_thread(self.enable_input)

    def disable_input(self) -> None:
        self.chat_input.disabled = True

    def enable_input(self) -> None:
        self.chat_input.disabled = False
        self.chat_input.focus()

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
            
            info_banner = Static(f"[dim yellow][sys] Theme changed dynamically to: [bold]{self.theme}[/bold][/dim yellow]")
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
    model = os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite")
    
    app = LocalAITUI(workspace, model)
    app.run()
