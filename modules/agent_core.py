#!/usr/bin/env python3
"""Core Module - Handles streaming SSE, tool gates, and Rich rendering"""

import os, sys, json, ast, re, shutil, subprocess, difflib, urllib.parse, urllib.request as urlreq
from typing import List, Dict, Any, Optional, Tuple

import requests
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from rich.syntax import Syntax

import agent_ui as ui
import agent_cloud

CFG_DIR: str = os.path.expanduser("~/.config/local-ai")
STATE_FILE: str = os.path.join(CFG_DIR, ".state.json")

_console, _console_err, _session = Console(), Console(stderr=True), requests.Session()

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')
RE_THINKING_TITLE = re.compile(r'^\s*Thinking Process:\s*', re.IGNORECASE)
RE_FINAL_ANSWER = re.compile(r'^\s*Final Answer:\s*', re.IGNORECASE)
RE_MULTIPLE_NEWLINES = re.compile(r'\n{2,}')
RE_JSON_OBJECT = re.compile(r"\{[\s\S]*\}")
RE_ABS_PATH = re.compile(r'/(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]*')

_MD_COMPACT_RULES = (
    (re.compile(r'\*\*(.*?)\*\*'), r'[bold]\1[/bold]'),
    (re.compile(r'\*(.*?)\*'), r'[italic]\1[/italic]'),
    (re.compile(r'`(.*?)`'), r'[cyan]\1[/cyan]'),
    (re.compile(r'^(\s*\d+\.)'), r'[bold green]\1[/bold green]'),
    (re.compile(r'^(\s*)[-•*]'), r'\1[bold cyan]•[/bold cyan]'),
)

BINARY_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".bin", ".pyc", ".so", ".dll", ".exe", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".tar", ".gz", ".7z", ".pdf", ".docx", ".xlsx", ".db-wal", ".db-shm"}

_TPM_SKIP_QUERIES = frozenset({"hello", "hi", "hey", "exit", "quit", "q", "/clear", "/reset", "/stats", "/tok", "/m", "/r"})
_TPM_BLACKLIST = frozenset({"files", "file", "file_list", "project", "code", "description", "features", "dependencies", "project_type", "directory", "folder", "workspace"})

