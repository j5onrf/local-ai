#!/usr/bin/env python3
# File: ~/.config/local-ai/modules/agent_tui.py
"""Production Textual TUI for Local-AI Agent Engine."""

import base64, json, os, re, sqlite3, subprocess, sys, threading, time
import urllib.request as urlreq
from contextlib import closing
from typing import Any, Dict, Iterator, List, Optional, Set

from rich.box import ROUNDED
from rich.console import Group
from rich.markdown import CodeBlock, Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Provider
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.theme import Theme
from textual.widgets import Footer, Input, Static

CFG_DIR: str = os.path.expanduser("~/.config/local-ai")
sys.path.append(os.path.join(CFG_DIR, "modules"))

import agent_cloud, agent_core as core, agent_ui as ui
try: import agent_skills as skills
except ImportError: skills = None

STATE_FILE = os.path.join(CFG_DIR, ".state.json")
CONTEXT_FILE = os.path.join(CFG_DIR, "ai-context.md")
SKILLS_DIR = os.path.join(CFG_DIR, "skills")
SESSIONS_DIR = os.path.join(CFG_DIR, "projects", "database")

TOKEN_RE = re.compile(r"[^\w\s]")
STOP_WORDS: Set[str] = {"is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"}
CSI_U_REGEX = re.compile(r'(?:\x1b\[<|\x1b\[|\[<)?\d+;\d+;\d+[mM]|\x1b\[[0-9;]*[a-zA-Z~]|\x1b[\[\(\=][0-9;]*[a-zA-Z~]?')
ANSI_CLEAN_REGEX = re.compile(r'\x1b\[[0-9;]*m')
QUESTION_SPLIT_REGEX = re.compile(r'(?<=\?)\s+')

Screen.command_sources = property(lambda self: set())

def get_dynamic_code_block_background() -> str:
    try: return "#0d0d0d" if getattr(App.get_running_app(), "theme", "dark") == "grok" else "#1a1a1a"
    except Exception: return "#1a1a1a"

def custom_code_block_rich_console(self, console, options):
    yield Syntax(str(self.text).rstrip(), self.lexer_name, theme=getattr(self, "code_theme", "github-dark"), word_wrap=True, padding=(1, 2), background_color=get_dynamic_code_block_background())

CodeBlock.__rich_console__ = custom_code_block_rich_console

BASE_PROMPT = "Read-only local shell assistant.\nIf <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n\n"
BASE_PROMPT_CHAT = BASE_PROMPT + "### Conversational Guidelines:\n- Role: Active, natural, and highly articulate conversational assistant.\n- Tone: Professional, warm, objective, and intellectually engaging.\n\n"
BASE_PROMPT_AGENT = "Active local project workspace developer agent.\nIf <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n\n"

def workspace_safe_name(workspace_path: str, home_dir: str) -> str:
    safe = workspace_path[len(home_dir):].lstrip("/") if workspace_path.startswith(home_dir) else workspace_path
    return safe.replace("/", "-").strip("-") or "home"

def load_tui_state(key: str, default: Any) -> Any:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f: return json.load(f).get(key, default)
        except Exception: pass
    return default

def save_tui_state(key: str, value: Any) -> None:
    data = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except Exception: pass
    data[key] = value
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
    except Exception: pass

