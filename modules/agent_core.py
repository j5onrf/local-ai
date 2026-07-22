# File: ~/.config/local-ai/modules/agent_core.py
import os
import sys
import json
import time
import ast
import subprocess
import difflib
import urllib.request as urlreq
import urllib.error as urlerr
from typing import List, Dict, Any, Optional, Tuple

import requests
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from rich.syntax import Syntax

import agent_ui as ui
import agent_cloud

_console = Console()
_session = requests.Session()

try:
    import agent_usage as usage_log
except ImportError:
    usage_log = None

try:
    import speed_test
except ImportError:
    speed_test = None


class RichStreamer:
    """Renders stream content dynamically using Rich with <think> panel support."""
    def __init__(self, prefix: str = "", active: bool = True) -> None:
        self.prefix: str = prefix
        self.active: bool = active and sys.stdout.isatty()
        self.accumulated: str = ""
        self.live: Optional[Live] = None

    def start(self) -> None:
        if self.active:
            self.live = Live("", console=_console, auto_refresh=False, vertical_overflow="crop", screen=False)
            self.live.start()

    def update(self, token: str) -> None:
        self.accumulated += token
        if not self.active:
            print(token, end="", flush=True)
            return

        show_think_panel = os.environ.get("AI_SHOW_THINKING", "0") == "1"
        text = self.accumulated

        if "<think>" in text:
            before, after = text.split("<think>", 1)
            if "</think>" in after:
                thinking_text, after_think = after.split("</think>", 1)
                answer_text = before + after_think
                if show_think_panel:
                    panel = Panel(Text(thinking_text.strip(), style="italic dim white"), title="⚙ Thinking Process", title_align="left", border_style="bright_black", box=ROUNDED, expand=True)
                    render_group = Group(panel, Markdown(f"{self.prefix}{answer_text}" if answer_text.strip() else ""))
                else:
                    render_group = Markdown(f"{self.prefix}{answer_text}" if answer_text.strip() else "")
            else:
                if show_think_panel:
                    panel = Panel(Text(after.strip(), style="italic dim white"), title="⚙ Thinking Process...", title_align="left", border_style="yellow", box=ROUNDED, expand=True)
                    render_group = Group(panel, Markdown(f"{self.prefix}{before}" if before.strip() else ""))
                else:
                    render_group = Text("⚙ Thinking...", style="italic dim yellow")
        else:
            render_group = Markdown(f"{self.prefix}{text}")

        if self.live:
            self.live.update(render_group)
            self.live.refresh()

    def stop(self) -> None:
        if self.live:
            try:
                self.live.stop()
            except Exception:
                pass
            self.live = None
            print()


def _log_turn_usage(model: str, in_tok: int, out_tok: int, cost: float, show_stats: bool, ctx_used: Optional[int] = None) -> None:
    if not usage_log:
        return
    try:
        usage_log.record(model, in_tok, out_tok, cost)
        usage_log.refresh_balance_async(min_age=10)
        if show_stats and sys.stdout.isatty():
            ctx_max = int(os.environ.get("AI_MAX_TOKENS", 8192)) if ctx_used is not None else None
            print(usage_log.turn_line(in_tok, out_tok, cost, ctx_used, ctx_max))
    except Exception:
        pass


def extract_stream_content(line_bytes: bytes) -> Tuple[str, str, Optional[Dict[str, Any]]]:
    """Safely extracts content, reasoning_content, and usage dictionary from an SSE byte line."""
    try:
        dec = line_bytes.decode("utf-8", errors="ignore").strip()
        if dec.startswith("data:"):
            dec = dec[5:].strip()
        if not dec or dec == "[DONE]":
            return "", "", None

        data = json.loads(dec)
        usage = data.get("usage")
        choices = data.get("choices", [])
        if not choices:
            return "", "", usage

        delta = choices[0].get("delta", {})
        return delta.get("content") or "", delta.get("reasoning_content") or delta.get("thinking") or "", usage
    except Exception:
        return "", "", None


def _process_stream_chunk(content: str, reasoning: str, in_think_block: bool) -> Tuple[str, bool, bool]:
    """Normalizes raw stream content and reasoning text into standard think tags for rendering."""
    if reasoning:
        if not in_think_block:
            return f"<think>{reasoning}", True, True
        return reasoning, True, True
    if content:
        if in_think_block and not ("<think>" in content or "</think>" in content):
            return f"</think>{content}", False, False
        in_think = True if "<think>" in content else (False if "</think>" in content else in_think_block)
        return content, in_think or ("<think>" in content), in_think
    return "", False, in_think_block


