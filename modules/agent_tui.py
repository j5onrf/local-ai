#!/usr/bin/env python3
# File: ~/.config/local-ai/modules/agent_tui.py
"""Full-Featured Textual TUI for Local-AI Agent Engine."""

import os
import re
import sys
import json
import time
import base64
import threading
import subprocess
import urllib.request as urlreq
from typing import List, Dict, Any, Optional, Iterator, Set

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Footer, Input, Static
from textual.binding import Binding
from textual.theme import Theme
from textual.command import Provider, Hit
from textual.screen import Screen
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED
from rich.console import Group

# Ensure parent modules path is present on system path
CFG_DIR: str = os.path.expanduser("~/.config/local-ai")
sys.path.append(os.path.join(CFG_DIR, "modules"))

import agent_cloud
import agent_ui as ui
import agent_core as core

try:
    import agent_skills as skills
except ImportError:
    skills = None

STATE_FILE: str = os.path.join(CFG_DIR, ".state.json")
CONTEXT_FILE: str = os.path.join(CFG_DIR, "ai-context.md")
SKILLS_DIR: str = os.path.join(CFG_DIR, "skills")
STOP_WORDS: Set[str] = {"is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"}

# Master Base Prompts mirrored directly from ai-agent.py
BASE_PROMPT: str = "Read-only local shell assistant.\nIf <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n\n"
BASE_PROMPT_CHAT: str = BASE_PROMPT + "### Conversational Guidelines:\n- Role: Active, natural, and highly articulate conversational assistant.\n- Tone: Professional, warm, objective, and intellectually engaging.\n\n"
BASE_PROMPT_AGENT: str = "Active local project workspace developer agent.\nIf <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n\n"

# Pre-compiled regular expressions (filters all terminal CSI/extended key artifacts like [13;129u, [104;e, and [<<)
CSI_U_REGEX: re.Pattern = re.compile(r'\x1b?\[?[<>\d;]+[0-9a-zA-Z;]*[a-zA-Z~]?')
ANSI_CLEAN_REGEX: re.Pattern = re.compile(r'\x1b\[[0-9;]*m')
QUESTION_SPLIT_REGEX: re.Pattern = re.compile(r'(?<=\?)\s+')

# Block standard system commands from Command Palette
Screen.command_sources = property(lambda self: set())


def workspace_safe_name(workspace_path: str, home_dir: str) -> str:
    """Converts a workspace path into a safe database name string."""
    safe = workspace_path[len(home_dir):].lstrip("/") if workspace_path.startswith(home_dir) else workspace_path
    return safe.replace("/", "-").strip("-") or "home"


