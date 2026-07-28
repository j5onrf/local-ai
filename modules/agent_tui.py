#!/usr/bin/env python3
# File: ~/.config/local-ai/modules/agent_tui.py
"""Production Minimal Textual TUI for Local-AI Agent Engine."""

import base64, json, os, re, sqlite3, subprocess, sys, threading, time
import urllib.request as urlreq
from contextlib import closing
from typing import Any, Dict, Iterator, List, Optional, Set

from rich.box import Box, ROUNDED
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

LEFT_BAR = Box("▌   \n▌   \n▌   \n▌   \n▌   \n▌   \n▌   \n▌   \n")
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

ACTIVE_THEME = "code"

def get_dynamic_code_block_background() -> str:
    global ACTIVE_THEME
    t = str(ACTIVE_THEME).lower()
    return "#0d0d0d" if "grok" in t else ("#1a1a1a" if "dark" in t else "#1b1c2b")

def custom_code_block_rich_console(self, console, options):
    yield Syntax(str(self.text).rstrip(), self.lexer_name, theme="github-dark", word_wrap=True, padding=(1, 2), background_color=get_dynamic_code_block_background())

CodeBlock.__rich_console__ = custom_code_block_rich_console

BASE_PROMPT = "Read-only local shell assistant.\nIf <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n\n"
BASE_PROMPT_CHAT = BASE_PROMPT + "### Conversational Guidelines:\n- Role: Active, natural, and highly articulate conversational assistant.\n- Tone: Professional, warm, objective, and intellectually engaging.\n\n"
BASE_PROMPT_AGENT = "Active local project workspace developer agent.\nIf <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n\n"

def workspace_safe_name(workspace_path: str, home_dir: str) -> str:
    if os.path.abspath(workspace_path) == os.path.abspath(home_dir):
        return "home"
    rel = os.path.relpath(workspace_path, home_dir)
    if rel.startswith(".."):
        rel = workspace_path
    clean = rel.lstrip(".").replace("/", "-").strip("-")
    return clean or "home"

def format_dir_path(path: str) -> str:
    p = path.replace(os.path.expanduser("~"), "~")
    return p if len(p) <= 20 else f".../{os.path.basename(path.rstrip('/'))}"

def load_tui_state(key: str, default: Any) -> Any:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f: return json.load(f).get(key, default)
        except Exception: pass
    return default

def save_tui_state(key: str, value: Any) -> None:
    data = {}
    os.makedirs(CFG_DIR, exist_ok=True)
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
    q_tokens = set(tokenize(query))
    db_path = os.path.join(SESSIONS_DIR, f"{workspace}.db")
    if not q_tokens or not os.path.exists(db_path): return ""
    try:
        with closing(sqlite3.connect(db_path, timeout=5)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_msg, assistant_msg, tokens, timestamp FROM turns WHERE workspace = ?", (workspace,))
            rows = cur.fetchall()

        candidates = []
        for u, a, t, ts in rows:
            t_tokens = set(t.split()) if t else set()
            score = len(q_tokens & t_tokens) / len(q_tokens | t_tokens) if (q_tokens & t_tokens) else 0.0
            if score >= 0.35: candidates.append((score, u, a, time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))))

        if not candidates: return ""
        candidates.sort(key=lambda x: -x[0])
        blocks = [f"* **On {dt} you asked**: \"{u.strip()}\"\n  **Agent responded**: \"{re.sub(r'<think>.*?</think>', '', a, flags=re.DOTALL).strip()}\"" for _, u, a, dt in candidates[:3]]
        return "### Relevant Past Discussion (Retrieved from Session Memory):\n" + "\n\n".join(blocks)
    except Exception: return ""

code_theme = Theme(name="code", primary="#cba6f7", secondary="#a6adc8", accent="#cba6f7", background="#11121d", surface="#161726", panel="#1b1c2b")
grok_theme = Theme(name="grok", primary="#444444", secondary="#888888", accent="#ffffff", background="#000000", surface="#0d0d0d", panel="#121212")
dark_theme = Theme(name="dark", primary="#555555", secondary="#b0b0b0", accent="#ffffff", background="#121212", surface="#1c1c1c", panel="#242424")

class FooterToggle(Static):
    def on_click(self) -> None:
        if hasattr(self.app, "action_toggle_footer"): self.app.action_toggle_footer()

class CloseCardButton(Static):
    def on_click(self) -> None:
        if hasattr(self.app, "action_close_tips_card"): self.app.action_close_tips_card()