def _calc_turn_tokens(ans_text: str, messages: List[Dict[str, Any]], captured_usage: Optional[Dict[str, Any]], is_local: bool) -> Tuple[int, int]:
    """Resolves precise prompt and completion token counts across endpoints."""
    if captured_usage and "completion_tokens" in captured_usage:
        return captured_usage.get("prompt_tokens", 0), captured_usage.get("completion_tokens", 0)
    if is_local:
        return sum(get_accurate_token_count(m.get("content") or "") for m in messages), get_accurate_token_count(ans_text)
    return sum(len(m.get("content") or "") for m in messages) // 4, len(ans_text) // 4


def stream(messages: List[Dict[str, str]], prefix: str, gkey: str, spinner_class: Any, show_stats: bool = True) -> Optional[str]:
    """Streams interactions directly from Google Generative Language interactions endpoint."""
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    sf = os.path.join(workspace, ".agent", "session.json")
    saved_id = json.load(open(sf)).get("last_interaction_id") if os.path.exists(sf) else None

    model = os.environ.get("CLOUD_MODEL", "gemini-3.5-flash")
    body: Dict[str, Any] = {"model": model, "input": messages[-1]["content"] if messages else "", "stream": True}
    if messages and messages[0]["role"] == "system":
        body["system_instruction"] = messages[0]["content"]
    if saved_id:
        body["previous_interaction_id"] = saved_id

    req = urlreq.Request(
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        data=json.dumps(body).encode("utf-8"),
        headers={"x-goog-api-key": gkey, "Content-Type": "application/json"},
        method="POST"
    )
    spinner = spinner_class()

    try:
        spinner.start()
        with urlreq.urlopen(req, timeout=30) as response:
            first, acc, resolved_id, streamer = True, [], None, None
            for line in response:
                dec = line.decode("utf-8").strip()
                if not dec or dec == "[DONE]":
                    continue
                if dec.startswith("data:"):
                    dec = dec[5:].strip()
                try:
                    data = json.loads(dec)
                    if data.get("event_type") == "interaction.completed":
                        resolved_id = data.get("interaction", {}).get("id")
                    
                    content = ""
                    if data.get("event_type") == "step.delta":
                        delta = data.get("delta", {})
                        content = delta.get("text", "") if delta.get("type") == "text" else delta.get("content", {}).get("text", "")
                    
                    if content:
                        if first:
                            spinner.stop()
                            first = False
                            streamer = RichStreamer(prefix=f"{prefix} " if prefix else "")
                            streamer.start()
                            if speed_test and show_stats:
                                speed_test.start()
                        if streamer:
                            streamer.update(content)
                        acc.append(content)
                        if speed_test and show_stats:
                            speed_test.count_token(content, is_thinking=False)
                except Exception:
                    pass
            
            if streamer:
                streamer.stop()
            else:
                print("")

            ans_text = "".join(acc)
            in_est, out_est = (len(body.get("input", "")) + len(body.get("system_instruction", ""))) // 4, len(ans_text) // 4
            
            if speed_test and show_stats:
                speed_test.end(actual_out_tokens=out_est, is_local=False)

            _log_turn_usage(model, in_est, out_est, 0.0, show_stats, (sum(len(m.get("content") or "") for m in messages) + len(ans_text)) // 4)

            if resolved_id:
                os.makedirs(os.path.dirname(sf), exist_ok=True)
                json.dump({"last_interaction_id": resolved_id}, open(sf, "w", encoding="utf-8"))
            return ans_text
    except Exception as e:
        spinner.stop()
        if saved_id and getattr(e, "code", None) in (400, 404):
            try:
                os.remove(sf)
            except Exception:
                pass
        return None


_EDIT_TOOLS: List[Dict[str, Any]] = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file from the project.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create or overwrite a file in the project.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "list_dir", "description": "List directory contents in the project.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run a shell command in project root.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
]

EDIT_SYSTEM_ADD = "\n\n### EDIT MODE:\nYou are an active coding agent at {ws}. Use tools to modify files directly."
TOOLS_SYSTEM_ADD = "\n\n### WORKING TOOLS:\nCapabilities: {names}. Root: {ws}."
TOOL_VERBS = {"read_file": "checking", "write_file": "updating", "list_dir": "checking", "run_command": "executing"}