EDIT_TOOLS: List[Dict[str, Any]] = [
    {"type": "function", "function": {"name": n, "description": d, "parameters": {"type": "object", "properties": p, "required": r}}}
    for n, d, p, r in [
        ("read_symbol", "Extract the precise source code snippet for a function or class symbol from the index graph without reading the whole file.", {"symbol": {"type": "string"}}, ["symbol"]),
        ("read_file", "Read a text file from the project.", {"path": {"type": "string"}}, ["path"]),
        ("write_file", "Create or overwrite a file in the project.", {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
        ("list_dir", "List directory contents in the project.", {"path": {"type": "string"}}, []),
        ("run_command", "Run a shell command in project root.", {"command": {"type": "string"}}, ["command"]),
    ]
]
TOOL_VERBS = {"read_symbol": "tracing symbol", "read_file": "checking", "write_file": "updating", "list_dir": "checking", "run_command": "executing"}

DEFAULTS = {
    "spell_active": True, "show_stats": True, "memory_active": True, "box_style": 2, "yolo_mode": False,
    "show_thinking": True, "reasoning_active": False, "reasoning_budget": 500, "render_markdown": True,
    "compact_mode": 0, "sidebar_hidden": False, "footer_hidden": True, "tips_card_hidden": False, "tui_theme": "code",
    "voice_auto_submit": True, "tts_enabled": False
}

try: import agent_usage as usage_log
except ImportError: usage_log = None

try: import speed_test
except ImportError: speed_test = None


def get_state(key: str = "", default: Any = None) -> Any:
    st = dict(DEFAULTS)
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f: st.update(json.load(f))
        except (OSError, json.JSONDecodeError): pass
    return st.get(key, default) if key else st


def save_state(key: str, value: Any) -> None:
    st = get_state()
    st[key] = value
    tmp = f"{STATE_FILE}.tmp"
    try:
        os.makedirs(CFG_DIR, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f: json.dump(st, f, indent=2)
        os.replace(tmp, STATE_FILE)
    except OSError:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except OSError: pass


def workspace_safe_name(workspace_path: str, home_dir: str = "") -> str:
    home, ws = os.path.realpath(home_dir or os.path.expanduser("~")), os.path.realpath(workspace_path)
    return "home" if ws == home else (ws.replace("/", "-").strip("-.") or "home")


def run_mod(module_name: str, *args: str, input_data: Optional[str] = None) -> str:
    for sub in ("modules", ""):
        path = os.path.join(CFG_DIR, sub, module_name)
        if os.path.exists(path):
            try:
                res = subprocess.run([sys.executable, path, *args], input=input_data, capture_output=True, text=True, timeout=15)
                return res.stdout.strip() if res.returncode == 0 else ""
            except (OSError, subprocess.SubprocessError, TimeoutError): return ""
    return ""


def background_tpm_update(user_msg: str, assistant_msg: str, workspace: str, workspace_path: str) -> None:
    clean = user_msg.lower().strip()
    if len(clean) < 8 or clean in _TPM_SKIP_QUERIES: return
    try:
        ex_facts = run_mod("ai-agent-memories", "tpm-get", workspace)
        sys_p = "You are an async memory compiler. Extract ONLY persistent facts, roles, or preferences about the HUMAN USER (e.g. {\"user_role\": \"python dev\", \"preferred_style\": \"concise\"}). Do NOT extract project code descriptions, file listings, or software features. Output ONLY a flat JSON object or {} if no user facts exist."
        payload = {"messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": f"### Profile:\n{ex_facts or 'None'}\n\n### Turn:\nUser: {user_msg}\nAssistant: {assistant_msg}\n\nJSON:"}], "stream": False}
        req = urlreq.Request("http://localhost:8080/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urlreq.urlopen(req, timeout=10) as resp:
            out = json.loads(resp.read().decode())["choices"][0]["message"].get("content", "")
        if m := RE_JSON_OBJECT.search(out):
            if parsed := {str(k).strip().lower(): str(v).strip() for k, v in json.loads(m.group(0)).items() if k and v is not None and str(k).strip().lower() not in _TPM_BLACKLIST}:
                run_mod("ai-agent-memories", "tpm-reconcile", workspace, input_data=json.dumps(parsed))
                if res := run_mod("ai-agent-memories", "tpm-get", workspace):
                    md_dir = os.path.join(workspace_path, ".agent")
                    os.makedirs(md_dir, exist_ok=True)
                    with open(os.path.join(md_dir, "tpm.md"), "w", encoding="utf-8") as f: f.write(res + "\n")
    except (OSError, urlreq.URLError, TimeoutError, json.JSONDecodeError): pass


def _clear_lines(stream_err: bool, text: str, extra_top: int = 0) -> None:
    cols = shutil.get_terminal_size((80, 24)).columns or 80
    rows = extra_top + sum(max(1, (len(ANSI_ESCAPE.sub('', l.replace('\t', '    '))) + cols - 1) // cols) for l in text.split("\n"))
    up = max(0, rows - 1)
    target = sys.stderr if stream_err else sys.stdout
    try:
        target.write(f"\r\033[{up}A\033[J" if up > 0 else "\r\033[J")
        target.flush()
    except (IOError, OSError): pass


def _render_compact_markdown_think(raw_think: str) -> None:
    clean = RE_THINKING_TITLE.sub('', raw_think).strip()
    if clean:
        try: _console_err.print(Markdown(clean, code_theme="ansi_dark"))
        except (ValueError, KeyError, TypeError, OSError): _console_err.print(clean)


class RichStreamer:
    def __init__(self, prefix: str = "", active: bool = True, spinner: Any = None) -> None:
        self.prefix, self.active, self.spinner = prefix, active and sys.stdout.isatty(), spinner
        self.acc_think, self.acc_ans, self.phase, self.think_hdr_printed, self.ans_started = "", "", "INIT", False, False

    def _stop_spinner(self, done_msg: Optional[str] = None) -> None:
        if self.spinner:
            try: self.spinner.stop(done_msg=done_msg)
            except (AttributeError, RuntimeError, OSError): pass

    def start(self) -> None:
        if self.active:
            try: sys.stdout.write("\033[?25h"); sys.stdout.flush()
            except (IOError, OSError): pass

    def update(self, token: str) -> None:
        if not self.active:
            if "<think>" in token and self.phase != "THINKING": self.phase, token = "THINKING", token.replace("<think>", "")
            if "</think>" in token: self.phase, token = "ANSWER", token.split("</think>", 1)[1] if "</think>" in token else ""
            if self.phase != "THINKING" and token:
                try: sys.stdout.write(token); sys.stdout.flush()
                except (IOError, OSError): pass
            return

        show_think, render_md = os.environ.get("AI_SHOW_THINKING", "1") == "1", os.environ.get("AI_RENDER_MARKDOWN", "1") == "1"

        if "<think>" in token and self.phase != "THINKING":
            self.phase, token = "THINKING", token.replace("<think>", "")
            if self.spinner: self.spinner.update("Thinking...")

        if "</think>" in token:
            parts = token.split("</think>", 1)
            if parts[0]: self.update(parts[0])
            if show_think and self.think_hdr_printed:
                sep = "" if self.acc_think.endswith("\n") else "\n"
                _console_err.print(f"{sep}[dim]╰────────────────────────────────────────────────────────[/dim]")
                sys.stderr.flush()
            self.phase = "ANSWER"
            if len(parts) > 1 and parts[1]: self.update(parts[1])
            return

        if self.phase == "THINKING":
            tok = RE_MULTIPLE_NEWLINES.sub('\n', RE_THINKING_TITLE.sub('', token.replace("\\n", "\n")))
            if self.acc_think.endswith("\n") and tok.startswith("\n"): tok = tok.lstrip("\r\n")
            self.acc_think += tok
            if show_think and tok:
                if not self.think_hdr_printed and tok.strip():
                    self.think_hdr_printed = True
                    self._stop_spinner()
                    _console_err.print("[dim]╭─ ⚙ ────────────────────────────────────────────────────[/dim]")
                    tok = tok.lstrip("\r\n")
                if tok:
                    try: sys.stderr.write(tok); sys.stderr.flush()
                    except (IOError, OSError): pass
        else:
            if not self.ans_started:
                self._stop_spinner()
                self.ans_started, p_clean = True, self.prefix.strip()
                p_str = f"{p_clean} " if p_clean else ""
                p_style = "\033[1;32m" if "Agent" in p_clean else "\033[1;36m"
                if p_str:
                    try: sys.stdout.write(f"{p_style}{p_str}\033[0m"); sys.stdout.flush()
                    except (IOError, OSError): pass
                self.acc_ans += p_str

            tok = RE_FINAL_ANSWER.sub('', token.replace("\\n", "\n"))
            self.acc_ans += tok
            if tok:
                try: sys.stdout.write(tok); sys.stdout.flush()
                except (IOError, OSError): pass

    def stop(self, interrupted: bool = False) -> None:
        self._stop_spinner()
        if interrupted:
            try: sys.stdout.write("\033[?25h\n"); sys.stdout.flush()
            except (IOError, OSError): pass
            return

        show_think, render_md = os.environ.get("AI_SHOW_THINKING", "1") == "1", os.environ.get("AI_RENDER_MARKDOWN", "1") == "1"

        if self.phase == "THINKING" and show_think and self.think_hdr_printed:
            sep = "" if self.acc_think.endswith("\n") else "\n"
            _console_err.print(f"{sep}[dim]╰────────────────────────────────────────────────────────[/dim]")
            self.phase = "ANSWER"

        if self.ans_started and self.acc_ans.strip():
            try: sys.stdout.write("\n"); sys.stdout.flush()
            except (IOError, OSError): pass


def _log_turn_usage(model: str, in_tok: int, out_tok: int, cost: float, show_stats: bool, ctx_used: Optional[int] = None) -> None:
    if not usage_log: return
    try:
        usage_log.record(model, in_tok, out_tok, cost)
        usage_log.refresh_balance_async(min_age=10)
        if show_stats and sys.stdout.isatty():
            ctx_max = int(os.environ.get("AI_MAX_TOKENS", 8192)) if ctx_used is not None else None
            print(usage_log.turn_line(in_tok, out_tok, cost, ctx_used, ctx_max))
    except (OSError, TypeError, ValueError, KeyError): pass


def _process_stream_chunk(content: str, reasoning: str, in_think_block: bool) -> Tuple[str, bool, bool]:
    if content:
        if "Final Answer:" in content: content = RE_FINAL_ANSWER.sub('', content).lstrip()
        if "<|tool_call" in content:
            content = re.sub(r'<\|tool_call_start\|>.*?<\|tool_call_end\|>', '', content, flags=re.DOTALL)
            content = content.replace("<|tool_call_start|>", "").replace("<|tool_call_end|>", "")
    if reasoning: return (f"<think>{reasoning}", True, True) if not in_think_block else (reasoning, True, True)
    if content:
        if in_think_block and "</think>" not in content: return f"</think>{content}", False, False
        in_think = True if "<think>" in content else (False if "</think>" in content else in_think_block)
        return content, in_think, in_think
    return "", False, in_think_block


def _calc_turn_tokens(ans_text: str, messages: List[Dict[str, Any]], captured_usage: Optional[Dict[str, Any]], is_local: bool) -> Tuple[int, int]:
    if captured_usage and "completion_tokens" in captured_usage:
        return captured_usage.get("prompt_tokens", 0), captured_usage.get("completion_tokens", 0)
    if is_local:
        return sum(get_accurate_token_count(m.get("content") or "") for m in messages), get_accurate_token_count(ans_text)
    return sum(len(str(m.get("content") or "")) for m in messages) // 4, len(ans_text) // 4


def _safe_path(workspace: str, p: str) -> str:
    if not p: return os.path.realpath(workspace)
    p = os.path.expanduser(urllib.parse.unquote(str(p).strip()))
    return os.path.realpath(p if os.path.isabs(p) else os.path.join(workspace, p))


def _is_outside_workspace(workspace: str, full_path: str) -> bool:
    root = os.path.realpath(workspace)
    return full_path != root and not full_path.startswith(root + os.sep)


def _confirm_gate(reason: str, spinner: Any) -> bool:
    if spinner: spinner.stop()
    return sys.stdout.isatty() and ui.confirm_tool(reason)


def _print_tool_output(spinner: Any, text: str) -> None:
    if sys.stdout.isatty() and text.strip():
        if spinner: spinner.stop("Done")
        if os.environ.get("AI_RENDER_MARKDOWN", "1") == "1" and any(k in text for k in ("#", "|", "```")):
            _console_err.print(Markdown(text, code_theme="ansi_dark"))
        else: _console_err.print(text)


def _run_edit_tool(name: str, args: Dict[str, Any], workspace: str, spinner: Any = None) -> str:
    gates_active = os.environ.get("AI_CONFIRM_GATES", "1") == "1"
    denial = "[denied] User declined tool execution."
    raw_path = args.get("path", "")
    full = _safe_path(workspace, raw_path) if raw_path else ""

    if name == "exec_python":
        try:
            import agent_ipython as ipython
            out = ipython.run_cell(args.get("code", ""), workspace, lambda r: _confirm_gate(r, spinner))
            _print_tool_output(spinner, out)
            return out
        except Exception as e: return f"[error] Python kernel execution failed: {e}"

    if name == "read_symbol":
        sym = args.get("symbol", "").strip()
        try:
            mod_path = os.path.join(CFG_DIR, "tools", "map", "index-map")
            res = subprocess.run([sys.executable, mod_path, "snippet", sym], cwd=workspace, capture_output=True, text=True, timeout=10)
            out = (res.stdout or res.stderr or "").strip()
            _print_tool_output(spinner, out)
            return out or f"[error] Symbol '{sym}' not found in index graph."
        except (OSError, subprocess.SubprocessError, TimeoutError) as e: return f"[error] failed to extract symbol: {e}"

    if name == "read_file":
        if os.path.splitext(full)[1].lower() in BINARY_EXTENSIONS or os.path.isdir(full):
            return f"[error] Refused to read binary file or directory '{raw_path}'."
        if _is_outside_workspace(workspace, full) and not _confirm_gate(f"OUT-OF-BOUNDS READ: {full}", spinner): return denial
        if gates_active and not _confirm_gate(f"read file {raw_path}", spinner): return denial
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f: content = f.read(60000)
            _print_tool_output(spinner, content)
            return content
        except OSError as e: return f"[error] failed to read file: {e}"

    if name == "write_file":
        content = args.get("content", "")
        if full.endswith(".py"):
            try: ast.parse(content)
            except SyntaxError as e: return f"[error] Write blocked. Python syntax error: {e} on line {getattr(e, 'lineno', '?')}."
        if full.endswith(".json"):
            try: json.loads(content)
            except (json.JSONDecodeError, TypeError, ValueError) as e: return f"[error] Write blocked. JSON syntax error: {e}."

        if sys.stdout.isatty() and os.path.exists(full):
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f: old = f.read()
                if diff := "\n".join(difflib.unified_diff(old.splitlines(), content.splitlines(), fromfile=f"a/{raw_path}", tofile=f"b/{raw_path}", lineterm="")):
                    _console_err.print("\n", Syntax(diff, "diff", theme="ansi_dark", background_color="default"), "\n")
            except OSError: pass

        if _is_outside_workspace(workspace, full) and not _confirm_gate(f"OUT-OF-BOUNDS WRITE: {full}", spinner): return denial
        if gates_active and not _confirm_gate(f"{'overwrite' if os.path.exists(full) else 'create'} {raw_path}", spinner): return denial

        try:
            os.makedirs(os.path.dirname(full) or workspace, exist_ok=True)
            with open(full, "w", encoding="utf-8") as f: f.write(content)
            return f"wrote {len(content)} chars to {raw_path}"
        except OSError as e: return f"[error] failed to write file: {e}"

    if name == "list_dir":
        if _is_outside_workspace(workspace, full) and not _confirm_gate(f"OUT-OF-BOUNDS LIST DIR: {full}", spinner): return denial
        if gates_active and not _confirm_gate(f"list directory {raw_path or '.'}", spinner): return denial
        try:
            entries = sorted(os.listdir(full))
            res_str = "\n".join((e + "/" if os.path.isdir(os.path.join(full, e)) else e) for e in entries) or "(empty)"
            if sys.stdout.isatty():
                if spinner: spinner.stop()
                _console_err.print(f"[dim]{res_str}[/dim]")
            return res_str
        except OSError as e: return f"[error] failed to list files: {e}"

    if name == "run_command":
        cmd = args.get("command", "")
        expanded = cmd.replace("~", os.path.expanduser("~"))
        abs_paths = RE_ABS_PATH.findall(expanded)
        sys_prefixes = ("/bin/", "/usr/bin/", "/usr/local/bin/", "/sbin/", "/usr/sbin/")
        target_paths = [p for p in abs_paths if not any(p.startswith(sp) for sp in sys_prefixes)]
        if (".." in cmd or any(_is_outside_workspace(workspace, p) for p in target_paths if os.path.exists(p) or os.path.isabs(p))) and not _confirm_gate(f"OUT-OF-BOUNDS EXECUTION: $ {cmd}", spinner):
            return denial

        if gates_active:
            if not sys.stdout.isatty(): return "[denied] no terminal available to approve command execution"
            if not _confirm_gate(f"execute: $ {cmd}", spinner): return denial
        else:
            _console_err.print(f"[dim]  Executing command autonomously: $ {cmd}[/dim]")

        shell = os.environ.get("SHELL") or "/bin/sh"
        if spinner:
            try: spinner.update("Working...")
            except (AttributeError, RuntimeError): pass
            spinner.start("Working...")
        try:
            res = subprocess.run([shell, "-lc", cmd], cwd=workspace, capture_output=True, text=True, timeout=300)
            out = ((res.stdout or "") + (("\n" + res.stderr) if res.stderr else "")).strip()[:10000]
            _print_tool_output(spinner, out)
            return f"(exit {res.returncode})\n{out}" if res.returncode != 0 else (out or "(exit 0, no output)")
        except subprocess.TimeoutExpired: return "[error] command timed out after 300 seconds"
        except OSError as e: return f"[error] failed to run command: {e}"
        finally:
            if spinner: spinner.stop()

    return f"[error] unknown tool {name}"


def agentic_turn(messages: List[Dict[str, Any]], url: str, headers: Dict[str, str], body: Dict[str, Any], timeout: int, spinner: Any, show_stats: bool = False, is_agent: bool = False) -> Optional[str]:
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    is_local = "localhost" in url or "127.0.0.1" in url or body.get("model") == "local-model"

    if is_agent and messages and messages[0]["role"] == "system" and "### EDIT MODE" not in messages[0]["content"]:
        tools_header = f"### EDIT MODE:\nYou are an active coding agent at {workspace}.\n\n### WORKING TOOLS:\nCapabilities: read_symbol, read_file, write_file, list_dir, run_command. Root: {workspace}.\n\n"
        messages[0]["content"] = tools_header + messages[0]["content"]

    resolved_model, streamer, res = None, None, None

    try: import agent_ipython as ipython
    except ImportError: ipython = None

    for _round in range(10):
        body_tools = {**body, "messages": messages, "stream": True}
        if is_agent:
            body_tools["tools"] = ipython.get_active_tools() if ipython else EDIT_TOOLS

        if spinner:
            try: spinner.update("Working...")
            except (AttributeError, RuntimeError): pass
            spinner.start("Working...")
        try:
            res = _session.post(url, json=body_tools, headers={"Content-Type": "application/json", **headers}, timeout=timeout, stream=True)
            first_chunk, acc_content, tool_calls_map, in_think_block, captured_usage = True, [], {}, False, None

            for line in res.iter_lines():
                if not line: continue
                line_str = line.decode("utf-8", errors="ignore").strip()
                if not line_str.startswith("data:"): continue
                data_str = line_str[5:].strip()
                if data_str == "[DONE]": break

                try:
                    data = json.loads(data_str)
                    captured_usage = data.get("usage") or captured_usage
                    resolved_model = data.get("model") or resolved_model
                    choices = data.get("choices", [{}])
                    if not choices: continue
                    delta = choices[0].get("delta", {})

                    content, reasoning = delta.get("content", "") or "", delta.get("reasoning_content", "") or delta.get("thinking", "") or ""

                    if spinner:
                        try: spinner.update("Thinking..." if reasoning else "Working...")
                        except (AttributeError, RuntimeError): pass

                    chunk_to_stream, is_thinking, in_think_block = _process_stream_chunk(content, reasoning, in_think_block)

                    if chunk_to_stream:
                        if first_chunk:
                            first_chunk = False
                            if os.environ.get("AI_SHOW_THINKING", "1") == "1": spinner.stop()
                            streamer = RichStreamer(prefix="Agent:" if is_agent else "AI:", spinner=spinner)
                            streamer.start()
                            if speed_test and show_stats: speed_test.start()

                        if streamer: streamer.update(chunk_to_stream)
                        acc_content.append(chunk_to_stream)
                        if speed_test and show_stats: speed_test.count_token(chunk_to_stream, is_thinking=is_thinking)

                    for tc in delta.get("tool_calls", []):
                        idx = tc.get("index", 0)
                        tc_entry = tool_calls_map.setdefault(idx, {"id": tc.get("id", ""), "type": "function", "function": {"name": tc.get("function", {}).get("name", ""), "arguments": ""}})
                        if tc.get("function", {}).get("name"): tc_entry["function"]["name"] = tc["function"]["name"]
                        tc_entry["function"]["arguments"] += tc.get("function", {}).get("arguments", "")
                except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError): pass

            if streamer: streamer.stop()
            elif not first_chunk: print("")

            ans_text = "".join(acc_content)
            in_tok, out_tok = _calc_turn_tokens(ans_text, messages, captured_usage, is_local)

            if speed_test and show_stats and not first_chunk:
                speed_test.end(actual_out_tokens=out_tok, is_local=is_local)

            calls = [val for _, val in sorted(tool_calls_map.items())] if tool_calls_map else None
            if not calls or not is_agent:
                tool_toks = sum(get_accurate_token_count(m.get("content") or "") for m in messages if m.get("role") in ("assistant", "tool"))
                final_out = max(out_tok, tool_toks)
                if spinner: spinner.stop("Done" if ans_text and ans_text.strip() else None)
                _log_turn_usage(resolved_model or body.get("model") or "local-model", in_tok, final_out, 0.0, show_stats, in_tok + final_out)
                return ans_text

            messages.append({"role": "assistant", "content": ans_text or None, "tool_calls": calls})

            for tc in calls:
                fname = tc.get("function", {}).get("name", "")
                try:
                    raw_args = tc.get("function", {}).get("arguments") or ""
                    args = json.loads(raw_args) if raw_args else {}
                except (json.JSONDecodeError, TypeError, ValueError): args = {}
                brief = str(args.get("symbol") or args.get("path") or args.get("command") or "")[:100]
                verb = TOOL_VERBS.get(fname, "working")

                _console_err.print(f"[dim]∗ {verb} • [cyan]{fname}[/cyan] [italic]{brief}[/italic][/dim]")
                if spinner:
                    try: spinner.update("Working...")
                    except (AttributeError, RuntimeError): pass
                    spinner.start("Working...")

                try: result = _run_edit_tool(fname, args, workspace, spinner)
                except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError) as e: result = f"[tool error] {e}"
                finally:
                    if spinner: spinner.stop(done_msg="Done")

                pruned_result = result if len(result) <= 1500 else result[:1200] + f"\n... [Reasonix Harness: Snipped {len(result) - 1200} chars for context stability]"
                messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "name": fname, "content": pruned_result})

        except KeyboardInterrupt:
            if streamer:
                try: streamer.stop(interrupted=True)
                except (AttributeError, RuntimeError, OSError): pass
            if spinner:
                try: spinner.stop()
                except (AttributeError, RuntimeError, OSError): pass
            raise
        except (requests.RequestException, OSError, TimeoutError, ValueError, TypeError) as e:
            sys.stderr.write(f"\033[90m[sys] API response error: {e}\033[0m\n")
            return None
        finally:
            if res is not None:
                try: res.close()
                except Exception: pass
            if spinner: spinner.stop()

    return None


