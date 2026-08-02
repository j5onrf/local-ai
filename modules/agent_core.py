"""
Local-AI Agent Core Module
Handles streaming SSE payloads, function execution, tool gates, shared state, and Rich rendering.
"""

import os
import sys
import json
import ast
import re
import shutil
import subprocess
import difflib
import urllib.parse
import urllib.request as urlreq
from typing import List, Dict, Any, Optional, Tuple
from contextlib import closing

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

_console = Console()
_console_err = Console(stderr=True)
_session = requests.Session()

# Pre-compiled regular expressions for 0% streaming overhead
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')
RE_THINKING_TITLE = re.compile(r'^\s*Thinking Process:\s*', re.IGNORECASE)
RE_FINAL_ANSWER = re.compile(r'^\s*Final Answer:\s*', re.IGNORECASE)
RE_TRIPLE_NEWLINES = re.compile(r'\n{3,}')

BINARY_EXTENSIONS = {
    ".db", ".sqlite", ".sqlite3", ".bin", ".pyc", ".so", ".dll", 
    ".exe", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".tar", ".gz", 
    ".7z", ".pdf", ".docx", ".xlsx", ".db-wal", ".db-shm"
}
EDIT_TOOLS: List[Dict[str, Any]] = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file from the project.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create or overwrite a file in the project.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "list_dir", "description": "List directory contents in the project.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run a shell command in project root.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
]
TOOL_VERBS = {"read_file": "checking", "write_file": "updating", "list_dir": "checking", "run_command": "executing"}

try:
    import agent_usage as usage_log
except ImportError:
    usage_log = None

try:
    import speed_test
except ImportError:
    speed_test = None