def _safe_path(workspace: str, p: str) -> str:
    return os.path.realpath(os.path.join(os.path.realpath(workspace), os.path.expanduser(p or "")))


def _is_outside_workspace(workspace: str, full_path: str) -> bool:
    root = os.path.realpath(workspace)
    return full_path != root and not full_path.startswith(root + os.sep)


def _confirm_gate(reason: str, spinner: Any) -> bool:
    if spinner:
        spinner.stop()
    return sys.stdout.isatty() and ui.confirm_tool(reason)


def _run_edit_tool(name: str, args: Dict[str, Any], workspace: str, spinner: Any = None) -> str:
    gates_active = os.environ.get("AI_CONFIRM_GATES", "1") == "1"

    if name == "read_file":
        full = _safe_path(workspace, args.get("path", ""))
        outside = _is_outside_workspace(workspace, full)
        if (outside or gates_active) and not _confirm_gate(f"read {full}" if outside else f"read file {args.get('path')}", spinner):
            return f"[denied] user blocked reading: {args.get('path')}"
        try:
            return open(full, "r", encoding="utf-8", errors="replace").read(60000)
        except Exception as e:
            return f"[error] failed to read file: {e}"

    if name == "write_file":
        full = _safe_path(workspace, args.get("path", ""))
        content = args.get("content", "")
        outside = _is_outside_workspace(workspace, full)
        exists = os.path.exists(full)
        
        if full.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError as e:
                return f"[error] Write blocked. Python syntax error: {e.msg} on line {e.lineno}."
        if full.endswith(".json"):
            try:
                json.loads(content)
            except Exception as e:
                return f"[error] Write blocked. JSON syntax error: {e}."

        if sys.stdout.isatty() and exists:
            try:
                old = open(full, "r", encoding="utf-8", errors="replace").read()
                diff_text = "\n".join(difflib.unified_diff(old.splitlines(), content.splitlines(), fromfile=f"a/{args.get('path')}", tofile=f"b/{args.get('path')}", lineterm=""))
                if diff_text:
                    _console.print()
                    _console.print(Syntax(diff_text, "diff", theme="ansi_dark", background_color="default"))
                    _console.print()
            except Exception:
                pass

        if (outside or gates_active) and not _confirm_gate(f"{'overwrite' if exists else 'create'} {args.get('path')}", spinner):
            return f"[denied] user blocked file write: {args.get('path')}"

        try:
            os.makedirs(os.path.dirname(full) or workspace, exist_ok=True)
            open(full, "w", encoding="utf-8").write(content)
            return f"wrote {len(content)} chars to {args.get('path')}"
        except Exception as e:
            return f"[error] failed to write file: {e}"

    if name == "list_dir":
        full = _safe_path(workspace, args.get("path", ""))
        outside = _is_outside_workspace(workspace, full)
        if (outside or gates_active) and not _confirm_gate(f"list directory {args.get('path') or '.'}", spinner):
            return f"[denied] user blocked directory listing: {args.get('path')}"
        try:
            entries = sorted(os.listdir(full))
            return "\n".join((e + "/" if os.path.isdir(os.path.join(full, e)) else e) for e in entries) or "(empty)"
        except Exception as e:
            return f"[error] failed to list files: {e}"

    if name == "run_command":
        cmd = args.get("command", "")
        if not sys.stdout.isatty():
            return "[denied] no terminal available to approve command execution"
        if gates_active:
            if spinner:
                spinner.stop()
            if not ui.confirm_tool(f"execute: $ {cmd}"):
                return "[denied] user rejected command execution"
        else:
            _console.print(f"[dim]  Executing command autonomously: $ {cmd}[/dim]")

        shell = os.environ.get("SHELL") or "/bin/sh"
        if spinner:
            spinner.start("running")
        try:
            res = subprocess.run([shell, "-lc", cmd], cwd=workspace, capture_output=True, text=True, timeout=300)
            out = ((res.stdout or "") + (("\n" + res.stderr) if res.stderr else "")).strip()[:10000]
            return f"(exit {res.returncode})\n{out}" if res.returncode != 0 else (out or "(exit 0, no output)")
        except subprocess.TimeoutExpired:
            return "[error] command timed out after 300 seconds"
        finally:
            if spinner:
                spinner.stop()

    return f"[error] unknown tool {name}"