def copy_to_clipboard(text: str) -> bool:
    if not text: return False
    try:
        sys.stdout.write(f"\x1b]52;c;{base64.b64encode(text.encode('utf-8')).decode('utf-8')}\x07")
        sys.stdout.flush()
    except Exception: pass
    for tool in [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"], ["pbcopy"], ["clip.exe"]]:
        try:
            p = subprocess.Popen(tool, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            p.communicate(input=text.encode("utf-8"), timeout=1.0)
            if p.returncode == 0: return True
        except Exception: continue
    return True

def tokenize(text: str) -> List[str]:
    return [w for w in TOKEN_RE.sub(" ", text.lower()).split() if len(w) > 1 and w not in STOP_WORDS] if text else []

def get_recalled_memory(workspace: str, query: str) -> str:
    """100% Parity Jaccard Similarity Recall matching ai-agent-memories against turns table."""
    q_tokens = set(tokenize(query))
    if not q_tokens or not os.path.exists(os.path.join(SESSIONS_DIR, f"{workspace}.db")): return ""
    try:
        with closing(sqlite3.connect(os.path.join(SESSIONS_DIR, f"{workspace}.db"), timeout=5)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_msg, assistant_msg, tokens, timestamp FROM turns WHERE workspace = ?", (workspace,))
            rows = cur.fetchall()

        candidates = []
        for u, a, t, ts in rows:
            t_tokens = set(t.split()) if t else set()
            score = len(q_tokens & t_tokens) / len(q_tokens | t_tokens) if (q_tokens & t_tokens) else 0.0
            if score >= 0.35:
                candidates.append((score, u, a, time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))))

        if not candidates: return ""
        candidates.sort(key=lambda x: -x[0])
        blocks = [f"* **On {dt} you asked**: \"{u.strip()}\"\n  **Agent responded**: \"{re.sub(r'<think>.*?</think>', '', a, flags=re.DOTALL).strip()}\"" for _, u, a, dt in candidates[:3]]
        return "### Relevant Past Discussion (Retrieved from Session Memory):\n" + "\n\n".join(blocks)
    except Exception: return ""

grok_theme = Theme(name="grok", primary="#444444", secondary="#888888", accent="#ffffff", background="#000000", surface="#0d0d0d", panel="#121212")
dark_theme = Theme(name="dark", primary="#555555", secondary="#b0b0b0", accent="#ffffff", background="#121212", surface="#1c1c1c", panel="#242424")

class FooterToggle(Static):
    def on_click(self) -> None:
        if hasattr(self.app, "action_toggle_footer"): self.app.action_toggle_footer()

class Message(Static):
    def __init__(self, sender: str, content: Any) -> None:
        super().__init__()
        self.sender, self.content = sender, content

    def update_content(self, new_content: Any) -> None:
        self.content = new_content
        self.refresh()

    def render(self) -> Group:
        compact = getattr(self.app, "compact_mode", False)
        theme = getattr(self.app, "theme", "dark")
        prefix = "" if compact else "\n"
        u_style, a_style = ("bold bright_white", "bold #b0b0b0") if theme == "grok" else ("bold cyan", "bold green")

        if self.sender == "User":
            text = self.content
            if isinstance(text, list): text = next((i["text"] for i in text if i.get("type") == "text"), "[Multimodal]")
            return Group(Text(f"{prefix}❯ USER: {text}", style=u_style))

        hdr, text = Text(f"{prefix}❖ AGENT:", style=a_style), str(self.content or "")
        if "<think>" in text:
            before, after = text.split("<think>", 1)
            if "</think>" in after:
                think, rest = after.split("</think>", 1)
                panel = Panel(Text(think.strip(), style="italic dim white"), title="⚙ Thinking Process", title_align="left", border_style="bright_black", box=ROUNDED, expand=True)
                body = Markdown(before + rest.strip(), code_theme="ansi_dark") if (before + rest).strip() else Text("")
                return Group(hdr, panel, body)
            return Group(hdr, Panel(Text(after.strip(), style="italic dim white"), title="⚙ Thinking Process...", title_align="left", border_style="bright_black", box=ROUNDED, expand=True))
        return Group(hdr, Markdown(text, code_theme="ansi_dark"))

class AgentCommandProvider(Provider):
    async def search(self, query: str) -> Iterator[Hit]:
        m = self.matcher(query)
        cmds = [
            ("Copy Last Response", "copy_last_response", "Copy the latest agent response to system clipboard"),
            ("Copy Entire Chat Page", "copy_entire_chat", "Copy complete conversation transcript to system clipboard"),
            ("Attach Image URL", "attach_image_url", "Attach an image URL to analyze on your next query"),
            ("Cycle Theme", "cycle_theme", "Cycle through available color themes"),
            ("Toggle Sidebar", "toggle_sidebar", "Show or hide the metadata panel"),
            ("Toggle Compact Mode", "toggle_compact", "Toggle between dense and spacious spacing layouts"),
            ("Toggle Reasoning", "toggle_reasoning", "Enable or disable deep reasoning budget"),
            ("Toggle Bottom Bar", "toggle_footer", "Hide or show the bottom bar buttons"),
        ]
        for title, action, desc in cmds:
            score = m.match(title)
            if score > 0: yield Hit(score, Text(title), lambda act=action: self.app.run_action(act), help=desc)

class LocalAITUI(App):
    ENABLE_COMMAND_PALETTE = True
    THEMES: List[str] = ["dark", "grok"]

    @property
    def command_sources(self) -> Set[Any]: return {AgentCommandProvider}

    @property
    def border_accent(self) -> str:
        return "#444444" if getattr(self, "theme", "dark") == "grok" else "bright_blue"

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

    BINDINGS = [
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=True),
        Binding("ctrl+g", "toggle_compact", "Compact", show=True),
        Binding("ctrl+r", "toggle_reasoning", "Reasoning", show=True),
        Binding("ctrl+t", "cycle_theme", "Theme", show=True),
        Binding("ctrl+o", "copy_last_response", "Copy Out", show=True),
        Binding("ctrl+y", "attach_image_url", "Image", show=True),
        Binding("ctrl+c", "stop_generation", "Stop Out", show=True),
        Binding("ctrl+f", "toggle_footer", "Footer", show=False),
        Binding("pageup", "scroll_page_up", "Page Up", show=False),
        Binding("pagedown", "scroll_page_down", "Page Down", show=False),
        Binding("shift+up", "scroll_up", "Scroll Up", show=False),
        Binding("shift+down", "scroll_down", "Scroll Down", show=False),
        Binding("ctrl+q", "quit", "Exit TUI", show=False),
        Binding("escape", "quit", "Exit TUI", show=False),
    ]

    def __init__(self, workspace_path: str, model_name: str, is_agent: Optional[bool] = None) -> None:
        super().__init__()
        self.workspace_path, self.model_name = workspace_path, model_name
        self.safe_name = workspace_safe_name(workspace_path, os.path.expanduser("~"))
        
        self.gates_enabled = os.environ.get("AI_CONFIRM_GATES", "1") == "1"
        os.environ["AI_CONFIRM_GATES"] = "1" if self.gates_enabled else "0"
        
        self.gate_auth_event = threading.Event()
        self.gate_auth_result, self.entering_gate_authorization, self.current_gate_prompt = False, False, ""
        self.spell_enabled, self.active_skill, self.pending_skill_prefix = True, os.environ.get("AI_ACTIVE_SKILL", "default"), None
        
        self.is_agent = (os.environ.get("AI_IS_AGENT", "").lower() in ("1", "true", "yes") or "/projects/" in workspace_path) if is_agent is None else is_agent
        self.memory_active = load_tui_state("memory_active", True)
        self.db_turns, self.tpm_count = 0, 0
        self.refresh_db_counts()

        self.compact_mode = load_tui_state("compact_mode", False)
        self.reasoning_active, self.reasoning_budget, self.entering_reasoning_budget = False, 500, False
        self.active_image_url, self.entering_image_url = None, False
        
        cli_hist = os.environ.get("AI_SESSION_HISTORY")
        try: self.history: List[Dict[str, Any]] = json.loads(cli_hist) if cli_hist else []
        except Exception: self.history = []
        
        self.generation_cancelled, self.active_response, self.stats_turns = False, None, 0
        self.footer_hidden = load_tui_state("footer_hidden", False)

    def refresh_db_counts(self) -> None:
        try:
            t_res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "get-count", self.safe_name], capture_output=True, text=True, timeout=2)
            f_res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "get-tpm-count", self.safe_name], capture_output=True, text=True, timeout=2)
            self.db_turns, self.tpm_count = int(t_res.stdout.strip() or 0), int(f_res.stdout.strip() or 0)
        except Exception: pass

    def ensure_system_context(self) -> None:
        if not any(m.get("role") == "system" for m in self.history):
            s_list = [s.lstrip("-").lower() for s in self.active_skill.split() if s] if (self.active_skill and self.active_skill.lower() != "default") else []
            s_content = skills.load_skill_content(" ".join(s_list), SKILLS_DIR, CFG_DIR) if (skills and s_list) else ""
            base = BASE_PROMPT_AGENT if self.is_agent else (BASE_PROMPT_CHAT if not s_list else BASE_PROMPT)
            sys_p = s_content if (self.is_agent and s_content) else (base + (f"\n\n### Active Skill/Role Instructions:\n{s_content}\n" if s_content else ""))
            
            if self.is_agent:
                sys_p += f"\n\n### ACTIVE PROJECT WORKSPACE:\nYour active project root directory is: {self.workspace_path}\n"
                if hasattr(core, "EDIT_SYSTEM_ADD") and "### EDIT MODE" not in sys_p:
                    sys_p += core.EDIT_SYSTEM_ADD.format(ws=self.workspace_path) + core.TOOLS_SYSTEM_ADD.format(names="read_file, write_file, list_dir, run_command", ws=self.workspace_path)
                try:
                    map_files = [f for f in os.listdir(self.workspace_path) if f.startswith("index-map-") and f.endswith(".txt")]
                    if map_files:
                        with open(os.path.join(self.workspace_path, map_files[0]), "r", encoding="utf-8", errors="ignore") as mf:
                            cmap = mf.read().strip()
                            if cmap: sys_p += f"\n\n### CODESPACE MAP:\n{cmap}\n"
                except Exception: pass

            self.history.insert(0, {"role": "system", "content": sys_p})
            if self.is_agent and len(self.history) == 1:
                self.history.append({"role": "assistant", "content": "Agent: Workspace loaded. Awaiting instructions."})

    def get_db_status_string(self) -> str:
        if not self.is_agent: return "stateless"
        return f"active ({self.tpm_count} facts, {self.db_turns} turns)" if self.memory_active else "disabled"

    def update_welcome_banner(self) -> None:
        try:
            self.query_one("#welcome-banner", Static).update(Panel(
                Markdown("# Workspace Loaded • Awaiting Instructions\nType your query and press `Enter`.\n`Ctrl+B` toggle sidebar • `Ctrl+T` cycle themes • `/copy` copy page • `Ctrl+O` copy response."),
                border_style=self.border_accent, box=ROUNDED
            ))
        except Exception: pass

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
                        Markdown("# Workspace Loaded • Awaiting Instructions\nType your query and press `Enter`.\n`Ctrl+B` toggle sidebar • `Ctrl+T` cycle themes • `/copy` copy page • `Ctrl+O` copy response."),
                        border_style="bright_blue", box=ROUNDED
                    ), id="welcome-banner")
                with Horizontal(id="input-pane"):
                    yield Input(placeholder="Ask your agent anything...", id="chat-input")
                    yield FooterToggle("▲ Show", id="input-toggle")
        with Horizontal(id="footer-bar"):
            yield Footer(id="footer-keys")
            yield FooterToggle("▼ Hide", id="footer-toggle")

    def on_mount(self) -> None:
        if hasattr(self, "register_theme"):
            for t in (grok_theme, dark_theme):
                try: self.register_theme(t)
                except Exception: pass
        
        saved_theme = load_tui_state("tui_theme", "dark")
        if saved_theme in self.THEMES:
            try: self.theme = saved_theme
            except Exception: pass
        
        self.update_welcome_banner()
        self.chat_area = self.query_one("#chat-area", Vertical)
        self.chat_input = self.query_one("#chat-input", Input)
        self.update_footer_visibility()

        if len(self.history) > 1:
            try: self.query_one("#welcome-banner").remove()
            except Exception: pass
            for msg in self.history:
                r, c = msg.get("role"), msg.get("content")
                if r == "user" and c: self.chat_area.mount(Message("User", c))
                elif r == "assistant" and c: self.chat_area.mount(Message("Agent", c))

        self.chat_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        clean = CSI_U_REGEX.sub('', event.value)
        if clean != event.value: event.input.value = clean

    def update_stats_ui(self, turns: int, tps: float, elapsed: float) -> None:
        self.query_one("#lbl-stats", Static).update(f"Turns: {turns}\nSpeed: {tps:.1f} t/s\nElapsed: {elapsed:.1f}s")

    def action_scroll_page_up(self) -> None:
        self.chat_area.scroll_page_up(animate=False)

    def action_scroll_page_down(self) -> None:
        self.chat_area.scroll_page_down(animate=False)

    def action_scroll_up(self) -> None:
        self.chat_area.scroll_up(animate=False)

    def action_scroll_down(self) -> None:
        self.chat_area.scroll_down(animate=False)

    def action_copy_last_response(self) -> None:
        last = next((m.get("content", "") for m in reversed(self.history) if m.get("role") == "assistant"), "")
        if last:
            copy_to_clipboard(last.split("</think>", 1)[-1].strip() if "</think>" in last else last)
            self.chat_area.mount(Static("[dim white][sys] Copied latest agent response to clipboard.[/dim white]"))
        else:
            self.chat_area.mount(Static("[dim white][sys] No response available to copy yet.[/dim white]"))
        self.chat_area.scroll_end(animate=False)

    def action_copy_entire_chat(self) -> None:
        """Copies complete conversation transcript to system clipboard."""
        transcript = []
        for msg in self.history:
            role, content = msg.get("role"), msg.get("content")
            if not content or role == "system": continue
            if role == "user":
                txt = content if isinstance(content, str) else next((i["text"] for i in content if i.get("type") == "text"), "[Multimodal]")
                transcript.append(f"❯ USER: {txt}")
            elif role == "assistant":
                clean_c = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                if clean_c: transcript.append(f"❖ AGENT:\n{clean_c}")

        full_text = "\n\n".join(transcript)
        if full_text:
            copy_to_clipboard(full_text)
            self.chat_area.mount(Static("[dim white][sys] Copied entire session transcript to clipboard.[/dim white]"))
        else:
            self.chat_area.mount(Static("[dim white][sys] No transcript available to copy yet.[/dim white]"))
        self.chat_area.scroll_end(animate=False)

    async def handle_view_file(self, file_path: str) -> None:
        full_p = os.path.expanduser(file_path)
        if not os.path.isabs(full_p): full_p = os.path.join(self.workspace_path, file_path)
        if os.path.isfile(full_p):
            try:
                with open(full_p, "r", encoding="utf-8", errors="ignore") as f: content = f.read(12000)
                self.history.append({"role": "user", "content": f"[FILE LOADED: {file_path}]\n```\n{content}\n```"})
                await self.chat_area.mount(Static(f"[dim white][sys] Loaded file content into active context: [bold]{file_path}[/bold][/dim white]"))
            except Exception as e: await self.chat_area.mount(Static(f"[bold red][sys] Error reading file: {e}[/bold red]"))
        else: await self.chat_area.mount(Static(f"[bold red][sys] File not found: {file_path}[/bold red]"))
        self.chat_area.scroll_end(animate=False)

    async def handle_meta_chat_command(self, cmd_root: str) -> None:
        think_bin = os.path.join(CFG_DIR, "modules", "chat")
        try: self.query_one("#welcome-banner").remove()
        except Exception: pass

        self.ensure_system_context()
        c_raw = cmd_root.lstrip("/").lower()
        sub_arg = "/t" if c_raw in ("tk", "thinking") else f"/{c_raw}"
        hdr_map = {"f": "Follow-up", "b": "Brainstorm", "t": "Thinking", "tk": "Thinking", "a": "All"}
        output_hdr = hdr_map.get(c_raw, "Follow-up")
        
        await self.chat_area.mount(Message("User", f"/{c_raw}"))
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
                        formatted = f"**{lines[0]}**\n\n" + "\n\n".join(q.strip() for item in lines[1:] for q in QUESTION_SPLIT_REGEX.split(item) if q.strip()) if len(lines) > 1 else clean_out
                        self.call_from_thread(assistant_msg.update_content, formatted)
                        self.history.append({"role": "assistant", "content": formatted})
                        return
                except Exception as e: self.call_from_thread(assistant_msg.update_content, f"[red][sys] Chat error: {e}[/red]")
            else: self.call_from_thread(assistant_msg.update_content, "[red][sys] modules/chat script not found.[/red]")

        self.run_worker(_run_chat_sub, thread=True)

    async def handle_slash_command(self, cmd: str) -> None:
        parts = cmd.split(maxsplit=1)
        root, args = parts[0].lower(), parts[1] if len(parts) > 1 else ""

        if root in ("/help", "/h"):
            t = Table(show_header=False, box=None, padding=(0, 1))
            cmd_style = "bold #b0b0b0" if self.theme == "grok" else "bold cyan"
            t.add_column("Command", style=cmd_style)
            t.add_column("Description", style="white")
            for c, d in [
                ("/help, /h", "Show command list"), ("/copy, /copy-all", "Copy entire page transcript"),
                ("/g, /yolo", "Toggle autonomous YOLO mode vs per-action gates"),
                ("/m", "Toggle long-term memory"), ("/clear, /reset", "Clear chat & history"),
                ("/tok", "Show token usage"), ("/sync, /re", "Sync codebase AST index"),
                ("/skill <q>, /s", "Load skill blueprint"), ("/compact, /c", "Toggle compact mode"),
                ("/t, /thinking", "Toggle reasoning budget"), ("/f, /tk, /b, /a", "Skill mode prompts"),
                ("view file <path>", "Attach file content to context"), ("exit, quit, q", "Exit TUI")
            ]: t.add_row(c, d)
            await self.chat_area.mount(Static(Panel(t, title="⚙ Agent TUI Commands", title_align="left", border_style=self.border_accent, box=ROUNDED)))

        elif root in ("exit", "quit", "q"): self.exit()
        elif root in ("/copy", "/copy-all", "/copyall"): self.action_copy_entire_chat()
        elif root == "/m":
            self.memory_active = not self.memory_active
            save_tui_state("memory_active", self.memory_active)
            self.query_one("#lbl-database", Static).update(self.get_db_status_string())
            await self.chat_area.mount(Static(f"[dim white][sys] Memory {'enabled' if self.memory_active else 'disabled'}.[/dim white]"))
        elif root in ("/g", "/yolo"):
            self.gates_enabled = not self.gates_enabled
            os.environ["AI_CONFIRM_GATES"] = "1" if self.gates_enabled else "0"
            self.query_one("#lbl-gates", Static).update("Enabled" if self.gates_enabled else "Autonomous")
            await self.chat_area.mount(Static(f"[dim white][sys] Confirmation gates {'enabled' if self.gates_enabled else 'disabled (YOLO Mode)'}.[/dim white]"))
        elif root in ("/clear", "/reset"):
            self.history.clear(); self.stats_turns = 0
            self.update_stats_ui(0, 0.0, 0.0)
            for child in list(self.chat_area.children): child.remove()
            await self.chat_area.mount(Static("[dim white][sys] Session history and chat window cleared.[/dim white]"))
        elif root == "/tok":
            est = sum(len(m.get("content", "")) // 4 for m in self.history)
            await self.chat_area.mount(Static(f"[dim white][sys] History: ~{est:,} tokens ({len(self.history)} messages)[/dim white]"))
        elif root in ("/sync", "/re"):
            await self.chat_area.mount(Static("[dim white][sys] Triggered background AST codebase sync.[/dim white]"))
            try: subprocess.Popen(["index-map", self.workspace_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception: pass
        elif root in ("/skill", "/s"):
            if args and skills:
                content = skills.load_skill_content(args, SKILLS_DIR, CFG_DIR)
                if content:
                    s_name, s_text = content if isinstance(content, tuple) else (args, content)
                    self.active_skill = s_name
                    self.query_one("#lbl-skill", Static).update(s_name)
                    self.history.append({"role": "system", "content": f"[SKILL BLUEPRINT: {s_name}]\n{s_text}"})
                    await self.chat_area.mount(Static(f"[dim white][sys] Loaded skill blueprint: [bold]{s_name}[/bold][/dim white]"))
                else: await self.chat_area.mount(Static(f"[dim white][sys] No skill blueprint file found for '[bold]{args}[/bold]'.[/dim white]"))
            else: await self.chat_area.mount(Static("[dim white][sys] Usage: /skill <query> or /s <query>[/dim white]"))
        elif root in ("/compact", "/c"): self.action_toggle_compact()
        elif root in ("/t", "/thinking"): self.action_toggle_reasoning()
        elif root in ("/f", "/tk", "/b", "/a"): await self.handle_meta_chat_command(root)
        else: await self.chat_area.mount(Static(f"[dim white][sys] Unknown command '{root}'. Type [bold]/help[/bold] for commands.[/dim white]"))

        self.chat_area.scroll_end(animate=False)

    def prompt_tui_confirm(self, prompt_text: str) -> bool:
        self.gate_auth_event.clear()
        self.gate_auth_result = False
        def _show():
            self.entering_gate_authorization, self.current_gate_prompt = True, prompt_text
            self.chat_input.disabled, self.chat_input.value = False, ""
            self.chat_input.placeholder = f"▲ Authorize: {prompt_text}? [Y/n]: "
            self.chat_input.focus()
        self.call_from_thread(_show)
        self.gate_auth_event.wait()
        return self.gate_auth_result

    def process_query_worker(self, query: str) -> None:
        try: self.call_from_thread(self.query_one("#welcome-banner").remove)
        except Exception: pass

        self.ensure_system_context()
        self.call_from_thread(self.chat_area.mount, Message("User", query))

        old_confirm = getattr(ui, "confirm_tool", None)
        ui.confirm_tool = lambda reason: self.prompt_tui_confirm(reason)

        try:
            past_mem, tpm_ctx = "", ""
            if self.memory_active:
                try:
                    mem_bin = os.path.join(CFG_DIR, "modules", "ai-agent-memories")
                    if os.path.exists(mem_bin):
                        tpm_res = subprocess.run([sys.executable, mem_bin, "tpm-get", self.safe_name], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=2)
                        if tpm_res.returncode == 0 and tpm_res.stdout.strip(): tpm_ctx = tpm_res.stdout.strip()

                    matched = get_recalled_memory(self.safe_name, query)
                    if matched:
                        if not self.gates_enabled or self.prompt_tui_confirm(f"inject recalled memory for '{query}'"):
                            past_mem = matched
                            self.call_from_thread(self.chat_area.mount, Static("[dim white][sys] Memory injected.[/dim white]"))
                        else:
                            self.call_from_thread(self.chat_area.mount, Static("[dim white][sys] Memory recall skipped.[/dim white]"))
                except Exception: pass

            assistant_msg = Message("Agent", "Thinking...")
            self.call_from_thread(self.chat_area.mount, assistant_msg)
            self.call_from_thread(self.chat_area.scroll_end, animate=False)

            try: sys_ctx = skills.get_system_context(query, CONTEXT_FILE, STOP_WORDS, SKILLS_DIR, CFG_DIR) if (skills and hasattr(skills, "get_system_context")) else ""
            except Exception: sys_ctx = ""
            if sys_ctx == "__ABORT_TURN__": sys_ctx = ""

            combined = "\n\n".join(filter(None, [tpm_ctx, past_mem, sys_ctx]))
            fmt_p = f"<context>\n{combined}\n</context>\n\nUser Question: {query}" if combined else f"User Question: {query}"

            if self.active_image_url:
                self.history.append({"role": "user", "content": [{"type": "text", "text": fmt_p}, {"type": "image_url", "image_url": {"url": self.active_image_url}}]})
                self.active_image_url = None
                self.call_from_thread(self.query_one("#lbl-image", Static).update, "None")
            else: self.history.append({"role": "user", "content": fmt_p})

            self.call_from_thread(self.disable_input)
            self.generation_cancelled, self.active_response = False, None
            accumulated, start_time, first_token_time, token_count = "", time.perf_counter(), None, 0
            thinking_budget = self.reasoning_budget if self.reasoning_active else 0

            for _round in range(10):
                accumulated, in_thinking, tool_calls_map = "", False, {}
                configs = agent_cloud.get_active_configs(self.history) if agent_cloud else []
                local_extra = {"thinking_budget_tokens": thinking_budget, "chat_template_kwargs": {"enable_thinking": True}} if thinking_budget > 0 else {"chat_template_kwargs": {"enable_thinking": False}}

                url, headers, body, timeout = configs[0] if configs else ("http://localhost:8080/v1/chat/completions", {}, {"messages": self.history, "stream": True, "model": "local-model", **local_extra}, 180)
                body["stream"], body["messages"] = True, self.history
                if self.is_agent and hasattr(core, "_EDIT_TOOLS"): body["tools"] = core._EDIT_TOOLS

                req = urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", **headers}, method="POST")

                with urlreq.urlopen(req, timeout=timeout) as response:
                    self.active_response = response
                    if response.status != 200: raise Exception(f"HTTP {response.status}: {response.read().decode('utf-8', errors='ignore')[:200]}")

                    for line in response:
                        if self.generation_cancelled or not line.startswith(b"data:"): continue
                        dec = line.decode("utf-8", errors="ignore").strip()[5:].strip()
                        if dec == "[DONE]": break

                        try:
                            data = json.loads(dec)
                            choices = data.get("choices", [{}])
                            if not choices: continue
                            delta = choices[0].get("delta", {})
                            text_chunk, thinking_chunk = delta.get("content") or "", delta.get("reasoning_content") or delta.get("thinking") or ""

                            for tc in delta.get("tool_calls", []):
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_map: tool_calls_map[idx] = {"id": tc.get("id", ""), "type": "function", "function": {"name": tc.get("function", {}).get("name", ""), "arguments": ""}}
                                if tc.get("function", {}).get("name"): tool_calls_map[idx]["function"]["name"] = tc["function"]["name"]
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
                calls = [v for _, v in sorted(tool_calls_map.items())] if tool_calls_map else None
                if not calls:
                    self.history.append({"role": "assistant", "content": accumulated})
                    break

                self.history.append({"role": "assistant", "content": accumulated or None, "tool_calls": calls})
                user_aborted = False

                for tc in calls:
                    fname, raw_args = tc.get("function", {}).get("name", ""), tc.get("function", {}).get("arguments", "")
                    args = json.loads(raw_args) if raw_args else {}
                    brief = str(args.get("path") or args.get("command") or "")[:100]
                    verb = getattr(core, "TOOL_VERBS", {}).get(fname, "working")

                    if user_aborted: result = "[denied] execution cancelled by user"
                    else:
                        if self.gates_enabled and not self.prompt_tui_confirm(f"{fname} {brief}"):
                            result, user_aborted = f"[denied] user rejected {fname}", True
                            self.history.append({"role": "tool", "tool_call_id": tc.get("id", ""), "name": fname, "content": result})
                            continue

                        self.call_from_thread(self.chat_area.mount, Static(f"[dim white][sys] ∗ {verb} • [bold cyan]{fname}[/bold cyan] [italic]{brief}[/italic][/dim white]"))
                        self.call_from_thread(self.chat_area.scroll_end, animate=False)
                        try:
                            old_g = os.environ.get("AI_CONFIRM_GATES")
                            os.environ["AI_CONFIRM_GATES"] = "0"
                            result = core._run_edit_tool(fname, args, self.workspace_path)
                            if old_g: os.environ["AI_CONFIRM_GATES"] = old_g
                            if "[denied]" in result: user_aborted = True
                        except Exception as te: result = f"[tool error] {te}"

                    self.history.append({"role": "tool", "tool_call_id": tc.get("id", ""), "name": fname, "content": result})

                if user_aborted:
                    self.call_from_thread(self.chat_area.mount, Static("[dim white][sys] Execution halted by user gate.[/dim white]"))
                    break

                assistant_msg = Message("Agent", "Processing tool results...")
                self.call_from_thread(self.chat_area.mount, assistant_msg)

            end_time = time.perf_counter()
            total_elapsed = max(0.01, end_time - start_time)
            gen_dur = max(0.001, end_time - first_token_time) if first_token_time else total_elapsed
            tps = (token_count / gen_dur) if first_token_time and token_count > 0 else (len(accumulated) // 4) / total_elapsed

            self.stats_turns += 1
            self.call_from_thread(self.update_stats_ui, self.stats_turns, tps, total_elapsed)

            if query:
                try:
                    subprocess.Popen([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "log-turn", self.safe_name, query, accumulated], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.refresh_db_counts()
                    self.call_from_thread(self.query_one("#lbl-database", Static).update, self.get_db_status_string())
                except Exception: pass

        except Exception as e:
            if self.generation_cancelled: self.call_from_thread(assistant_msg.update_content, accumulated + " [dim white](stopped)[/dim white]")
            else: self.call_from_thread(assistant_msg.update_content, f"[red][sys] Error: {e}[/red]")
        finally:
            self.active_response = None
            if old_confirm: ui.confirm_tool = old_confirm
            self.call_from_thread(self.enable_input)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = CSI_U_REGEX.sub('', event.value.strip()).strip()
        self.chat_input.value = ""

        if getattr(self, "entering_gate_authorization", False):
            self.entering_gate_authorization = False
            self.chat_input.placeholder = "Ask your agent anything..."
            is_yes = query.lower() in ("y", "yes", "")
            self.gate_auth_result = is_yes
            self.gate_auth_event.set()
            color, status = ("green", "Authorized") if is_yes else ("red", "Denied")
            await self.chat_area.mount(Static(f"[dim white][sys] Gate: [bold {color}]{status}[/bold {color}][/dim white]"))
            self.chat_area.scroll_end(animate=False)
            return

        if not query: return
        if self.pending_skill_prefix:
            query, self.pending_skill_prefix = f"{self.pending_skill_prefix} {query}", None
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
                await self.chat_area.mount(Static("[dim white][sys] Deep reasoning enabled (default 500 tokens).[/dim white]"))
            else:
                try:
                    val = int(query)
                    if val > 0:
                        self.reasoning_budget, self.reasoning_active = val, True
                        self.query_one("#lbl-reasoning", Static).update(f"{val} tokens")
                        await self.chat_area.mount(Static(f"[dim white][sys] Deep reasoning enabled ({val} tokens).[/dim white]"))
                    else: raise ValueError
                except ValueError:
                    self.reasoning_active = False
                    self.query_one("#lbl-reasoning", Static).update("Disabled")
                    await self.chat_area.mount(Static("[bold red][sys] Invalid budget. Deep reasoning disabled.[/bold red]"))
            self.chat_area.scroll_end(animate=False)
            return

        if self.entering_image_url:
            self.entering_image_url, self.active_image_url = False, query
            self.chat_input.placeholder = "Ask your agent anything..."
            fname = query.split("/")[-1].split("?")[0][:25]
            self.query_one("#lbl-image", Static).update(fname or "image_attached")
            await self.chat_area.mount(Static(f"[dim white][sys] Attached image URL: [bold]{query}[/bold][/dim white]"))
            self.chat_area.scroll_end(animate=False)
            return

        self.run_worker(lambda: self.process_query_worker(query), thread=True)

    def disable_input(self) -> None:
        if not getattr(self, "entering_gate_authorization", False): self.chat_input.disabled = True

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
            self.query_one("#footer-bar", Horizontal).display = not self.footer_hidden
            self.query_one("#input-toggle", Static).display = self.footer_hidden
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
        self.chat_area.mount(Static(f"[dim white][sys] Compact mode {'enabled' if self.compact_mode else 'disabled'}.[/dim white]"))
        self.chat_area.scroll_end(animate=False)

    def action_cycle_theme(self) -> None:
        try:
            current_idx = self.THEMES.index(self.theme) if self.theme in self.THEMES else 0
            self.theme = self.THEMES[(current_idx + 1) % len(self.THEMES)]
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
    except Exception: model = ui.get_local_model_name()
            
    app = LocalAITUI(workspace, model)
    try:
        app.run()
    finally:
        try:
            subprocess.run(["stty", "sane"], check=False)
            sys.stdout.write("\033[0m\033[?25h")
            sys.stdout.flush()
        except Exception: pass