class Message(Static):
    def __init__(self, sender: str, content: Any) -> None:
        super().__init__()
        self.sender, self.content = sender, content

    def update_content(self, new_content: Any) -> None:
        self.content = new_content
        self.refresh()

    def render(self) -> Group:
        compact, theme = getattr(self.app, "compact_mode", False), getattr(self.app, "theme", "code")
        self.styles.color = "#c8d3f5" if theme == "code" else None
        u_style, a_style = (("bold bright_white", "bold #b0b0b0") if theme == "grok" else ("bold #89b4fa", "bold #a6e3a1") if theme == "code" else ("bold cyan", "bold green"))

        if self.sender == "User":
            text = self.content
            if isinstance(text, list): text = next((i["text"] for i in text if i.get("type") == "text"), "[Multimodal]")
            if not compact:
                bar_col = "#555555" if theme == "grok" else ("cyan" if theme == "dark" else "#cba6f7")
                bg_col = get_dynamic_code_block_background()
                user_txt_col = "#c8d3f5" if theme == "code" else "white"
                return Panel(Text(text, style=user_txt_col), box=LEFT_BAR, border_style=bar_col, style=f"on {bg_col}", padding=(0, 1))
            return Text(f"❯ {text}", style=u_style)

        text = str(self.content or "")
        if "<think>" in text:
            before, after = text.split("<think>", 1)
            border_col = getattr(self.app, "border_accent", "bright_black")
            if "</think>" in after:
                think, rest = after.split("</think>", 1)
                panel = Panel(Text(think.strip(), style="italic dim white"), title="⚙ Thinking Process", title_align="left", border_style=border_col, box=ROUNDED, expand=True)
                body = Markdown(before + rest.strip(), code_theme="ansi_dark") if (before + rest).strip() else Text("")
                return Group(panel, body)
            return Panel(Text(after.strip(), style="italic dim white"), title="⚙ Thinking Process...", title_align="left", border_style=border_col, box=ROUNDED, expand=True)
        return Markdown(text, code_theme="ansi_dark")

class AgentCommandProvider(Provider):
    async def search(self, query: str) -> Iterator[Hit]:
        m = self.matcher(query)
        cmds = [
            ("Copy Last Response", "copy_last_response", "Copy latest agent response"),
            ("Copy Entire Chat Page", "copy_entire_chat", "Copy complete conversation transcript"),
            ("Attach Image URL", "attach_image_url", "Attach an image URL to analyze"),
            ("Cycle Theme", "cycle_theme", "Cycle through color themes"),
            ("Toggle Sidebar", "toggle_sidebar", "Show or hide metadata panel"),
            ("Toggle Compact Mode", "toggle_compact", "Toggle spacing layouts"),
            ("Toggle Reasoning", "toggle_reasoning", "Enable or disable reasoning budget"),
            ("Toggle Mode (Plan/Build)", "toggle_plan_build", "Switch between Plan and Build modes"),
        ]
        for title, action, desc in cmds:
            score = m.match(title)
            if score > 0: yield Hit(score, Text(title), lambda act=action: self.app.run_action(act), help=desc)