def agentic_turn(messages: List[Dict[str, Any]], url: str, headers: Dict[str, str], body: Dict[str, Any], timeout: int, spinner: Any, show_stats: bool = False) -> Optional[str]:
    """Executes a multi-turn streaming agent loop supporting tool execution and evaluation."""
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    is_local = "localhost" in url or "127.0.0.1" in url or body.get("model") == "local-model"
    
    if messages and messages[0]["role"] == "system" and "### EDIT MODE" not in messages[0]["content"]:
        messages[0]["content"] += EDIT_SYSTEM_ADD.format(ws=workspace) + TOOLS_SYSTEM_ADD.format(names="read_file, write_file, list_dir, run_command", ws=workspace)
            
    resolved_model = None
    for _round in range(10):
        body_tools = {**body, "messages": messages, "stream": True, "tools": _EDIT_TOOLS}
        spinner.start()
        try:
            res = _session.post(url, json=body_tools, headers={"Content-Type": "application/json", **headers}, timeout=timeout, stream=True)
            first_chunk, acc_content, tool_calls_map, streamer, in_think_block, captured_usage = True, [], {}, None, False, None
            
            for line in res.iter_lines():
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
                    chunk_to_stream, is_thinking, in_think_block = _process_stream_chunk(content, reasoning, in_think_block)

                    if chunk_to_stream:
                        if first_chunk:
                            spinner.stop()
                            first_chunk = False
                            streamer = RichStreamer(prefix="Agent: ")
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
                except Exception:
                    pass
                    
            if streamer:
                streamer.stop()
            elif not first_chunk:
                print("")

            ans_text = "".join(acc_content)
            in_tok, out_tok = _calc_turn_tokens(ans_text, messages, captured_usage, is_local)

            if speed_test and show_stats and not first_chunk:
                speed_test.end(actual_out_tokens=out_tok, is_local=is_local)
            
            calls = [val for _, val in sorted(tool_calls_map.items())] if tool_calls_map else None
            if not calls:
                _log_turn_usage(resolved_model or body.get("model") or "local-model", in_tok, out_tok, 0.0, show_stats, in_tok + out_tok)
                return ans_text
                
            messages.append({"role": "assistant", "content": ans_text or None, "tool_calls": calls})
            
            user_aborted = False
            for tc in calls:
                fname = tc.get("function", {}).get("name", "")
                args = json.loads(tc.get("function", {}).get("arguments") or "{}") if tc.get("function", {}).get("arguments") else {}
                brief = str(args.get("path") or args.get("command") or "")[:100]
                verb = TOOL_VERBS.get(fname, "working")
                
                if user_aborted:
                    result = "[denied] execution cancelled by user"
                else:
                    _console.print(f"[dim]∗ {verb} • [cyan]{fname}[/cyan] [italic]{brief}[/italic][/dim]")
                    if spinner and fname in ("read_file", "list_dir"):
                        spinner.start(verb)
                    try:
                        result = _run_edit_tool(fname, args, workspace, spinner)
                        if "[denied]" in result:
                            user_aborted = True
                    except Exception as e:
                        result = f"[tool error] {e}"
                    finally:
                        if spinner:
                            spinner.stop()
                        
                messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "name": fname, "content": result})
                
            if user_aborted:
                _console.print("[dim][sys] Agent execution halted.[/dim]")
                return ans_text or "Agent: Action cancelled by user."
                
        except Exception as e:
            sys.stderr.write(f"\033[90m[sys] API response error: {e}\033[0m\n")
            return None
        finally:
            spinner.stop()
            
    return None