def load_tui_state(key: str, default: Any) -> Any:
    """Generic state loader from .state.json."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get(key, default)
        except Exception:
            pass
    return default


def save_tui_state(key: str, value: Any) -> None:
    """Generic state saver to .state.json."""
    data: Dict[str, Any] = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data[key] = value
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


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

    tools = [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"], ["pbcopy"], ["clip.exe"]]
    for tool in tools:
        try:
            p = subprocess.Popen(tool, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            p.communicate(input=text.encode("utf-8"), timeout=1.0)
            if p.returncode == 0:
                return True
        except Exception:
            continue
    return True


# Color Themes Definition
grok_theme = Theme(name="grok", primary="#444444", secondary="#888888", accent="#ffffff", background="#000000", surface="#0d0d0d", panel="#121212")
dracula_theme = Theme(name="dracula", primary="#bd93f9", secondary="#f8f8f2", accent="#ff79c6", background="#282a36", surface="#21222c", panel="#191a21")
nord_theme = Theme(name="nord", primary="#88c0d0", secondary="#d8dee9", accent="#81a1c1", background="#2e3440", surface="#242933", panel="#1c202a")
dark_theme = Theme(name="dark", primary="#555555", secondary="#b0b0b0", accent="#ffffff", background="#121212", surface="#1c1c1c", panel="#242424")


class FooterToggle(Static):
    """Clickable toggle button to hide/show bottom footer buttons."""
    def on_click(self) -> None:
        if hasattr(self.app, "action_toggle_footer"):
            self.app.action_toggle_footer()


class Message(Static):
    """A message widget isolating thinking blocks in real-time."""
    def __init__(self, sender: str, content: str) -> None:
        super().__init__()
        self.sender, self.content = sender, content

    def update_content(self, new_content: str) -> None:
        self.content = new_content
        self.refresh()

    def render(self) -> Group:
        compact = getattr(self.app, "compact_mode", False)
        current_theme = getattr(self.app, "theme", "dark")
        prefix = "" if compact else "\n"
        
        user_style = "bold bright_white" if current_theme == "grok" else "bold cyan"
        agent_style = "bold #b0b0b0" if current_theme == "grok" else "bold green"

        if self.sender == "User":
            display_text = self.content
            if isinstance(display_text, list):
                display_text = next((item["text"] for item in display_text if item.get("type") == "text"), "[Multimodal]")
            return Group(Text(f"{prefix}❯ USER: {display_text}", style=user_style))
        
        header = Text(f"{prefix}❖ AGENT:", style=agent_style)
        text = self.content
        
        if "<think>" in text:
            parts = text.split("<think>", 1)
            before_think, after_start_think = parts[0], parts[1]
            if "</think>" in after_start_think:
                think_parts = after_start_think.split("</think>", 1)
                thinking_panel = Panel(Text(think_parts[0].strip(), style="italic dim white"), title="⚙ Thinking Process", title_align="left", border_style="bright_black", box=ROUNDED, expand=True)
                body_md = Markdown(before_think + think_parts[1].strip()) if (before_think + think_parts[1]).strip() else Text("")
                return Group(header, thinking_panel, body_md)
            else:
                thinking_panel = Panel(Text(after_start_think.strip(), style="italic dim white"), title="⚙ Thinking Process...", title_align="left", border_style="bright_black", box=ROUNDED, expand=True)
                return Group(header, thinking_panel)
        else:
            return Group(header, Markdown(text))


class AgentCommandProvider(Provider):
    async def search(self, query: str) -> Iterator[Hit]:
        matcher = self.matcher(query)
        commands = [
            ("Copy Last Response", "copy_last_response", "Copy the latest agent response to system clipboard"),
            ("Attach Image URL", "attach_image_url", "Attach an image URL to analyze on your next query"),
            ("Cycle Theme", "cycle_theme", "Cycle through available color themes"),
            ("Toggle Sidebar", "toggle_sidebar", "Show or hide the metadata panel"),
            ("Toggle Compact Mode", "toggle_compact", "Toggle between dense and spacious spacing layouts"),
            ("Toggle Reasoning", "toggle_reasoning", "Enable or disable deep reasoning budget"),
            ("Toggle Bottom Bar", "toggle_footer", "Hide or show the bottom bar buttons"),
        ]
        for title, action, desc in commands:
            score = matcher.match(title)
            if score > 0:
                yield Hit(score, Text(title), lambda act=action: self.app.run_action(act), help=desc)


class LocalAITUI(App):
    """Full-parity Textual TUI for Local-AI Agent."""
    ENABLE_COMMAND_PALETTE = True

    @property
    def command_sources(self) -> Set[Any]:
        return {AgentCommandProvider}

    CSS = """
    Screen { background: $background; }
    #layout { height: 1fr; }
    #sidebar { width: 32; height: 100%; background: $surface; border-right: double #444444; padding: 1 2; }
    #main-container { height: 100%; width: 1fr; background: transparent; }
    #chat-area { height: 1fr; background: transparent; overflow-y: scroll; padding: 1 2; }
    #input-pane { height: 3; border-top: solid #444444; background: $surface; padding: 0 1; }
    Input { width: 1fr; border: none; background: transparent; height: 3; color: $text; }
    #input-toggle { width: auto; height: 3; content-align: center middle; color: $text; padding: 0 1; }
    #input-toggle:hover { background: $primary; color: $text; text-style: bold; }
    Message { margin: 0; height: auto; }
    .sidebar-label { color: $primary; text-style: bold; margin-top: 1; }
    #sidebar > .sidebar-label:first-child { margin-top: 0; }
    .sidebar-val { color: $secondary; margin-bottom: 1; }
    #footer-bar { dock: bottom; height: 1; width: 100%; background: $surface; }
    #footer-keys { dock: none; width: 1fr; height: 1; }
    #footer-toggle { dock: right; width: auto; height: 1; content-align: center middle; background: $surface; color: $text; padding: 0 1; }
    #footer-toggle:hover { background: $primary; color: $text; text-style: bold; }
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
        Binding("ctrl+f", "toggle_footer", "Footer", show=False),
        Binding("ctrl+q", "quit", "Exit TUI", show=False),      
        Binding("escape", "quit", "Exit TUI", show=False),      
    ]

    def __init__(self, workspace_path: str, model_name: str, is_agent: Optional[bool] = None) -> None:
        super().__init__()
        self.workspace_path: str = workspace_path
        self.model_name: str = model_name
        self.safe_name: str = workspace_safe_name(workspace_path, os.path.expanduser("~"))
        
        self.gates_enabled: bool = os.environ.get("AI_CONFIRM_GATES", "1") == "1"
        os.environ["AI_CONFIRM_GATES"] = "1" if self.gates_enabled else "0"
        
        self.gate_auth_event = threading.Event()
        self.gate_auth_result: bool = False
        self.entering_gate_authorization: bool = False

        self.spell_enabled: bool = True
        self.active_skill: str = os.environ.get("AI_ACTIVE_SKILL", "default")
        self.pending_skill_prefix: Optional[str] = None
        
        if is_agent is None:
            is_agent_env = os.environ.get("AI_IS_AGENT", "").lower() in ("1", "true", "yes")
            self.is_agent: bool = is_agent_env or ("/projects/" in workspace_path)
        else:
            self.is_agent: bool = is_agent
        
        self.memory_active: bool = load_tui_state("memory_active", True) if self.is_agent else False
        self.db_turns, self.tpm_count = (0, 0)
        self.refresh_db_counts()

        self.compact_mode: bool = load_tui_state("compact_mode", False)
        self.reasoning_active: bool = False
        self.reasoning_budget: int = 500
        self.entering_reasoning_budget: bool = False
        self.active_image_url: Optional[str] = None
        self.entering_image_url: bool = False
        
        # Load handoff history from CLI if passing from /tui
        cli_history_env = os.environ.get("AI_SESSION_HISTORY")
        if cli_history_env:
            try:
                self.history: List[Dict[str, Any]] = json.loads(cli_history_env)
            except Exception:
                self.history = []
        else:
            self.history = []
        
        self.generation_cancelled: bool = False
        self.active_response: Optional[Any] = None
        self.stats_turns: int = 0
        self.footer_hidden: bool = load_tui_state("footer_hidden", False)

    def refresh_db_counts(self) -> None:
        """Loads active SQLite turn and memory counts for the workspace."""
        if self.is_agent:
            try:
                turns_res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "get-count", self.safe_name], capture_output=True, text=True, timeout=2)
                facts_res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "get-tpm-count", self.safe_name], capture_output=True, text=True, timeout=2)
                self.db_turns = int(turns_res.stdout.strip() or 0)
                self.tpm_count = int(facts_res.stdout.strip() or 0)
            except Exception:
                pass

    def ensure_system_context(self) -> None:
        """Constructs system prompt using 100% identical logic to ai-agent.py."""
        if not any(m.get("role") == "system" for m in self.history):
            skills_list = []
            if self.active_skill and self.active_skill.lower() != "default":
                skills_list = [s.lstrip("-").lower() for s in self.active_skill.split() if s]

            skill_content = skills.load_skill_content(" ".join(skills_list), SKILLS_DIR, CFG_DIR) if (skills and skills_list) else ""
            base_p = BASE_PROMPT_AGENT if self.is_agent else (BASE_PROMPT_CHAT if not skills_list else BASE_PROMPT)
            sys_prompt = skill_content if (self.is_agent and skill_content) else (base_p + (f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n" if skill_content else ""))
            
            if self.is_agent and hasattr(core, "EDIT_SYSTEM_ADD") and "### EDIT MODE" not in sys_prompt:
                sys_prompt += core.EDIT_SYSTEM_ADD.format(ws=self.workspace_path) + core.TOOLS_SYSTEM_ADD.format(names="read_file, write_file, list_dir, run_command", ws=self.workspace_path)
                
            self.history.insert(0, {"role": "system", "content": sys_prompt})
            if self.is_agent and len(self.history) == 1:
                self.history.append({"role": "assistant", "content": "Agent: Workspace loaded. Awaiting instructions."})

    def get_db_status_string(self) -> str:
        if not self.is_agent: return "stateless"
        if not self.memory_active: return "disabled"
        return f"active ({self.tpm_count} facts, {self.db_turns} turns)"

    def update_welcome_banner(self) -> None:
        border_col = {"dark": "bright_blue", "grok": "#333333", "dracula": "#bd93f9", "nord": "#88c0d0"}.get(self.theme, "bright_blue")
        try:
            banner = self.query_one("#welcome-banner", Static)
            banner.update(Panel(
                Markdown("# Workspace Loaded • Awaiting Instructions\nType your query and press `Enter`.\n`Ctrl+B` toggle sidebar • `Ctrl+T` cycle themes • `Ctrl+G` toggle compact • `Ctrl+R` toggle reasoning • `Ctrl+O` copy response."),
                border_style=border_col, box=ROUNDED
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
                yield Static("Enabled" if self.gates_enabled else "Autonomous", id="lbl-gates", classes="sidebar-val")
                
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
                        border_style="bright_blue", box=ROUNDED
                    ), id="welcome-banner")
                with Horizontal(id="input-pane"):
                    yield Input(placeholder="Ask your agent anything...", id="chat-input")
                    yield FooterToggle("▲ Show", id="input-toggle")
        with Horizontal(id="footer-bar"):
            yield Footer(id="footer-keys")
            yield FooterToggle("▼ Hide", id="footer-toggle")

    def on_mount(self) -> None:
        for t in (grok_theme, dracula_theme, nord_theme, dark_theme):
            self.register_theme(t)
            
        self.theme = load_tui_state("tui_theme", "dark")
        self.update_welcome_banner()
        self.chat_area = self.query_one("#chat-area", Vertical)
        self.chat_input = self.query_one("#chat-input", Input)
        self.update_footer_visibility()

        # Mount pre-existing session history if handed off from CLI
        if len(self.history) > 1:
            try:
                self.query_one("#welcome-banner").remove()
            except Exception:
                pass
            for msg in self.history:
                role = msg.get("role")
                content = msg.get("content")
                if role == "user" and content:
                    self.chat_area.mount(Message("User", content))
                elif role == "assistant" and content:
                    self.chat_area.mount(Message("Agent", content))

        self.chat_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        clean_val = CSI_U_REGEX.sub('', event.value)
        if clean_val != event.value:
            event.input.value = clean_val

    def update_stats_ui(self, turns: int, tps: float, elapsed: float) -> None:
        self.query_one("#lbl-stats", Static).update(f"Turns: {turns}\nSpeed: {tps:.1f} t/s\nElapsed: {elapsed:.1f}s")

    def action_copy_last_response(self) -> None:
        last_msg = next((entry.get("content", "") for entry in reversed(self.history) if entry.get("role") == "assistant"), "")
        if last_msg:
            clean_text = last_msg.split("</think>", 1)[-1].strip() if "</think>" in last_msg else last_msg
            copy_to_clipboard(clean_text)
            self.chat_area.mount(Static("[dim white][sys] Copied latest agent response to clipboard.[/dim white]"))
        else:
            self.chat_area.mount(Static("[dim white][sys] No response available to copy yet.[/dim white]"))
        self.chat_area.scroll_end(animate=False)

    async def handle_view_file(self, file_path: str) -> None:
        full_p = os.path.expanduser(file_path)
        if not os.path.isabs(full_p): full_p = os.path.join(self.workspace_path, file_path)
            
        if os.path.exists(full_p) and os.path.isfile(full_p):
            try:
                with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(12000)
                self.history.append({"role": "user", "content": f"[FILE LOADED: {file_path}]\n```\n{content}\n```"})
                await self.chat_area.mount(Static(f"[dim white][sys] Loaded file content into active context: [bold]{file_path}[/bold][/dim white]"))
            except Exception as e:
                await self.chat_area.mount(Static(f"[bold red][sys] Error reading file: {e}[/bold red]"))
        else:
            await self.chat_area.mount(Static(f"[bold red][sys] File not found: {file_path}[/bold red]"))
        self.chat_area.scroll_end(animate=False)

    async def handle_meta_chat_command(self, cmd_root: str) -> None:
        """Executes modules/chat directly for 100% CLI parity on /f, /tk, /b, /a."""
        think_bin = os.path.join(CFG_DIR, "modules", "chat")
        
        try: self.query_one("#welcome-banner").remove()
        except Exception: pass

        self.ensure_system_context()
        
        c_raw = cmd_root.lstrip("/").lower()
        sub_arg = "/t" if c_raw in ("tk", "thinking") else f"/{c_raw}"
        
        hdr_map = {"f": "Follow-up", "b": "Brainstorm", "t": "Thinking", "tk": "Thinking", "a": "All"}
        output_hdr = hdr_map.get(c_raw, "Follow-up")
        
        user_msg = Message("User", f"/{c_raw}")
        await self.chat_area.mount(user_msg)
        
        assistant_msg = Message("Agent", f"Generating {output_hdr}...")
        await self.chat_area.mount(assistant_msg)
        self.chat_area.scroll_end(animate=False)

        self.active_skill = output_hdr.lower()
        self.query_one("#lbl-skill", Static).update(self.active_skill)

        def _run_chat_sub():
            if os.path.exists(think_bin):
                try:
                    res = subprocess.run([sys.executable, think_bin, sub_arg], input=json.dumps(self.history), capture_output=True, text=True, timeout=30)
                    out = res.stdout.strip()
                    if out:
                        clean_out = ANSI_CLEAN_REGEX.sub('', out)
                        if clean_out.startswith("AI:"): clean_out = clean_out[3:].strip()
                            
                        lines = [l.strip() for l in clean_out.splitlines() if l.strip()]
                        if len(lines) > 1:
                            hdr = lines[0]
                            items = []
                            for item in lines[1:]:
                                questions = [q.strip() for q in QUESTION_SPLIT_REGEX.split(item) if q.strip()]
                                items.extend(questions)
                            formatted_out = f"**{hdr}**\n\n" + "\n\n".join(items)
                        else:
                            formatted_out = clean_out

                        self.call_from_thread(assistant_msg.update_content, formatted_out)
                        self.history.append({"role": "assistant", "content": formatted_out})
                        return
                except Exception as e:
                    self.call_from_thread(assistant_msg.update_content, f"[red][sys] Chat error: {e}[/red]")
            else:
                self.call_from_thread(assistant_msg.update_content, "[red][sys] modules/chat script not found.[/red]")

        self.run_worker(_run_chat_sub, thread=True)

    async def handle_slash_command(self, cmd: str) -> None:
        parts = cmd.split(maxsplit=1)
        root, args = parts[0].lower(), parts[1] if len(parts) > 1 else ""

        if root in ("/help", "/h"):
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("Command", style="bold cyan")
            table.add_column("Description", style="white")
            for c, d in [
                ("/help, /h", "Show command list"), ("/g, /yolo", "Toggle autonomous YOLO mode vs per-action y/n gates"),
                ("/m", "Toggle long-term memory"), ("/clear, /reset", "Clear chat & history"),
                ("/tok", "Show token usage"), ("/sync, /re", "Sync codebase AST index"),
                ("/spell, /sp", "Toggle spellchecker"), ("/skill <q>, /s", "Load skill blueprint"),
                ("/compact, /c", "Toggle compact mode"), ("/t, /thinking", "Toggle reasoning budget"),
                ("/f, /tk, /b, /a", "Skill mode prompts"), ("view file <path>", "Attach file content to context"), ("exit, quit, q", "Exit TUI")
            ]: table.add_row(c, d)
            await self.chat_area.mount(Static(Panel(table, title="⚙ Full Agent TUI Commands", title_align="left", border_style="bright_blue", box=ROUNDED)))

        elif root in ("exit", "quit", "q"): self.exit()

        elif root == "/m":
            self.memory_active = not self.memory_active
            save_tui_state("memory_active", self.memory_active)
            self.query_one("#lbl-database", Static).update(self.get_db_status_string())
            await self.chat_area.mount(Static(f"[dim white][sys] Memory {'enabled' if self.memory_active else 'disabled'}.[/dim white]"))

        elif root in ("/g", "/yolo"):
            self.gates_enabled = not self.gates_enabled
            os.environ["AI_CONFIRM_GATES"] = "1" if self.gates_enabled else "0"
            status_lbl = "Enabled" if self.gates_enabled else "Autonomous"
            msg_str = "disabled (Autonomous / YOLO mode active)" if not self.gates_enabled else "enabled (y/n confirmation required per action)"
            self.query_one("#lbl-gates", Static).update(status_lbl)
            await self.chat_area.mount(Static(f"[dim white][sys] Confirmation gates {msg_str}.[/dim white]"))

        elif root in ("/clear", "/reset"):
            self.history.clear()
            self.stats_turns = 0
            self.update_stats_ui(0, 0.0, 0.0)
            for child in list(self.chat_area.children): child.remove()
            await self.chat_area.mount(Static("[dim white][sys] Session history and chat window cleared.[/dim white]"))

        elif root == "/tok":
            est = sum(len(m.get("content", "")) // 4 for m in self.history)
            await self.chat_area.mount(Static(f"[dim white][sys] Active conversation history: ~{est:,} tokens ({len(self.history)} messages)[/dim white]"))

        elif root in ("/sync", "/re"):
            await self.chat_area.mount(Static("[dim white][sys] Triggered background AST & codebase graph sync.[/dim white]"))
            try: subprocess.Popen(["index-map", self.workspace_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception: pass

        elif root in ("/spell", "/sp"):
            self.spell_enabled = not self.spell_enabled
            await self.chat_area.mount(Static(f"[dim white][sys] Spellchecker {'enabled' if self.spell_enabled else 'disabled'}.[/dim white]"))

        elif root in ("/skill", "/s"):
            if args:
                if skills is not None:
                    content = skills.load_skill_content(args, SKILLS_DIR, CFG_DIR)
                    if content:
                        s_name = content[0] if isinstance(content, tuple) else args
                        s_text = content[1] if isinstance(content, tuple) else content
                        self.active_skill = s_name
                        self.query_one("#lbl-skill", Static).update(s_name)
                        self.history.append({"role": "system", "content": f"[SKILL BLUEPRINT LOADED: {s_name}]\n{s_text}"})
                        await self.chat_area.mount(Static(f"[dim white][sys] Loaded skill blueprint into LLM context: [bold]{s_name}[/bold][/dim white]"))
                    else: await self.chat_area.mount(Static(f"[dim white][sys] Searched skills for '[bold]{args}[/bold]' (no blueprint file found).[/dim white]"))
                else:
                    self.active_skill = args
                    self.query_one("#lbl-skill", Static).update(args)
                    await self.chat_area.mount(Static(f"[dim white][sys] Skill query active: [bold]{args}[/bold][/dim white]"))
            else: await self.chat_area.mount(Static("[dim white][sys] Usage: /skill <query> or /s <query>[/dim white]"))

        elif root in ("/compact", "/c"): self.action_toggle_compact()
        elif root in ("/t", "/thinking"): self.action_toggle_reasoning()
        elif root in ("/f", "/tk", "/b", "/a"): await self.handle_meta_chat_command(root)
        else: await self.chat_area.mount(Static(f"[dim white][sys] Unknown command '{root}'. Type [bold]/help[/bold] for available commands.[/dim white]"))

        self.chat_area.scroll_end(animate=False)

    def prompt_tui_confirm(self, prompt_text: str) -> bool:
        """Presents an interactive y/n confirmation prompt in the TUI input bar."""
        self.gate_auth_event.clear()
        self.gate_auth_result = False
        
        def _show_prompt():
            self.entering_gate_authorization = True
            self.current_gate_prompt = prompt_text
            self.chat_input.disabled = False
            self.chat_input.value = ""
            self.chat_input.placeholder = f"▲ Authorize tool: {prompt_text}? [Y/n]: "
            self.chat_input.focus()

        self.call_from_thread(_show_prompt)
        self.gate_auth_event.wait()
        return self.gate_auth_result

    def process_query_worker(self, query: str) -> None:
        """Worker thread executing memory recall, system context, and stream response matching ai-agent.py."""
        try:
            self.call_from_thread(self.query_one("#welcome-banner").remove)
        except Exception:
            pass

        self.ensure_system_context()

        user_msg = Message("User", query)
        self.call_from_thread(self.chat_area.mount, user_msg)

        # Hook ui.confirm_tool directly to TUI confirmation prompt for entire turn
        old_confirm = getattr(ui, "confirm_tool", None)
        ui.confirm_tool = lambda reason: self.prompt_tui_confirm(reason)

        try:
            # Step 1: Memory Recall & TPM Context (100% Non-Blocking TUI Interactive Parity)
            past_memory, tpm_context = "", ""
            if self.is_agent and self.memory_active:
                try:
                    mem_bin = os.path.join(CFG_DIR, "modules", "ai-agent-memories")
                    if os.path.exists(mem_bin):
                        # Fetch TPM Facts
                        tpm_res = subprocess.run([sys.executable, mem_bin, "tpm-get", self.safe_name], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
                        if tpm_res.returncode == 0 and tpm_res.stdout.strip():
                            tpm_context = tpm_res.stdout.strip()

                        # Prompt user for gate authorization FIRST in TUI input box
                        do_recall = True
                        if self.gates_enabled:
                            do_recall = self.prompt_tui_confirm(f"inject recalled workspace memory for '{query}'")

                        if do_recall:
                            run_env = {**os.environ, "AI_CONTEXT_RUN": "1", "AI_CONFIRM_GATES": "0"}
                            res = subprocess.run([sys.executable, mem_bin, "get-context", self.safe_name, query], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10, env=run_env)
                            
                            matched_mem = res.stdout.strip()
                            if res.returncode == 0 and matched_mem and "NO_FACTS" not in matched_mem and "0 facts" not in matched_mem:
                                past_memory = matched_mem
                                self.call_from_thread(self.chat_area.mount, Static("[dim white][sys] Memory injected.[/dim white]"))
                            else:
                                self.call_from_thread(self.chat_area.mount, Static("[dim white][sys] Memory recall checked (0 facts found).[/dim white]"))
                        else:
                            self.call_from_thread(self.chat_area.mount, Static("[dim white][sys] Memory recall skipped.[/dim white]"))
                except Exception:
                    pass

            assistant_msg = Message("Agent", "Thinking...")
            self.call_from_thread(self.chat_area.mount, assistant_msg)
            self.call_from_thread(self.chat_area.scroll_end, animate=False)

            # Step 2: System Context Retrieval via agent_skills
            try:
                res_ctx = skills.get_system_context(query, CONTEXT_FILE, STOP_WORDS, SKILLS_DIR, CFG_DIR) if (skills and hasattr(skills, "get_system_context")) else ""
                sys_ctx = "" if res_ctx == "__ABORT_TURN__" else (res_ctx or "")
            except Exception:
                sys_ctx = ""

            # Step 3: Combine TPM Facts + Past Memories + System Context (100% CLI Parity)
            combined_ctx = "\n\n".join(filter(None, [tpm_context, past_memory, sys_ctx]))
            formatted_prompt = f"<context>\n{combined_ctx}\n</context>\n\nUser Question: {query}" if combined_ctx else f"User Question: {query}"

            if self.active_image_url:
                self.history.append({"role": "user", "content": [{"type": "text", "text": formatted_prompt}, {"type": "image_url", "image_url": {"url": self.active_image_url}}]})
                self.active_image_url = None  
                self.call_from_thread(self.query_one("#lbl-image", Static).update, "None")
            else:
                self.history.append({"role": "user", "content": formatted_prompt})
            
            # Step 4: Stream response using core CLI engine & agent_cloud
            self.call_from_thread(self.disable_input)
            self.generation_cancelled, self.active_response = False, None
            accumulated, start_time, first_token_time, token_count = "", time.perf_counter(), None, 0

            thinking_budget = self.reasoning_budget if self.reasoning_active else 0
            for _round in range(10):
                accumulated, in_thinking, tool_calls_map = "", False, {}
                configs = agent_cloud.get_active_configs(self.history) if agent_cloud else []
                local_extra = {"thinking_budget_tokens": thinking_budget, "chat_template_kwargs": {"enable_thinking": True}} if thinking_budget > 0 else {"chat_template_kwargs": {"enable_thinking": False}}

                if configs:
                    url, headers, body, timeout = configs[0]
                    if thinking_budget > 0: body["thinking_budget_tokens"] = thinking_budget
                else:
                    configs = [("http://localhost:8080/v1/chat/completions", {}, {"messages": self.history, "stream": True, "model": "local-model", **local_extra}, 180)]

                url, headers, body, timeout = configs[0]
                body["stream"], body["messages"] = True, self.history
                if hasattr(core, "_EDIT_TOOLS"):
                    body["tools"] = core._EDIT_TOOLS

                req = urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", **headers}, method="POST")

                with urlreq.urlopen(req, timeout=timeout) as response:
                    self.active_response = response
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {response.read().decode('utf-8', errors='ignore')[:200]}")

                    for line in response:
                        if self.generation_cancelled or not line.startswith(b"data:"): continue
                        dec_line = line.decode("utf-8", errors="ignore").strip()[5:].strip()
                        if dec_line == "[DONE]": break

                        try:
                            data = json.loads(dec_line)
                            choices = data.get("choices", [{}])
                            if not choices: continue
                            delta = choices[0].get("delta", {})
                            text_chunk, thinking_chunk = delta.get("content") or "", delta.get("reasoning_content") or delta.get("thinking") or ""

                            for tc in delta.get("tool_calls", []):
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_map:
                                    tool_calls_map[idx] = {"id": tc.get("id", ""), "type": "function", "function": {"name": tc.get("function", {}).get("name", ""), "arguments": ""}}
                                if tc.get("function", {}).get("name"):
                                    tool_calls_map[idx]["function"]["name"] = tc["function"]["name"]
                                tool_calls_map[idx]["function"]["arguments"] += tc.get("function", {}).get("arguments", "")

                            if text_chunk or thinking_chunk:
                                if first_token_time is None: first_token_time = time.perf_counter()
                                token_count += 1

                            if thinking_chunk:
                                if not in_thinking: accumulated += "<think>"; in_thinking = True
                                accumulated += thinking_chunk
                            if text_chunk:
                                if in_thinking: accumulated += "</think>"; in_thinking = False
                                accumulated += text_chunk

                            if text_chunk or thinking_chunk:
                                self.call_from_thread(assistant_msg.update_content, accumulated)
                                self.call_from_thread(self.chat_area.scroll_end, animate=False)
                        except Exception: pass

                if in_thinking: accumulated += "</think>"
                calls = [val for _, val in sorted(tool_calls_map.items())] if tool_calls_map else None

                if not calls:
                    self.history.append({"role": "assistant", "content": accumulated})
                    break

                self.history.append({"role": "assistant", "content": accumulated or None, "tool_calls": calls})
                user_aborted = False

                for tc in calls:
                    fname = tc.get("function", {}).get("name", "")
                    raw_args = tc.get("function", {}).get("arguments", "")
                    args = json.loads(raw_args) if raw_args else {}
                    brief = str(args.get("path") or args.get("command") or "")[:100]
                    verb = getattr(core, "TOOL_VERBS", {}).get(fname, "working")

                    if user_aborted:
                        result = "[denied] execution cancelled by user"
                    else:
                        if self.gates_enabled:
                            res = self.prompt_tui_confirm(f"{fname} {brief}")
                            if not res:
                                result = f"[denied] user rejected {fname} execution"
                                user_aborted = True
                                self.history.append({"role": "tool", "tool_call_id": tc.get("id", ""), "name": fname, "content": result})
                                continue

                        self.call_from_thread(self.chat_area.mount, Static(f"[dim white][sys] ∗ {verb} • [bold cyan]{fname}[/bold cyan] [italic]{brief}[/italic][/dim white]"))
                        self.call_from_thread(self.chat_area.scroll_end, animate=False)
                        try:
                            old_gates = os.environ.get("AI_CONFIRM_GATES")
                            os.environ["AI_CONFIRM_GATES"] = "0"
                            result = core._run_edit_tool(fname, args, self.workspace_path)
                            if old_gates: os.environ["AI_CONFIRM_GATES"] = old_gates
                            if "[denied]" in result: user_aborted = True
                        except Exception as te:
                            result = f"[tool error] {te}"

                    self.history.append({"role": "tool", "tool_call_id": tc.get("id", ""), "name": fname, "content": result})

                if user_aborted:
                    self.call_from_thread(self.chat_area.mount, Static("[dim white][sys] Agent execution halted by user gate.[/dim white]"))
                    break

                assistant_msg = Message("Agent", "Processing tool results...")
                self.call_from_thread(self.chat_area.mount, assistant_msg)

            end_time = time.perf_counter()
            total_elapsed = max(0.01, end_time - start_time)
            gen_duration = max(0.001, end_time - first_token_time) if first_token_time else total_elapsed
            tps = (token_count / gen_duration) if first_token_time and token_count > 0 else (len(accumulated) // 4) / total_elapsed

            self.stats_turns += 1
            self.call_from_thread(self.update_stats_ui, self.stats_turns, tps, total_elapsed)

            if self.is_agent and query:
                try:
                    subprocess.Popen([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "log-turn", self.safe_name, query, accumulated], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.refresh_db_counts()
                    self.call_from_thread(self.query_one("#lbl-database", Static).update, self.get_db_status_string())
                except Exception: pass

        except Exception as e:
            if self.generation_cancelled:
                self.call_from_thread(assistant_msg.update_content, accumulated + " [dim white](stopped)[/dim white]")
            else:
                self.call_from_thread(assistant_msg.update_content, f"[red][sys] Error: {e}[/red]")
        finally:
            self.active_response = None
            if old_confirm:
                ui.confirm_tool = old_confirm
            self.call_from_thread(self.enable_input)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        raw_val = event.value.strip()
        query = CSI_U_REGEX.sub('', raw_val).strip()
        self.chat_input.value = ""

        if getattr(self, "entering_gate_authorization", False):
            self.entering_gate_authorization = False
            self.chat_input.placeholder = "Ask your agent anything..."
            
            is_yes = query.lower() in ("y", "yes", "")
            self.gate_auth_result = is_yes
            self.gate_auth_event.set()
            
            status_text = "Authorized" if is_yes else "Denied"
            color = "green" if is_yes else "red"
            label = "Memory recall" if "recall" in getattr(self, "current_gate_prompt", "").lower() or "memory" in getattr(self, "current_gate_prompt", "").lower() else "Tool execution"
            await self.chat_area.mount(Static(f"[dim white][sys] {label}: [bold {color}]{status_text}[/bold {color}][/dim white]"))
            self.chat_area.scroll_end(animate=False)
            return

        if not query: return

        if self.pending_skill_prefix:
            query = f"{self.pending_skill_prefix} {query}"
            self.pending_skill_prefix = None
            self.chat_input.placeholder = "Ask your agent anything..."

        if query.lower() in ("exit", "quit", "q"): self.exit(); return
        if query.lower().startswith("view file "): await self.handle_view_file(query[10:].strip()); return
        if query.startswith("/"): await self.handle_slash_command(query); return

        if self.entering_reasoning_budget:
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "Ask your agent anything..."
            if not query:
                self.reasoning_budget, self.reasoning_active = 500, True
                self.query_one("#lbl-reasoning", Static).update("500 tokens")
                await self.chat_area.mount(Static("[dim white][sys] Deep reasoning enabled with default budget: [bold]500 tokens[/bold][/dim white]"))
            else:
                try:
                    val = int(query)
                    if val > 0:
                        self.reasoning_budget, self.reasoning_active = val, True
                        self.query_one("#lbl-reasoning", Static).update(f"{val} tokens")
                        await self.chat_area.mount(Static(f"[dim white][sys] Deep reasoning enabled with custom budget: [bold]{val} tokens[/bold][/dim white]"))
                    else: raise ValueError
                except ValueError:
                    self.reasoning_active = False
                    self.query_one("#lbl-reasoning", Static).update("Disabled")
                    await self.chat_area.mount(Static("[bold red][sys] Invalid budget. Deep reasoning remains disabled.[/bold red]"))
            self.chat_area.scroll_end(animate=False)
            return

        if self.entering_image_url:
            self.entering_image_url, self.active_image_url = False, query
            self.chat_input.placeholder = "Ask your agent anything..."
            filename = query.split("/")[-1].split("?")[0][:25]
            self.query_one("#lbl-image", Static).update(filename or "image_attached")
            await self.chat_area.mount(Static(f"[dim white][sys] Attached image URL: [bold]{query}[/bold][/dim white]"))
            self.chat_area.scroll_end(animate=False)
            return

        # Run query process in worker thread to prevent event queue blocking
        self.run_worker(lambda: self.process_query_worker(query), thread=True)

    def disable_input(self) -> None:
        if not getattr(self, "entering_gate_authorization", False):
            self.chat_input.disabled = True

    def enable_input(self) -> None:
        self.chat_input.disabled = False
        self.chat_input.focus()

    def action_stop_generation(self) -> None:
        if self.chat_input.disabled:
            self.generation_cancelled = True
            if self.active_response:
                try: self.active_response.close()
                except Exception: pass
            self.chat_area.mount(Static("[dim white][sys] Generation stopped by user.[/dim white]"))
            self.chat_area.scroll_end(animate=False)

    def action_attach_image_url(self) -> None:
        if self.entering_image_url:
            self.entering_image_url = False
            self.chat_input.placeholder = "Ask your agent anything..."
        else:
            self.entering_image_url, self.entering_reasoning_budget = True, False
            self.chat_input.placeholder = "Enter Web Image URL (http://... or https://...):"
            self.chat_input.focus()

    def action_toggle_sidebar(self) -> None:
        sb = self.query_one("#sidebar")
        sb.display = not sb.display

    def update_footer_visibility(self) -> None:
        try:
            footer_bar = self.query_one("#footer-bar", Horizontal)
            input_toggle = self.query_one("#input-toggle", Static)
            if self.footer_hidden:
                footer_bar.display = False
                input_toggle.display = True
            else:
                footer_bar.display = True
                input_toggle.display = False
        except Exception: pass

    def action_toggle_footer(self) -> None:
        self.footer_hidden = not self.footer_hidden
        save_tui_state("footer_hidden", self.footer_hidden)
        self.update_footer_visibility()

    def action_toggle_compact(self) -> None:
        self.compact_mode = not self.compact_mode
        save_tui_state("compact_mode", self.compact_mode)
        for child in self.chat_area.children:
            if isinstance(child, Message): child.refresh()
        self.chat_area.mount(Static(f"[dim white][sys] Compact spacing mode {'enabled' if self.compact_mode else 'disabled'}.[/dim white]"))
        self.chat_area.scroll_end(animate=False)

    def action_cycle_theme(self) -> None:
        try:
            self.theme = self.THEMES[(self.THEMES.index(self.theme) + 1) % len(self.THEMES)]
            save_tui_state("tui_theme", self.theme)
            self.update_welcome_banner()
            for child in self.chat_area.children:
                if isinstance(child, Message): child.refresh()
            self.chat_area.mount(Static(f"[dim white][sys] Theme changed to: [bold]{self.theme}[/bold][/dim white]"))
            self.chat_area.scroll_end(animate=False)
        except Exception: pass

    def action_toggle_reasoning(self) -> None:
        if self.entering_reasoning_budget:
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "Ask your agent anything..."
        elif self.reasoning_active:
            self.reasoning_active = False
            self.query_one("#lbl-reasoning", Static).update("Disabled")
            self.chat_area.mount(Static("[dim white][sys] Deep reasoning disabled.[/dim white]"))
            self.chat_area.scroll_end(animate=False)
        else:
            self.entering_reasoning_budget, self.entering_image_url = True, False
            self.chat_input.placeholder = "Enter Reasoning Budget (Press Enter for default 500):"
            self.chat_input.focus()

if __name__ == "__main__":
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    try:
        configs = agent_cloud.get_active_configs([]) if agent_cloud else []
        model = configs[0][2].get("model", "local-model") if configs else ui.get_local_model_name()
    except Exception:
        model = ui.get_local_model_name()
            
    app = LocalAITUI(workspace, model)
    app.run()