def _is_local_server_alive(url: str, timeout: float = 0.3) -> bool:
    if "localhost" not in url and "127.0.0.1" not in url: return True
    try:
        req = urlreq.Request("http://localhost:8080/v1/models", method="GET")
        with urlreq.urlopen(req, timeout=timeout) as r: return r.status == 200
    except (OSError, urlreq.URLError, TimeoutError): return False


def stream_response(messages: List[Dict[str, Any]], prefix: str = "AI: ", cfg_dir: str = "", show_stats: bool = False, thinking_budget: int = 0, is_agent: bool = False) -> Optional[str]:
    spinner = ui.InlineSpinner()
    try:
        configs = [c for c in agent_cloud.get_active_configs(messages) if _is_local_server_alive(c[0])]
        enable_think = thinking_budget > 0
        budget_val = thinking_budget if enable_think else 0
        think_kwargs = {"thinking_budget_tokens": budget_val, "reasoning_budget": budget_val, "chat_template_kwargs": {"enable_thinking": enable_think}}

        local_body = {"messages": messages, "stream": True, **think_kwargs}
        seen_urls, unique_configs = set(), []

        for url, headers, body, timeout in configs:
            norm_url = "http://localhost:8080/v1/chat/completions" if ":8080" in url else url.replace("127.0.0.1", "localhost")
            if "localhost" in norm_url: body.update(think_kwargs)
            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                unique_configs.append(("http://localhost:8080/v1/chat/completions" if ":8080" in url else url, headers, body, timeout))

        if "http://localhost:8080/v1/chat/completions" not in seen_urls:
            unique_configs.append(("http://localhost:8080/v1/chat/completions", {}, local_body, 180))

        for url, headers, body, timeout in unique_configs:
            if (ans := agentic_turn(messages, url, headers, body, timeout, spinner, show_stats, is_agent=is_agent)) is not None:
                if spinner: spinner.stop("Done")
                return ans
        if spinner: spinner.stop("Done")
        return None
    except KeyboardInterrupt:
        if spinner:
            try: spinner.stop()
            except (AttributeError, RuntimeError, OSError): pass
        sys.stderr.write("\r\x1b[2K\033[90m[sys] Interrupted.\033[0m\033[0m\n")
        return None


