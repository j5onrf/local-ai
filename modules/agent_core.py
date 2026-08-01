"""
Local-AI Agent Core Module
Handles streaming SSE payloads, function execution, tool gates, and Rich Markdown rendering.
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

import requests
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from rich.syntax import Syntax

import agent_ui as ui
import agent_cloud

_console = Console()
_console_err = Console(stderr=True)
_session = requests.Session()

# Pre-compiled module constants
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')
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


class RichStreamer:
    """Streams direct text during generation, then renders full Rich Markdown on completion in a final pass."""

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
        self.pending_think_newlines: str = ""

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

            if self.phase == "THINKING":
                return

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
            self.pending_think_newlines = ""
            self._update_spinner("Thinking...")
            token = token.replace("<think>", "")

        if "</think>" in token:
            parts = token.split("</think>", 1)
            thinking_part = parts[0]
            answer_part = parts[1] if len(parts) > 1 else ""

            self.accumulated_thinking += thinking_part

            if show_think and self.phase == "THINKING" and self.accumulated_thinking.strip():
                text_part = thinking_part.rstrip("\r\n")
                if text_part:
                    try:
                        if self.pending_think_newlines:
                            sys.stderr.write(f"\033[2;3m{self.pending_think_newlines}\033[0m")
                            self.pending_think_newlines = ""
                        sys.stderr.write(f"\033[2;3m{text_part}\033[0m")
                        sys.stderr.flush()
                    except (IOError, OSError): pass

                self.pending_think_newlines = ""
                try:
                    sys.stderr.write("\n")
                    sys.stderr.flush()
                except (IOError, OSError): pass
                _console_err.print("[dim]╰────────────────────────────────────────────────────────[/dim]")

            self.phase = "ANSWER"
            self._update_spinner("Working...")
            try:
                sys.stdout.write("\n")
                sys.stdout.flush()
            except (IOError, OSError): pass

            if answer_part:
                self.update(answer_part)
            return

        if self.phase == "THINKING":
            if self.first_think_token:
                token = token.lstrip("\r\n")
                if token:
                    self.first_think_token = False

            if token:
                self.accumulated_thinking += token
                if show_think:
                    if not self.thinking_started and token.strip():
                        self.thinking_started = True
                        self._stop_spinner()
                        _console_err.print("[dim]╭─ ⚙ ────────────────────────────────────────────────────[/dim]")

                    text_part = token.rstrip("\r\n")
                    newlines_part = token[len(text_part):]

                    try:
                        if text_part:
                            if self.pending_think_newlines:
                                sys.stderr.write(f"\033[2;3m{self.pending_think_newlines}\033[0m")
                                self.pending_think_newlines = ""
                            sys.stderr.write(f"\033[2;3m{text_part}\033[0m")
                            sys.stderr.flush()

                        if newlines_part:
                            self.pending_think_newlines += newlines_part
                    except (IOError, OSError): pass
        else:
            if self.phase != "ANSWER":
                self.phase = "ANSWER"

            if not self.answer_started:
                self._stop_spinner()
                self.answer_started = True
                p_style = "\033[1;32m" if "Agent" in self.prefix else "\033[1;36m"
                try:
                    sys.stdout.write(f"{p_style}{self.prefix.strip()}\033[0m ")
                    sys.stdout.write("\033[?25h")
                    sys.stdout.flush()
                except (IOError, OSError): pass

            clean_tok = token.replace("\\n", "\n")
            self.accumulated_answer += clean_tok
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
            try:
                sys.stderr.write("\n")
                sys.stderr.flush()
            except (IOError, OSError): pass
            _console_err.print("[dim]╰────────────────────────────────────────────────────────[/dim]")
            self.phase = "ANSWER"

        # FINAL PASS: Rewind lines and render Rich Markdown
        if self.answer_started:
            render_md = os.environ.get("AI_RENDER_MARKDOWN", "1") == "1"
            if render_md and self.accumulated_answer.strip() and sys.stdout.isatty():
                try:
                    cols = shutil.get_terminal_size((80, 24)).columns or 80
                    p_str = f"{self.prefix.strip()} " if self.prefix else ""
                    full_str = p_str + self.accumulated_answer

                    total_rows = 0
                    for line in full_str.split("\n"):
                        clean_len = len(ANSI_ESCAPE.sub('', line))
                        total_rows += max(1, (clean_len + cols - 1) // cols)

                    up_count = max(0, total_rows - 1)
                    if up_count > 0:
                        sys.stdout.write(f"\r\033[{up_count}A\033[J")
                    else:
                        sys.stdout.write("\r\033[J")
                    sys.stdout.flush()

                    p_style = "bold green" if "Agent" in self.prefix else "bold cyan"
                    if self.prefix.strip():
                        _console.print(Text.from_markup(f"[{p_style}]{self.prefix.strip()}[/{p_style}]"))
                    _console.print(Markdown(self.accumulated_answer, code_theme="ansi_dark"))
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
    if not usage_log:
        return
    try:
        usage_log.record(model, in_tok, out_tok, cost)
        usage_log.refresh_balance_async(min_age=10)
        if show_stats and sys.stdout.isatty():
            ctx_max = int(os.environ.get("AI_MAX_TOKENS", 8192)) if ctx_used is not None else None
            print(usage_log.turn_line(in_tok, out_tok, cost, ctx_used, ctx_max))
    except Exception: pass


def _process_stream_chunk(content: str, reasoning: str, in_think_block: bool) -> Tuple[str, bool, bool]:
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
    return sum(len(m.get("content") or "") for m in messages) // 4, len(ans_text) // 4


def _safe_path(workspace: str, p: str) -> str:
    if not p:
        return os.path.realpath(workspace)
    p = os.path.expanduser(urllib.parse.unquote(str(p).strip()))
    return os.path.realpath(p if os.path.isabs(p) else os.path.join(workspace, p))


def _is_outside_workspace(workspace: str, full_path: str) -> bool:
    root = os.path.realpath(workspace)
    return full_path != root and not full_path.startswith(root + os.sep)


def _confirm_gate(reason: str, spinner: Any) -> bool:
    if spinner:
        spinner.stop()
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
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(60000)
            if sys.stdout.isatty() and content.strip():
                if spinner: spinner.stop()
                _console_err.print()
                if os.environ.get("AI_RENDER_MARKDOWN", "1") == "1" and ("#" in content or "|" in content):
                    _console_err.print(Markdown(content, code_theme="ansi_dark"))
                else:
                    _console_err.print(content)
                _console_err.print()
            return content
        except Exception as e:
            return f"[error] failed to read file: {e}"

    if name == "write_file":
        raw_path = args.get("path", "")
        full = _safe_path(workspace, raw_path)
        content = args.get("content", "")
        outside = _is_outside_workspace(workspace, full)
        exists = os.path.exists(full)

        if full.endswith(".py"):
            try: ast.parse(content)
            except SyntaxError as e: return f"[error] Write blocked. Python syntax error: {e.msg} on line {e.lineno}."
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
        except Exception as e:
            return f"[error] failed to write file: {e}"

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
        except Exception as e:
            return f"[error] failed to list files: {e}"

    if name == "run_command":
        cmd = args.get("command", "")
        if not sys.stdout.isatty():
            return "[denied] no terminal available to approve command execution"
        if gates_active:
            if spinner: spinner.stop()
            if not ui.confirm_tool(f"execute: $ {cmd}"):
                return denial_msg
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
                else:
                    _console_err.print(out)
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
        if is_agent:
            body_tools["tools"] = EDIT_TOOLS

        if spinner:
            try: spinner.update("Working...")
            except Exception: pass
            spinner.start("Working...")
        try:
            res = _session.post(url, json=body_tools, headers={"Content-Type": "application/json", **headers}, timeout=timeout, stream=True)
            first_chunk, acc_content, tool_calls_map, in_think_block, captured_usage = True, [], {}, False, None

            for line in res.iter_lines(chunk_size=1):
                if not line or not line.decode("utf-8", errors="ignore").strip().startswith("data:"):
                    continue
                data_str = line.decode("utf-8", errors="ignore").strip()[5:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                    captured_usage = data.get("usage") or captured_usage
                    resolved_model = data.get("model") or resolved_model
                    choices = data.get("choices", [{}])
                    if not choices:
                        continue
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
                            if os.environ.get("AI_SHOW_THINKING", "1") == "1":
                                spinner.stop()
                            streamer = RichStreamer(prefix="Agent:" if is_agent else "AI:", spinner=spinner)
                            streamer.start()
                            if speed_test and show_stats:
                                speed_test.start()

                        if streamer:
                            streamer.update(chunk_to_stream)
                        acc_content.append(chunk_to_stream)
                        if speed_test and show_stats:
                            speed_test.count_token(chunk_to_stream, is_thinking=is_thinking)

                    for tc in delta.get("tool_calls", []):
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {"id": tc.get("id", ""), "type": "function", "function": {"name": tc.get("function", {}).get("name", ""), "arguments": ""}}
                        if tc.get("function", {}).get("name"):
                            tool_calls_map[idx]["function"]["name"] = tc["function"]["name"]
                        tool_calls_map[idx]["function"]["arguments"] += tc.get("function", {}).get("arguments", "")
                except Exception: pass

            if streamer:
                streamer.stop()
            elif not first_chunk:
                print("")

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

                messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "name": fname, "content": result})

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

        local_body = {
            "messages": messages,
            "stream": True,
            "model": "local-model",
            "max_tokens": 2048,
            "reasoning_budget": budget_val,
            "thinking_budget_tokens": budget_val,
            "chat_template_kwargs": {"enable_thinking": enable_think}
        }

        seen_urls = set()
        unique_configs = []
        for url, headers, body, timeout in configs:
            norm_url = "http://localhost:8080/v1/chat/completions" if ":8080" in url else url.replace("127.0.0.1", "localhost")
            if "localhost" in norm_url or "127.0.0.1" in norm_url:
                body["reasoning_budget"] = budget_val
                body["thinking_budget_tokens"] = budget_val
                body["chat_template_kwargs"] = {"enable_thinking": enable_think}

            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                unique_configs.append(("http://localhost:8080/v1/chat/completions" if ":8080" in url else url, headers, body, timeout))

        if "http://localhost:8080/v1/chat/completions" not in seen_urls:
            unique_configs.append(("http://localhost:8080/v1/chat/completions", {}, local_body, 180))

        for url, headers, body, timeout in unique_configs:
            ans = agentic_turn(messages, url, headers, body, timeout, spinner, show_stats, is_agent=is_agent)
            if ans is not None:
                return ans

        return None
    except KeyboardInterrupt:
        if spinner:
            try: spinner.stop()
            except Exception: pass
        sys.stderr.write("\r\x1b[2K\033[90m[sys] Interrupted.\033[0m\033[0m\n")
        return None


def get_accurate_token_count(text: str, server_url: str = "http://localhost:8080") -> int:
    if not text:
        return 0
    return max(1, int(len(text) / 3.6))


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
    if len(history) <= 1:
        return history
    try:
        limit = int(os.environ.get("AI_MAX_TOKENS", 8192)) if max_tokens is None else max_tokens
    except (ValueError, TypeError):
        limit = 8192

    sys_prompt = history[0]
    curr = len(sys_prompt.get("content", "")) // 4
    selected: List[Dict[str, Any]] = []

    for msg in reversed(history[1:]):
        toks = len(msg.get("content", "") or "") // 4
        if not selected or (curr + toks <= limit):
            selected.append(msg)
            curr += toks
        else:
            break

    return [sys_prompt] + list(reversed(selected))