def stream_response(messages: List[Dict[str, Any]], prefix: str = "AI: ", cfg_dir: str = "", show_stats: bool = False, thinking_budget: int = 0, is_agent: bool = False) -> Optional[str]:
    """Primary streaming endpoint manager supporting multi-provider failover cascades."""
    acc, spinner = [], ui.InlineSpinner()
    try:
        configs = agent_cloud.get_active_configs(messages)
        local_body = {
            "messages": messages,
            "stream": True,
            "model": "local-model",
            "thinking_budget_tokens": thinking_budget if thinking_budget > 0 else 0,
            "chat_template_kwargs": {"enable_thinking": thinking_budget > 0}
        }
        
        seen_urls = set()
        unique_configs = []
        for url, headers, body, timeout in configs:
            norm_url = "http://localhost:8080/v1/chat/completions" if ":8080" in url else url.replace("127.0.0.1", "localhost")
            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                unique_configs.append(("http://localhost:8080/v1/chat/completions" if ":8080" in url else url, headers, body, timeout))
                
        if "http://localhost:8080/v1/chat/completions" not in seen_urls:
            unique_configs.append(("http://localhost:8080/v1/chat/completions", {}, local_body, 180))
            
        for url, headers, body, timeout in unique_configs:
            if is_agent:
                ans = agentic_turn(messages, url, headers, body, timeout, spinner, show_stats)
                if ans is not None:
                    return ans
                continue

            is_local = "localhost" in url or "127.0.0.1" in url or body.get("model") == "local-model"
            req = urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", **headers}, method="POST")
            retries, backoff = 2, 1.5

            while retries >= 0:
                try:
                    spinner.start()
                    with urlreq.urlopen(req, timeout=timeout) as response:
                        if cfg_dir:
                            p = "gemini" if "generativelanguage" in url else ("openrouter" if "openrouter" in url else ("openai" if "api.openai" in url else ("claude" if "api.anthropic" in url else None)))
                            if p:
                                try:
                                    open(os.path.join(cfg_dir, ".request_log"), "a", encoding="utf-8").write(f"{int(time.time())}|{p}\n")
                                except Exception:
                                    pass
                        
                        first, resolved_model, streamer, in_think_block, captured_usage = True, None, None, False, None
                        for line in response:
                            if not line.startswith(b"data:"):
                                continue
                            
                            content, reasoning, usage = extract_stream_content(line)
                            captured_usage = usage or captured_usage

                            if not content and not reasoning:
                                continue

                            chunk_to_stream, is_thinking, in_think_block = _process_stream_chunk(content, reasoning, in_think_block)

                            if chunk_to_stream:
                                if first:
                                    spinner.stop()
                                    first = False
                                    streamer = RichStreamer(prefix=f"{prefix} " if prefix else "")
                                    streamer.start()
                                    if speed_test and show_stats:
                                        speed_test.start()
                                if streamer:
                                    streamer.update(chunk_to_stream)
                                acc.append(chunk_to_stream)
                                if speed_test and show_stats:
                                    speed_test.count_token(chunk_to_stream, is_thinking=is_thinking)

                        if streamer:
                            streamer.stop()
                        else:
                            print("")
                        
                        ans_text = "".join(acc)
                        in_tok, out_tok = _calc_turn_tokens(ans_text, messages, captured_usage, is_local)

                        if speed_test and show_stats:
                            speed_test.end(actual_out_tokens=out_tok, is_local=is_local)
                        
                        _log_turn_usage(resolved_model or body.get("model") or url.split('/')[2], in_tok, out_tok, 0.0, show_stats, in_tok + out_tok)
                        return ans_text
                except urlerr.HTTPError as e:
                    spinner.stop()
                    if e.code == 429 and retries > 0:
                        time.sleep(backoff)
                        retries -= 1
                        backoff *= 2
                    else:
                        break
                except Exception:
                    spinner.stop()
                    break
    except KeyboardInterrupt:
        if 'streamer' in locals() and streamer:
            try:
                streamer.stop()
            except Exception:
                pass
        if 'spinner' in locals() and spinner:
            try:
                spinner.stop()
            except Exception:
                pass
        sys.stderr.write("\r\x1b[2K\033[90m[sys] Interrupted.\033[0m\n")
        return None


def get_accurate_token_count(text: str, server_url: str = "http://localhost:8080") -> int:
    """Queries the local llama server tokenize endpoint or estimates token count accurately."""
    if not text:
        return 0
    try:
        res = _session.post(f"{server_url}/tokenize", json={"content": text}, timeout=2)
        if res.status_code == 200:
            toks = res.json().get("tokens", [])
            if toks:
                return len(toks)
    except Exception:
        pass
    return max(1, len(text) // 4)


def show_memory_status(messages: List[Dict[str, Any]], max_context: int = 8192, server_url: str = "http://localhost:8080") -> None:
    """Displays context window usage as a Rich graphical bar panel."""
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
        title="📊 Memory & Context Status", title_align="left", border_style="bright_black", box=ROUNDED, expand=False
    ))


def prune_history(history: List[Dict[str, Any]], max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
    """Prunes old conversation messages to stay within maximum context limits."""
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