def get_state(key: str = "", default: Any = None) -> Any:
    """Centralized state JSON getter."""
    defs = {
        "spell_active": True, "show_stats": True, "memory_active": True,
        "box_style": 2, "yolo_mode": False, "show_thinking": True,
        "reasoning_active": False, "reasoning_budget": 500, "render_markdown": True,
        "compact_mode": 0, "sidebar_hidden": False, "footer_hidden": True,
        "tips_card_hidden": False, "tui_theme": "code"
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                defs.update(json.load(f))
        except Exception: pass
    return defs.get(key, default) if key else defs


def save_state(key: str, value: Any) -> None:
    """Centralized state JSON setter."""
    st = get_state()
    st[key] = value
    try:
        os.makedirs(CFG_DIR, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2)
    except Exception: pass


def workspace_safe_name(workspace_path: str, home_dir: str = "") -> str:
    """Sanitizes workspace directory path to safe database string key."""
    home = home_dir or os.path.expanduser("~")
    abs_ws, abs_home = os.path.abspath(workspace_path), os.path.abspath(home)
    if abs_ws == abs_home: return "home"
    clean = abs_ws.replace("/", "-").strip("-.")
    return clean or "home"


def run_mod(module_name: str, *args: str, input_data: Optional[str] = None) -> str:
    """Compact subprocess executor for Local-AI modules."""
    mod_path = os.path.join(CFG_DIR, "modules", module_name)
    if not os.path.exists(mod_path):
        mod_path = os.path.join(CFG_DIR, module_name)
    try:
        cmd = [sys.executable, mod_path] + list(args)
        res = subprocess.run(cmd, input=input_data, capture_output=True, text=True, timeout=15)
        return res.stdout.strip() if res.returncode == 0 else ""
    except Exception: return ""


def background_tpm_update(user_msg: str, assistant_msg: str, workspace: str, workspace_path: str) -> None:
    """Streamlined asynchronous background TPM memory compiler."""
    cleaned = user_msg.lower().strip()
    if len(cleaned) < 8 or cleaned in ("hello", "hi", "hey", "exit", "quit", "q", "/clear", "/reset", "/stats", "/tok", "/m", "/r"):
        return
    try:
        ex_facts = run_mod("ai-agent-memories", "tpm-get", workspace)
        sys_p = "You are an async memory compiler. Extract persistent user facts, roles, or preferences. Output ONLY a flat JSON object of key-value pairs (e.g. {\"role\": \"python dev\"}). Output {} if none exist."
        usr_p = f"### Profile:\n{ex_facts or 'None'}\n\n### Turn:\nUser: {user_msg}\nAssistant: {assistant_msg}\n\nJSON:"
        
        payload = {
            "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}],
            "stream": False
        }
        req = urlreq.Request("http://localhost:8080/v1/chat/completions", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urlreq.urlopen(req, timeout=10) as resp:
            out = json.loads(resp.read().decode("utf-8"))["choices"][0]["message"].get("content", "")

        if m := re.search(r"\{[\s\S]*\}", out):
            if parsed := json.loads(m.group(0)):
                clean = {str(k).strip().lower(): str(v).strip() for k, v in parsed.items() if k and v is not None}
                if clean:
                    run_mod("ai-agent-memories", "tpm-reconcile", workspace, input_data=json.dumps(clean))
                    if res := run_mod("ai-agent-memories", "tpm-get", workspace):
                        md_dir = os.path.join(workspace_path, ".agent")
                        os.makedirs(md_dir, exist_ok=True)
                        with open(os.path.join(md_dir, "tpm.md"), "w", encoding="utf-8") as f: f.write(res + "\n")
    except Exception: pass


class RichStreamer:
    """Streams direct text during generation, then renders clean Rich Markdown on completion in a final pass."""

    def __init__(self, prefix: str = "", active: bool = True, spinner: Any = None) -> None:
        self.prefix: str = prefix
        self.active: bool = active and sys.stdout.isatty()
        self.spinner: Any = spinner
        self.accumulated_thinking: str = ""
        self.accumulated_answer: str = ""
        self.phase: str = "INIT"
        self.answer_started: bool = False
        self.thinking_started: bool = False
        self.first_think_token: bool = False

    def _stop_spinner(self) -> None:
        if self.spinner:
            try: self.spinner.stop()
            except Exception: pass

    def _update_spinner(self, msg: str) -> None:
        if self.spinner:
            try: self.spinner.update(msg)
            except Exception: pass

    def start(self) -> None:
        if self.active:
            try:
                sys.stdout.write("\033[?25h")
                sys.stdout.flush()
            except (IOError, OSError): pass

    def update(self, token: str) -> None:
        if not self.active:
            if "<think>" in token and self.phase != "THINKING":
                self.phase = "THINKING"
                token = token.replace("<think>", "")

            if "</think>" in token:
                parts = token.split("</think>", 1)
                self.phase = "ANSWER"
                token = parts[1] if len(parts) > 1 else ""

            if self.phase == "THINKING": return

            if token:
                try:
                    sys.stdout.write(token)
                    sys.stdout.flush()
                except (IOError, OSError): pass
            return

        show_think = os.environ.get("AI_SHOW_THINKING", "1") == "1"

        if "<think>" in token and self.phase != "THINKING":
            self.phase = "THINKING"
            self.first_think_token = True
            self.thinking_started = False
            self._update_spinner("Thinking...")
            token = token.replace("<think>", "")

        if "</think>" in token:
            parts = token.split("</think>", 1)
            thinking_part = parts[0]
            answer_part = parts[1] if len(parts) > 1 else ""

            if thinking_part:
                self.accumulated_thinking += thinking_part
                if show_think and self.phase == "THINKING":
                    try:
                        clean_text = thinking_part.rstrip("\r\n")
                        if clean_text:
                            sys.stderr.write(clean_text + "\n")
                            sys.stderr.flush()
                    except (IOError, OSError): pass

            if show_think and self.phase == "THINKING":
                _console_err.print("[dim]╰────────────────────────────────────────────────────────[/dim]")

            self.phase = "ANSWER"
            self._update_spinner("Working...")

            if answer_part: self.update(answer_part)
            return

        if self.phase == "THINKING":
            if self.first_think_token:
                token = token.lstrip("\r\n")
                if token: self.first_think_token = False

            if token:
                token = RE_THINKING_TITLE.sub('', token.replace("\\n", "\n").replace("\r\n\r\n", "\n").replace("\n\n", "\n"))
                self.accumulated_thinking += token
                if show_think:
                    if not self.thinking_started and token.strip():
                        self.thinking_started = True
                        self._stop_spinner()
                        _console_err.print("[dim]╭─ ⚙ ────────────────────────────────────────────────────[/dim]")
                        token = token.lstrip("\r\n")

                    if token:
                        try:
                            sys.stderr.write(token)
                            sys.stderr.flush()
                        except (IOError, OSError): pass
        else:
            if self.phase != "ANSWER": self.phase = "ANSWER"

            if not self.answer_started:
                self._stop_spinner()
                self.answer_started = True
                p_style = "\033[1;32m" if "Agent" in self.prefix else "\033[1;36m"
                try:
                    sys.stdout.write(f"{p_style}{self.prefix.strip()}\033[0m ")
                    sys.stdout.write("\033[?25h")
                    sys.stdout.flush()
                except (IOError, OSError): pass

            clean_tok = RE_FINAL_ANSWER.sub('', token.replace("\\n", "\n"))
            self.accumulated_answer += clean_tok

            if clean_tok:
                try:
                    sys.stdout.write(clean_tok)
                    sys.stdout.write("\033[?25h")
                    sys.stdout.flush()
                except (IOError, OSError): pass

    def stop(self, interrupted: bool = False) -> None:
        self._stop_spinner()

        if interrupted:
            try:
                sys.stdout.write("\033[?25h\n")
                sys.stdout.flush()
            except Exception: pass
            return

        if self.phase == "THINKING" and self.accumulated_thinking.strip():
            _console_err.print("[dim]╰────────────────────────────────────────────────────────[/dim]")
            self.phase = "ANSWER"

        if not self.answer_started and self.accumulated_answer.strip():
            self.answer_started = True

        if self.answer_started:
            render_md = os.environ.get("AI_RENDER_MARKDOWN", "1") == "1"
            if render_md and self.accumulated_answer.strip() and sys.stdout.isatty():
                try:
                    cols = shutil.get_terminal_size((80, 24)).columns or 80
                    p_clean = self.prefix.strip() if self.prefix else ""
                    clean_ans = RE_FINAL_ANSWER.sub('', RE_TRIPLE_NEWLINES.sub('\n\n', self.accumulated_answer.strip())).strip()

                    full_str = f"{p_clean} {clean_ans}" if p_clean else clean_ans

                    total_rows = sum(max(1, (len(ANSI_ESCAPE.sub('', l)) + cols - 1) // cols) for l in full_str.split("\n"))
                    up_count = max(0, total_rows - 1)

                    if up_count > 0:
                        sys.stdout.write(f"\r\033[{up_count}A\033[J")
                    else:
                        sys.stdout.write("\r\033[2K")
                    sys.stdout.flush()

                    p_col = "bold green" if "Agent" in p_clean else "bold cyan"
                    if p_clean:
                        _console.print(Text(p_clean, style=p_col))
                    _console.print(Markdown(clean_ans, code_theme="ansi_dark"))
                except Exception:
                    try:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                    except Exception: pass
            else:
                try:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                except Exception: pass


def _log_turn_usage(model: str, in_tok: int, out_tok: int, cost: float, show_stats: bool, ctx_used: Optional[int] = None) -> None:
    if not usage_log: return
    try:
        usage_log.record(model, in_tok, out_tok, cost)
        usage_log.refresh_balance_async(min_age=10)
        if show_stats and sys.stdout.isatty():
            ctx_max = int(os.environ.get("AI_MAX_TOKENS", 8192)) if ctx_used is not None else None
            print(usage_log.turn_line(in_tok, out_tok, cost, ctx_used, ctx_max))
    except Exception: pass


def _process_stream_chunk(content: str, reasoning: str, in_think_block: bool) -> Tuple[str, bool, bool]:
    """Reasonix Harness Stream Interceptor: Routes reasoning tokens vs response text."""
    if content and "Final Answer:" in content:
        content = RE_FINAL_ANSWER.sub('', content).lstrip()

    if reasoning:
        return (f"<think>{reasoning}", True, True) if not in_think_block else (reasoning, True, True)
    if content:
        if in_think_block and "</think>" not in content:
            return f"</think>{content}", False, False
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


def _run_edit_tool(name: str, args: Dict[str, Any], workspace: str, spinner: Any = None) -> str:
    gates_active = os.environ.get("AI_CONFIRM_GATES", "1") == "1"
    denial_msg = "[denied] User declined tool execution."

    if name == "read_file":
        raw_path = args.get("path", "")
        full = _safe_path(workspace, raw_path)
        ext = os.path.splitext(full)[1].lower()
        if ext in BINARY_EXTENSIONS or os.path.isdir(full):
            return f"[error] Refused to read binary file or directory '{raw_path}'."

        outside = _is_outside_workspace(workspace, full)
        if (outside or gates_active) and not _confirm_gate(f"read {full}" if outside else f"read file {raw_path}", spinner):
            return denial_msg
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f: content = f.read(60000)
            if sys.stdout.isatty() and content.strip():
                if spinner: spinner.stop()
                _console_err.print()
                if os.environ.get("AI_RENDER_MARKDOWN", "1") == "1" and ("#" in content or "|" in content):
                    _console_err.print(Markdown(content, code_theme="ansi_dark"))
                else: _console_err.print(content)
                _console_err.print()
            return content
        except Exception as e: return f"[error] failed to read file: {e}"

    if name == "write_file":
        raw_path = args.get("path", "")
        full = _safe_path(workspace, raw_path)
        content = args.get("content", "")
        outside = _is_outside_workspace(workspace, full)
        exists = os.path.exists(full)

        if full.endswith(".py"):
            try: ast.parse(content)
            except SyntaxError as e: return f"[error] Write blocked. Python syntax error: {e} on line {getattr(e, 'lineno', '?')}."
        if full.endswith(".json"):
            try: json.loads(content)
            except Exception as e: return f"[error] Write blocked. JSON syntax error: {e}."

        if sys.stdout.isatty() and exists:
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f: old = f.read()
                diff_text = "\n".join(difflib.unified_diff(old.splitlines(), content.splitlines(), fromfile=f"a/{raw_path}", tofile=f"b/{raw_path}", lineterm=""))
                if diff_text:
                    _console_err.print()
                    _console_err.print(Syntax(diff_text, "diff", theme="ansi_dark", background_color="default"))
                    _console_err.print()
            except Exception: pass

        if (outside or gates_active) and not _confirm_gate(f"{'overwrite' if exists else 'create'} {raw_path}", spinner):
            return denial_msg

        try:
            os.makedirs(os.path.dirname(full) or workspace, exist_ok=True)
            with open(full, "w", encoding="utf-8") as f: f.write(content)
            return f"wrote {len(content)} chars to {raw_path}"
        except Exception as e: return f"[error] failed to write file: {e}"

    if name == "list_dir":
        raw_path = args.get("path", "")
        full = _safe_path(workspace, raw_path)
        outside = _is_outside_workspace(workspace, full)
        if (outside or gates_active) and not _confirm_gate(f"list directory {raw_path or '.'}", spinner):
            return denial_msg
        try:
            entries = sorted(os.listdir(full))
            res_str = "\n".join((e + "/" if os.path.isdir(os.path.join(full, e)) else e) for e in entries) or "(empty)"
            if sys.stdout.isatty():
                if spinner: spinner.stop()
                _console_err.print(f"[dim]{res_str}[/dim]")
            return res_str
        except Exception as e: return f"[error] failed to list files: {e}"

    if name == "run_command":
        cmd = args.get("command", "")
        if gates_active and not sys.stdout.isatty():
            return "[denied] no terminal available to approve command execution"
        if gates_active:
            if spinner: spinner.stop()
            if not ui.confirm_tool(f"execute: $ {cmd}"): return denial_msg
        else:
            _console_err.print(f"[dim]  Executing command autonomously: $ {cmd}[/dim]")

        shell = os.environ.get("SHELL") or "/bin/sh"
        if spinner:
            try: spinner.update("Working...")
            except Exception: pass
            spinner.start("Working...")
        try:
            res = subprocess.run([shell, "-lc", cmd], cwd=workspace, capture_output=True, text=True, timeout=300)
            out = ((res.stdout or "") + (("\n" + res.stderr) if res.stderr else "")).strip()[:10000]

            if sys.stdout.isatty() and out.strip():
                if spinner: spinner.stop()
                _console_err.print()
                if os.environ.get("AI_RENDER_MARKDOWN", "1") == "1" and ("#" in out or "|" in out or "```" in out):
                    _console_err.print(Markdown(out, code_theme="ansi_dark"))
                else: _console_err.print(out)
                _console_err.print()

            return f"(exit {res.returncode})\n{out}" if res.returncode != 0 else (out or "(exit 0, no output)")
        except subprocess.TimeoutExpired:
            return "[error] command timed out after 300 seconds"
        finally:
            if spinner: spinner.stop()

    return f"[error] unknown tool {name}"


def agentic_turn(messages: List[Dict[str, Any]], url: str, headers: Dict[str, str], body: Dict[str, Any], timeout: int, spinner: Any, show_stats: bool = False, is_agent: bool = False) -> Optional[str]:
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    is_local = "localhost" in url or "127.0.0.1" in url or body.get("model") == "local-model"

    if is_agent and messages and messages[0]["role"] == "system" and "### EDIT MODE" not in messages[0]["content"]:
        messages[0]["content"] += f"\n\n### EDIT MODE:\nYou are an active coding agent at {workspace}.\n\n### WORKING TOOLS:\nCapabilities: read_file, write_file, list_dir, run_command. Root: {workspace}."

    resolved_model = None
    streamer = None

    for _round in range(10):
        body_tools = {**body, "messages": messages, "stream": True}
        if is_agent: body_tools["tools"] = EDIT_TOOLS

        if spinner:
            try: spinner.update("Working...")
            except Exception: pass
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

                    if reasoning and spinner:
                        try: spinner.update("Thinking...")
                        except Exception: pass
                    elif content and spinner and not reasoning and not in_think_block:
                        try: spinner.update("Working...")
                        except Exception: pass

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
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {"id": tc.get("id", ""), "type": "function", "function": {"name": tc.get("function", {}).get("name", ""), "arguments": ""}}
                        if tc.get("function", {}).get("name"): tool_calls_map[idx]["function"]["name"] = tc["function"]["name"]
                        tool_calls_map[idx]["function"]["arguments"] += tc.get("function", {}).get("arguments", "")
                except Exception: pass

            if streamer: streamer.stop()
            elif not first_chunk: print("")

            ans_text = "".join(acc_content)
            in_tok, out_tok = _calc_turn_tokens(ans_text, messages, captured_usage, is_local)

            if speed_test and show_stats and not first_chunk:
                speed_test.end(actual_out_tokens=out_tok, is_local=is_local)

            calls = [val for _, val in sorted(tool_calls_map.items())] if tool_calls_map else None
            if not calls or not is_agent:
                _log_turn_usage(resolved_model or body.get("model") or "local-model", in_tok, out_tok, 0.0, show_stats, in_tok + out_tok)
                return ans_text

            messages.append({"role": "assistant", "content": ans_text or None, "tool_calls": calls})

            for tc in calls:
                fname = tc.get("function", {}).get("name", "")
                args = json.loads(tc.get("function", {}).get("arguments") or "{}") if tc.get("function", {}).get("arguments") else {}
                brief = str(args.get("path") or args.get("command") or "")[:100]
                verb = TOOL_VERBS.get(fname, "working")

                _console_err.print(f"[dim]∗ {verb} • [cyan]{fname}[/cyan] [italic]{brief}[/italic][/dim]")
                if spinner:
                    try: spinner.update("Working...")
                    except Exception: pass
                    spinner.start("Working...")

                try:
                    result = _run_edit_tool(fname, args, workspace, spinner)
                except Exception as e:
                    result = f"[tool error] {e}"
                finally:
                    if spinner: spinner.stop()

                # Reasonix Harness: Deterministic Tool Result Pruning for Prefix Cache Stability
                if len(result) > 1500:
                    pruned_result = result[:1200] + f"\n... [Reasonix Harness: Snipped {len(result) - 1200} chars for context stability]"
                else:
                    pruned_result = result

                messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "name": fname, "content": pruned_result})

        except KeyboardInterrupt:
            if streamer:
                try: streamer.stop(interrupted=True)
                except Exception: pass
            if spinner:
                try: spinner.stop()
                except Exception: pass
            raise
        except Exception as e:
            sys.stderr.write(f"\033[90m[sys] API response error: {e}\033[0m\n")
            return None
        finally:
            if spinner: spinner.stop()

    return None


def stream_response(messages: List[Dict[str, Any]], prefix: str = "AI: ", cfg_dir: str = "", show_stats: bool = False, thinking_budget: int = 0, is_agent: bool = False) -> Optional[str]:
    spinner = ui.InlineSpinner()
    try:
        configs = agent_cloud.get_active_configs(messages)
        enable_think = thinking_budget > 0
        budget_val = thinking_budget if enable_think else 0

        local_body = {"messages": messages, "stream": True}
        if enable_think:
            local_body["thinking_budget_tokens"] = budget_val
            local_body["reasoning_budget"] = budget_val
            local_body["chat_template_kwargs"] = {"enable_thinking": True}

        seen_urls = set()
        unique_configs = []
        for url, headers, body, timeout in configs:
            norm_url = "http://localhost:8080/v1/chat/completions" if ":8080" in url else url.replace("127.0.0.1", "localhost")
            if "localhost" in norm_url or "127.0.0.1" in norm_url:
                if enable_think:
                    body["thinking_budget_tokens"] = budget_val
                    body["reasoning_budget"] = budget_val
                    body["chat_template_kwargs"] = {"enable_thinking": True}

            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                unique_configs.append(("http://localhost:8080/v1/chat/completions" if ":8080" in url else url, headers, body, timeout))

        if "http://localhost:8080/v1/chat/completions" not in seen_urls:
            unique_configs.append(("http://localhost:8080/v1/chat/completions", {}, local_body, 180))

        for url, headers, body, timeout in unique_configs:
            ans = agentic_turn(messages, url, headers, body, timeout, spinner, show_stats, is_agent=is_agent)
            if ans is not None: return ans

        return None
    except KeyboardInterrupt:
        if spinner:
            try: spinner.stop()
            except Exception: pass
        sys.stderr.write("\r\x1b[2K\033[90m[sys] Interrupted.\033[0m\033[0m\n")
        return None


def get_accurate_token_count(text: Any, server_url: str = "http://localhost:8080") -> int:
    """Fast non-allocating token estimation (3.6 chars/token average)."""
    if not text: return 0
    length = len(text) if isinstance(text, str) else len(str(text))
    return max(1, (length * 10) // 36)


def show_memory_status(messages: List[Dict[str, Any]], max_context: int = 8192, server_url: str = "http://localhost:8080") -> None:
    total_toks = sum(get_accurate_token_count(m.get("content") or "", server_url) for m in messages)
    pct = (total_toks / max_context) * 100
    filled = int((total_toks / max_context) * 20)
    bar = "█" * filled + "░" * (20 - filled)
    color = "green" if pct < 70 else "yellow" if pct < 90 else "red"

    _console.print(Panel(
        Group(
            Text.assemble(("Context Window: ", "dim"), (f"{total_toks}", f"bold {color}"), (f"/{max_context} tokens ", "dim"), (f"({pct:.1f}%)", f"bold {color}")),
            Text(f"[{bar}]", style=color)
        ),
        title="Memory & Context Status", title_align="left", border_style="bright_black", box=ROUNDED, expand=False
    ))


def prune_history(history: List[Dict[str, Any]], max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
    """Prune conversation history while preserving system prompt and maintaining Reasonix cache stability."""
    if len(history) <= 1: return history
    limit = max_tokens or int(os.environ.get("AI_MAX_TOKENS", 8192))
    
    # Reasonix Harness: Strip stale tool interactions during context compaction
    history = [m for m in history if m.get("role") != "tool"]

    sys_prompt = history[0]
    curr = get_accurate_token_count(sys_prompt.get("content", ""))
    selected: List[Dict[str, Any]] = []

    for msg in reversed(history[1:]):
        toks = get_accurate_token_count(msg.get("content", ""))
        if curr + toks > limit and selected: break
        selected.append(msg)
        curr += toks

    selected.reverse()
    return [sys_prompt] + selected