class LocalAITUI(App):
    ENABLE_COMMAND_PALETTE = True
    THEMES: List[str] = ["code", "dark", "grok"]

    @property
    def command_sources(self) -> Set[Any]: return {AgentCommandProvider}

    @property
    def border_accent(self) -> str:
        t = getattr(self, "theme", "code")
        return "bright_white" if t == "grok" else ("bright_blue" if t == "dark" else "#cba6f7")

    CSS = """
    Screen { background: $background; }
    #layout { height: 1fr; }
    #main-container { height: 100%; width: 1fr; background: transparent; }
    #chat-area { height: 1fr; background: transparent; overflow-y: scroll; padding: 1 0 1 2; }
    #welcome-banner { margin-right: 2; }
    #input-pane { height: 3; border: none; background: $surface; padding: 0; margin: 0; align: left middle; }
    #input-bar { width: auto; height: 100%; color: $primary; padding: 0; margin: 0; }
    Input { width: 1fr; border: none; outline: none; background: transparent; height: 1; color: $text; padding: 0 1; margin-top: 1; }
    Input:focus { border: none; outline: none; }
    #input-toggle { width: auto; height: 100%; content-align: center middle; color: $secondary; padding: 0 1; }
    #input-toggle:hover { background: $primary; color: $text; text-style: bold; }
    #sidebar { width: 30; height: 100%; background: $surface; border-left: solid #1a1b2a; padding: 1 1; align: left top; }
    Message { margin-top: 1; margin-right: 2; height: auto; }
    #chat-area > Message:first-child { margin-top: 0; }
    .sidebar-section { height: auto; border-bottom: none; padding-bottom: 1; margin-bottom: 1; }
    .sidebar-label { color: $primary; text-style: bold; margin-bottom: 0; }
    .sidebar-val { color: $text; margin-bottom: 0; }
    #card-tips { background: $panel; padding: 1; margin-top: 1; }
    #card-tips-header { height: 1; width: 100%; }
    #lbl-tips-title { width: 1fr; color: $primary; text-style: bold; }
    #btn-close-tips { width: auto; color: $secondary; text-style: bold; }
    #btn-close-tips:hover { color: red; }
    #lbl-tips-body { color: $secondary; margin-top: 1; }
    #footer-bar { dock: bottom; height: 1; width: 100%; background: $surface; }
    #footer-keys { dock: none; width: 1fr; height: 1; }
    """

    BINDINGS = [
        Binding("tab", "toggle_plan_build", "Toggle Mode", show=False),
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=True),
        Binding("ctrl+g", "toggle_compact", "Compact", show=True),
        Binding("ctrl+r", "toggle_reasoning", "Reasoning", show=True),
        Binding("ctrl+t", "cycle_theme", "Theme", show=True),
        Binding("ctrl+o", "copy_last_response", "Copy Out", show=True),
        Binding("ctrl+y", "attach_image_url", "Image", show=True),
        Binding("ctrl+c", "stop_generation", "Stop Out", show=True),
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
        self.agent_mode = "Plan"
        self.gates_enabled = True
        os.environ["AI_CONFIRM_GATES"] = "1"
        
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
        self.footer_hidden = load_tui_state("footer_hidden", True)
        self.sidebar_hidden = load_tui_state("sidebar_hidden", False)
        self.tips_card_hidden = load_tui_state("tips_card_hidden", False)

    def on_unmount(self) -> None:
        self.gate_auth_result = False
        self.gate_auth_event.set()
        if self.active_response:
            try: self.active_response.close()
            except Exception: pass

    def notify(self, text: str, sys_prefix: bool = True, css_class: str = "sys-notice") -> None:
        """Centralized helper for mounting system status notifications."""
        fmt = f"[dim white][sys] {text}[/dim white]" if sys_prefix else text
        self.chat_area.mount(Static(fmt, classes=css_class))
        self.chat_area.scroll_end(animate=False)

    def set_skill(self, skill_name: str) -> None:
        self.active_skill = skill_name
        t = getattr(self, "theme", "code")
        bg, fg = ("#26273b", "#cba6f7") if t == "code" else ("#222222", "#ffffff") if t == "grok" else ("#333333", "#e0e0e0")
        try: self.query_one("#lbl-skill", Static).update(f"[dim]Skill[/dim]   [bold {fg} on {bg}] {skill_name} [/]")
        except Exception: pass

    def set_mode(self, mode_name: str) -> None:
        self.agent_mode = mode_name
        try: self.query_one("#lbl-mode", Static).update(f"[dim]Mode[/dim]    {mode_name}")
        except Exception: pass

    def set_reasoning(self, text: str) -> None:
        try: self.query_one("#lbl-reasoning", Static).update(f"[dim]Reasoning[/dim] {text}")
        except Exception: pass

    def set_image(self, text: str) -> None:
        try: self.query_one("#lbl-image", Static).update(f"[dim]Image[/dim]     {text}")
        except Exception: pass

    def on_key(self, event) -> None:
        if event.key == "tab":
            self.action_toggle_plan_build()
            event.prevent_default()
            event.stop()

    def refresh_db_counts(self) -> None:
        sessions_bin = os.path.join(CFG_DIR, "modules", "ai-agent-sessions")
        memories_bin = os.path.join(CFG_DIR, "modules", "ai-agent-memories")
        try:
            if os.path.exists(sessions_bin):
                t_res = subprocess.run([sys.executable, sessions_bin, "get-count", self.safe_name], capture_output=True, text=True, timeout=2)
                self.db_turns = int(t_res.stdout.strip() or 0)
            if os.path.exists(memories_bin):
                f_res = subprocess.run([sys.executable, memories_bin, "get-tpm-count", self.safe_name], capture_output=True, text=True, timeout=2)
                self.tpm_count = int(f_res.stdout.strip() or 0)
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
                    if os.path.exists(self.workspace_path):
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
            banner_md = Markdown(
                "Type your query below and press **`Enter`**.\n\n"
                "• **`Tab`** : Switch Plan / Build Mode\n"
                "• **`Ctrl+B`** : Toggle Sidebar\n"
                "• **`Ctrl+T`** : Cycle Color Themes\n"
                "• **`Ctrl+O`** : Copy Agent Response\n"
                "• **`▲ Show`** : Toggle Bottom Shortcut Bar\n"
                "• **`/help`** : View All Commands"
            )
            self.query_one("#welcome-banner", Static).update(Panel(banner_md, border_style=self.border_accent, box=ROUNDED, padding=(1, 2)))
        except Exception: pass

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            with Vertical(id="main-container"):
                with Vertical(id="chat-area"):
                    yield Static(id="welcome-banner")
                with Horizontal(id="input-pane"):
                    yield Static("▌\n▌\n▌", id="input-bar")
                    yield Input(placeholder="  Ask your agent anything...", id="chat-input")
                    yield FooterToggle("▲ Show", id="input-toggle")
            
            with Vertical(id="sidebar"):
                with Vertical(classes="sidebar-section"):
                    yield Static("MODEL & SESSION", classes="sidebar-label")
                    yield Static(f"[dim]Model[/dim]   {self.model_name}", id="lbl-model", classes="sidebar-val")
                    yield Static(f"[dim]Dir[/dim]     {format_dir_path(self.workspace_path)}", id="lbl-dir", classes="sidebar-val")
                    yield Static(f"[dim]Skill[/dim]   {self.active_skill}", id="lbl-skill", classes="sidebar-val")
                    yield Static(f"[dim]Mode[/dim]    {self.agent_mode}", id="lbl-mode", classes="sidebar-val")
                
                with Vertical(classes="sidebar-section"):
                    yield Static("SETTINGS", classes="sidebar-label")
                    yield Static("[dim]Reasoning[/dim] Disabled", id="lbl-reasoning", classes="sidebar-val")
                    yield Static("[dim]Image[/dim]     None", id="lbl-image", classes="sidebar-val")
                
                with Vertical(classes="sidebar-section"):
                    yield Static("CONTEXT & MEMORY", classes="sidebar-label")
                    yield Static(f"[dim]DB State[/dim]  {self.get_db_status_string()}", id="lbl-database", classes="sidebar-val")
                    yield Static("Turns: 0 | Speed: -- t/s", id="lbl-stats", classes="sidebar-val")

                with Vertical(id="card-tips"):
                    with Horizontal(id="card-tips-header"):
                        yield Static("Quick Tips", id="lbl-tips-title")
                        yield CloseCardButton("×", id="btn-close-tips")
                    yield Static("Tab: Switch Mode\nCtrl+B: Toggle Sidebar\n/help: Commands List", id="lbl-tips-body")

        with Horizontal(id="footer-bar"):
            yield Footer(id="footer-keys")

    def action_close_tips_card(self) -> None:
        self.tips_card_hidden = True
        save_tui_state("tips_card_hidden", True)
        try: self.query_one("#card-tips", Vertical).display = False
        except Exception: pass

    def on_mount(self) -> None:
        if hasattr(self, "register_theme"):
            for t in (code_theme, grok_theme, dark_theme):
                try: self.register_theme(t)
                except Exception: pass
        
        saved_theme = load_tui_state("tui_theme", "code")
        if saved_theme in self.THEMES:
            try: self.theme = saved_theme
            except Exception: pass
        global ACTIVE_THEME
        ACTIVE_THEME = self.theme

        self.set_skill(self.active_skill)
        self.update_welcome_banner()
        self.chat_area = self.query_one("#chat-area", Vertical)
        self.chat_input = self.query_one("#chat-input", Input)
        self.chat_input.cursor_blink = True
        self.update_footer_visibility()
        self.update_sidebar_visibility()

        if self.tips_card_hidden:
            try: self.query_one("#card-tips", Vertical).display = False
            except Exception: pass

        if len(self.history) > 1:
            try: self.query_one("#welcome-banner").remove()
            except Exception: pass
            for msg in self.history:
                r, c = msg.get("role"), msg.get("content")
                if r == "user" and c: self.chat_area.mount(Message("User", c))
                elif r == "assistant" and c: self.chat_area.mount(Message("Agent", c))

        self.chat_input.focus()

    def action_toggle_plan_build(self) -> None:
        self.agent_mode, self.gates_enabled = ("Build", False) if self.agent_mode == "Plan" else ("Plan", True)
        os.environ["AI_CONFIRM_GATES"] = "1" if self.gates_enabled else "0"
        self.set_mode(self.agent_mode)

    def on_input_changed(self, event: Input.Changed) -> None:
        clean = CSI_U_REGEX.sub('', event.value)
        if clean != event.value: event.input.value = clean
        if event.value.strip(): self.chat_input.cursor_blink = False

    def update_stats_ui(self, turns: int, tps: float, elapsed: float) -> None:
        try: self.query_one("#lbl-stats", Static).update(f"Turns: {turns} | Speed: {tps:.1f} t/s")
        except Exception: pass

    def action_scroll_page_up(self) -> None: self.chat_area.scroll_page_up(animate=False)
    def action_scroll_page_down(self) -> None: self.chat_area.scroll_page_down(animate=False)
    def action_scroll_up(self) -> None: self.chat_area.scroll_up(animate=False)
    def action_scroll_down(self) -> None: self.chat_area.scroll_down(animate=False)

    def action_copy_last_response(self) -> None:
        last = next((m.get("content", "") for m in reversed(self.history) if m.get("role") == "assistant"), "")
        if last:
            copy_to_clipboard(last.split("</think>", 1)[-1].strip() if "</think>" in last else last)
            self.notify("Copied latest agent response to clipboard.")
        else: self.notify("No response available to copy yet.")

    def action_copy_entire_chat(self) -> None:
        transcript = []
        for msg in self.history:
            role, content = msg.get("role"), msg.get("content")
            if not content or role == "system": continue
            if role == "user":
                txt = content if isinstance(content, str) else next((i["text"] for i in content if i.get("type") == "text"), "[Multimodal]")
                transcript.append(f"❯ USER: {txt}")
            elif role == "assistant":
                clean_c = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                if clean_c: transcript.append(f"AGENT:\n{clean_c}")

        full_text = "\n\n".join(transcript)
        if full_text:
            copy_to_clipboard(full_text)
            self.notify("Copied entire session transcript to clipboard.")
        else: self.notify("No transcript available to copy yet.")

    async def handle_view_file(self, file_path: str) -> None:
        full_p = os.path.expanduser(file_path)
        if not os.path.isabs(full_p): full_p = os.path.join(self.workspace_path, file_path)
        if os.path.isfile(full_p):
            try:
                with open(full_p, "r", encoding="utf-8", errors="ignore") as f: content = f.read(12000)
                self.history.append({"role": "user", "content": f"[FILE LOADED: {file_path}]\n```\n{content}\n```"})
                self.notify(f"Loaded file content into active context: [bold]{file_path}[/bold]")
            except Exception as e: self.notify(f"[bold red]Error reading file: {e}[/bold red]", sys_prefix=False)
        else: self.notify(f"[bold red]File not found: {file_path}[/bold red]", sys_prefix=False)

    async def handle_meta_chat_command(self, cmd_root: str, args: str = "") -> None:
        think_bin = os.path.join(CFG_DIR, "modules", "chat")
        try: self.query_one("#welcome-banner").remove()
        except Exception: pass

        self.ensure_system_context()
        c_raw = cmd_root.lstrip("/").lower()
        sub_arg = "/t" if c_raw in ("tk", "thinking") else f"/{c_raw}"
        hdr_map = {"f": "Follow-up", "b": "Brainstorm", "t": "Thinking", "tk": "Thinking", "a": "All"}
        output_hdr = hdr_map.get(c_raw, "Follow-up")
        
        user_disp = f"/{c_raw} {args}".strip()
        await self.chat_area.mount(Message("User", user_disp))
        if args:
            self.history.append({"role": "user", "content": args})

        assistant_msg = Message("Agent", f"Generating {output_hdr}...")
        await self.chat_area.mount(assistant_msg)
        self.chat_area.scroll_end(animate=False)

        self.set_skill(output_hdr.lower())

        def _run_chat_sub():
            if os.path.exists(think_bin):
                try:
                    res = subprocess.run([sys.executable, think_bin, sub_arg], input=json.dumps(self.history), capture_output=True, text=True, timeout=30)
                    out = (res.stdout or res.stderr or "").strip()
                    if out:
                        clean_out = ANSI_CLEAN_REGEX.sub('', out)
                        if clean_out.startswith("AI:"): clean_out = clean_out[3:].strip()
                        lines = [l.strip() for l in clean_out.splitlines() if l.strip()]
                        formatted = f"**{lines[0]}**\n\n" + "\n\n".join(q.strip() for item in lines[1:] for q in QUESTION_SPLIT_REGEX.split(item) if q.strip()) if len(lines) > 1 else clean_out
                        self.call_from_thread(assistant_msg.update_content, formatted)
                        self.history.append({"role": "assistant", "content": formatted})
                    else:
                        self.call_from_thread(assistant_msg.update_content, "[red][sys] Chat returned no output.[/red]")
                except Exception as e: self.call_from_thread(assistant_msg.update_content, f"[red][sys] Chat error: {e}[/red]")
            else: self.call_from_thread(assistant_msg.update_content, "[red][sys] modules/chat script not found.[/red]")

        self.run_worker(_run_chat_sub, thread=True)

    async def handle_slash_command(self, cmd: str) -> None:
        try: self.query_one("#welcome-banner").remove()
        except Exception: pass

        parts = cmd.split(maxsplit=1)
        root, args = parts[0].lower(), parts[1] if len(parts) > 1 else ""

        if root in ("/help", "/h"):
            t = Table(show_header=False, box=None, padding=(0, 1), expand=False)
            cmd_style = "bold #89b4fa" if self.theme == "code" else "bold cyan"
            t.add_column("Command", style=cmd_style)
            t.add_column("Description", style="white")
            for c, d in [
                ("/help, /h", "Show command list"),
                ("/plan, /build, (tab)", "Switch Plan vs Build"),
                ("/copy", "Copy entire page transcript"),
                ("/m", "Toggle long-term memory"),
                ("/clear, /reset", "Clear chat & history"),
                ("/tok", "Show token usage"),
                ("/sync", "Sync codebase AST index"),
                ("/s <q>", "Load skill"),
                ("/c", "Toggle compact mode"),
                ("/t <toks>", "Toggle thinking, set budget"),
                ("/f, /tk, /b, /a", "Skill mode prompts"),
                ("file <path>", "Attach file content to context"),
                ("exit, quit, q", "Exit TUI")
            ]: t.add_row(c, d)
            await self.chat_area.mount(Static(Panel(t, title="⚙ Agent TUI Commands", title_align="left", border_style=self.border_accent, box=ROUNDED, expand=False)))

        elif root in ("exit", "quit", "q"): self.exit()
        elif root in ("/copy", "/copy-all", "/copyall"): self.action_copy_entire_chat()
        elif root == "/m":
            self.memory_active = not self.memory_active
            save_tui_state("memory_active", self.memory_active)
            self.query_one("#lbl-database", Static).update(self.get_db_status_string())
            self.notify(f"Memory {'enabled' if self.memory_active else 'disabled'}.")
        elif root in ("/plan", "/build"):
            if root == "/plan" and self.agent_mode != "Plan": self.action_toggle_plan_build()
            elif root == "/build" and self.agent_mode != "Build": self.action_toggle_plan_build()
            self.notify(f"Mode set to [bold]{self.agent_mode}[/bold].")
        elif root in ("/clear", "/reset"):
            self.history.clear(); self.stats_turns = 0
            self.update_stats_ui(0, 0.0, 0.0)
            for child in list(self.chat_area.children): child.remove()
            self.notify("Session history and chat window cleared.")
        elif root == "/tok":
            est = sum(len(m.get("content", "")) // 4 for m in self.history)
            self.notify(f"History: ~{est:,} tokens ({len(self.history)} messages)")
        elif root in ("/sync", "/re"):
            self.notify("Triggered background AST codebase sync.")
            try: subprocess.Popen(["index-map", self.workspace_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception: pass
        elif root in ("/skill", "/s"):
            if args and skills:
                content = skills.load_skill_content(args, SKILLS_DIR, CFG_DIR)
                if content:
                    s_name, s_text = content if isinstance(content, tuple) else (args, content)
                    self.set_skill(s_name)
                    self.history.append({"role": "system", "content": f"[SKILL BLUEPRINT: {s_name}]\n{s_text}"})
                    self.notify(f"Loaded skill blueprint: [bold]{s_name}[/bold]")
                else: self.notify(f"No skill blueprint file found for '[bold]{args}[/bold]'.")
            else: self.notify("Usage: /skill <query> or /s <query>")
        elif root in ("/compact", "/c"): self.action_toggle_compact()
        elif root in ("/t", "/thinking"): self.action_toggle_reasoning()
        elif root in ("/f", "/tk", "/b", "/a"): await self.handle_meta_chat_command(root, args)
        else: self.notify(f"Unknown command '{root}'. Type [bold]/help[/bold] for commands.")

    def prompt_tui_confirm(self, prompt_text: str) -> bool:
        self.gate_auth_event.clear()
        self.gate_auth_result = False
        def _show():
            self.entering_gate_authorization, self.current_gate_prompt = True, prompt_text
            self.chat_input.disabled, self.chat_input.value = False, ""
            self.chat_input.placeholder = f"  ▲ Authorize: {prompt_text}? [Y/n]: "
            self.chat_input.focus()
        self.call_from_thread(_show)
        self.gate_auth_event.wait()
        return self.gate_auth_result

    def process_query_worker(self, query: str) -> None:
        try: self.call_from_thread(self.query_one("#welcome-banner").remove)
        except Exception: pass
        for notice in self.chat_area.query(".sys-notice, .theme-notice"):
            try: self.call_from_thread(notice.remove)
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
                            self.call_from_thread(self.notify, "Memory injected.")
                        else: self.call_from_thread(self.notify, "Memory recall skipped.")
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
                self.set_image("None")
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

                        self.call_from_thread(self.notify, f"∗ {verb} • [bold cyan]{fname}[/bold cyan] [italic]{brief}[/italic]")
                        try:
                            old_g = os.environ.get("AI_CONFIRM_GATES")
                            os.environ["AI_CONFIRM_GATES"] = "0"
                            result = core._run_edit_tool(fname, args, self.workspace_path)
                            if old_g: os.environ["AI_CONFIRM_GATES"] = old_g
                            if "[denied]" in result: user_aborted = True
                        except Exception as te: result = f"[tool error] {te}"

                    self.history.append({"role": "tool", "tool_call_id": tc.get("id", ""), "name": fname, "content": result})

                if user_aborted:
                    self.call_from_thread(self.notify, "Execution halted by user gate.")
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
                    sess_bin = os.path.join(CFG_DIR, "modules", "ai-agent-sessions")
                    if os.path.exists(sess_bin):
                        subprocess.Popen([sys.executable, sess_bin, "log-turn", self.safe_name, query, accumulated], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self.refresh_db_counts()
                        self.call_from_thread(self.query_one("#lbl-database", Static).update, f"[dim]DB State[/dim]  {self.get_db_status_string()}")
                except Exception: pass

        except Exception as e:
            if self.generation_cancelled: self.call_from_thread(assistant_msg.update_content, (accumulated or "") + " (stopped)")
            else: self.call_from_thread(assistant_msg.update_content, f"Error: {e}")
        finally:
            self.active_response = None
            if old_confirm: ui.confirm_tool = old_confirm
            self.call_from_thread(self.enable_input)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = CSI_U_REGEX.sub('', event.value.strip()).strip()
        self.chat_input.value = ""

        if getattr(self, "entering_gate_authorization", False):
            self.entering_gate_authorization = False
            self.chat_input.placeholder = "  Ask your agent anything..."
            is_yes = query.lower() in ("y", "yes", "")
            self.gate_auth_result = is_yes
            self.gate_auth_event.set()
            color, status = ("green", "Authorized") if is_yes else ("red", "Denied")
            self.notify(f"Gate: [bold {color}]{status}[/bold {color}]")
            return

        if self.entering_reasoning_budget:
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "   Ask your agent anything..."
            if not query:
                self.reasoning_budget, self.reasoning_active = 500, True
                self.set_reasoning("500 tokens")
                self.notify("Deep reasoning enabled (default 500 tokens).")
            else:
                try:
                    val = int(query)
                    if val > 0:
                        self.reasoning_budget, self.reasoning_active = val, True
                        self.set_reasoning(f"{val} tokens")
                        self.notify(f"Deep reasoning enabled ({val} tokens).")
                    else: raise ValueError
                except ValueError:
                    self.reasoning_active = False
                    self.set_reasoning("Disabled")
                    self.notify("[bold red]Invalid budget. Deep reasoning disabled.[/bold red]", sys_prefix=False)
            return

        if self.entering_image_url:
            self.entering_image_url = False
            self.chat_input.placeholder = "   Ask your agent anything..."
            if query:
                self.active_image_url = query
                fname = query.split("/")[-1].split("?")[0][:25]
                self.set_image(fname or 'attached')
                self.notify(f"Attached image URL: [bold]{query}[/bold]")
            else: self.notify("Image attachment cancelled.")
            return

        if not query: return

        if query.startswith("/"): await self.handle_slash_command(query); return

        if self.pending_skill_prefix:
            query, self.pending_skill_prefix = f"{self.pending_skill_prefix} {query}", None
            self.chat_input.placeholder = "   Ask your agent anything..."

        if query.lower() in ("exit", "quit", "q"): self.exit(); return
        if query.lower().startswith("file "):
            parts = query.split(maxsplit=1)
            if len(parts) > 1: await self.handle_view_file(parts[1].strip())
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
            self.notify("(Generation stopped by user.)", sys_prefix=False)

    def action_attach_image_url(self) -> None:
        if self.entering_image_url:
            self.entering_image_url = False
            self.chat_input.placeholder = "   Ask your agent anything..."
        else:
            self.entering_image_url, self.entering_reasoning_budget = True, False
            self.chat_input.placeholder = "  Enter Web Image URL (http://... or https://...):"
            self.chat_input.focus()

    def update_sidebar_visibility(self) -> None:
        try: self.query_one("#sidebar", Vertical).display = not self.sidebar_hidden
        except Exception: pass

    def action_toggle_sidebar(self) -> None:
        self.sidebar_hidden = not self.sidebar_hidden
        save_tui_state("sidebar_hidden", self.sidebar_hidden)
        self.update_sidebar_visibility()

    def update_footer_visibility(self) -> None:
        try:
            self.query_one("#footer-bar", Horizontal).display = not self.footer_hidden
            toggle_btn = self.query_one("#input-toggle", FooterToggle)
            toggle_btn.update("▲ Show" if self.footer_hidden else "▼ Hide")
        except Exception: pass

    def action_toggle_footer(self) -> None:
        self.footer_hidden = not self.footer_hidden
        save_tui_state("footer_hidden", self.footer_hidden)
        self.update_footer_visibility()

    def action_toggle_compact(self) -> None:
        self.compact_mode = not self.compact_mode
        save_tui_state("compact_mode", self.compact_mode)
        for child in self.chat_area.children:
            if isinstance(child, Message): child.refresh(layout=True)
        self.chat_area.refresh(layout=True)
        self.notify(f"Compact mode {'enabled' if self.compact_mode else 'disabled'}.")

    def action_cycle_theme(self) -> None:
        try:
            current_idx = self.THEMES.index(self.theme) if self.theme in self.THEMES else 0
            self.theme = self.THEMES[(current_idx + 1) % len(self.THEMES)]
            global ACTIVE_THEME
            ACTIVE_THEME = self.theme
            save_tui_state("tui_theme", self.theme)
            self.update_welcome_banner()
            self.set_skill(self.active_skill)
            for child in self.chat_area.children:
                if isinstance(child, Message): child.refresh(layout=True)
            self.chat_area.refresh(layout=True)
            self.notify(f"Theme: {self.theme}", sys_prefix=False, css_class="theme-notice")
        except Exception: pass

    def action_toggle_reasoning(self) -> None:
        if self.entering_reasoning_budget:
            self.entering_reasoning_budget = False
            self.chat_input.placeholder = "   Ask your agent anything..."
        elif self.reasoning_active:
            self.reasoning_active = False
            self.set_reasoning("Disabled")
            self.notify("Deep reasoning disabled.")
        else:
            self.entering_reasoning_budget, self.entering_image_url = True, False
            self.chat_input.placeholder = "  Enter Reasoning Budget (Press Enter for default 500):"
            self.chat_input.focus()

if __name__ == "__main__":
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    try:
        configs = agent_cloud.get_active_configs([]) if agent_cloud else []
        model = configs[0][2].get("model", "local-model") if configs else ui.get_local_model_name()
    except Exception: model = ui.get_local_model_name()
            
    app = LocalAITUI(workspace, model)
    try: app.run()
    finally:
        try:
            subprocess.run(["stty", "sane"], check=False)
            sys.stdout.write("\033[0m\033[?25h")
            sys.stdout.flush()
        except Exception: pass