def get_accurate_token_count(text: Any, server_url: str = "http://localhost:8080") -> int:
    return max(1, (len(text if isinstance(text, str) else str(text)) * 10) // 36) if text else 0


def show_memory_status(messages: List[Dict[str, Any]], max_context: int = 8192, server_url: str = "http://localhost:8080") -> None:
    total_toks = sum(get_accurate_token_count(m.get("content") or "", server_url) for m in messages)
    pct = (total_toks / max_context) * 100
    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
    color = "green" if pct < 70 else "yellow" if pct < 90 else "red"

    _console.print(Panel(
        Group(
            Text.assemble(("Context Window: ", "dim"), (f"{total_toks}", f"bold {color}"), (f"/{max_context} tokens ", "dim"), (f"({pct:.1f}%)", f"bold {color}")),
            Text(f"[{bar}]", style=color)
        ),
        title="Memory & Context Status", title_align="left", border_style="bright_black", box=ROUNDED, expand=False
    ))


def prune_history(history: List[Dict[str, Any]], max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
    if len(history) <= 1: return history
    limit = max_tokens or int(os.environ.get("AI_MAX_TOKENS", 8192))
    history = [m for m in history if m.get("role") != "tool"]

    sys_prompt = history[0]
    curr = get_accurate_token_count(sys_prompt.get("content", ""))
    selected = []

    for msg in reversed(history[1:]):
        toks = get_accurate_token_count(msg.get("content", ""))
        if curr + toks > limit and selected: break
        selected.append(msg)
        curr += toks

    return [sys_prompt] + list(reversed(selected))
