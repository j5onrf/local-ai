# File: ~/.config/local-ai/modules/agent_core.py
import os
import sys
import re
import json
import time
import urllib.request as urlreq
import urllib.error as urlerr
import requests
import difflib
import agent_ui as ui
import agent_cloud

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from rich.console import Group

_console = Console()

try:
    import agent_usage as usage_log
except ImportError:
    usage_log = None

_session = requests.Session()

try:
    import speed_test
except ImportError:
    speed_test = None


class RichStreamer:
    """
    Renders stream content dynamically using Rich.
    Detects and isolates <think>...</think> monologue blocks into a distinct panel,
    rendering final conversational answers with full syntax-highlighted Markdown.
    """
    def __init__(self, prefix: str = "", active: bool = True):
        self.prefix = prefix
        self.active = active and sys.stdout.isatty()
        self.accumulated = ""
        self.live = None

    def start(self):
        if self.active:
            self.live = Live("", console=_console, auto_refresh=False, vertical_overflow="visible")
            self.live.start()

    def update(self, token: str):
        self.accumulated += token
        if not self.active:
            print(token, end="", flush=True)
            return

        text = self.accumulated
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
                
                render_group = Group(
                    thinking_panel, 
                    Markdown(f"{self.prefix}{answer_text}" if answer_text.strip() else "")
                )
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
                render_group = Group(
                    thinking_panel,
                    Markdown(f"{self.prefix}{before_think}" if before_think.strip() else "")
                )
            
            self.live.update(render_group)
        else:
            self.live.update(Markdown(f"{self.prefix}{text}"))
        
        self.live.refresh()

    def stop(self):
        if self.live:
            self.live.stop()
            print()


def _log_turn_usage(model: str, in_tok: int, out_tok: int, cost: float,
                    show_stats: bool, ctx_used: int = None) -> None:
    """Records a finished turn in the spend ledger and, when stats are on,
    prints the dim usage line (tokens, turn cost, today's spend, context left)."""
    if not usage_log:
        return
    try:
        usage_log.record(model, in_tok, out_tok, cost)
        usage_log.refresh_balance_async(min_age=10)
        if show_stats and sys.stdout.isatty():
            ctx_max = None
            if ctx_used is not None:
                try:
                    ctx_max = int(os.environ.get("AI_MAX_TOKENS", 8192))
                except Exception:
                    ctx_max = 8192
            print(usage_log.turn_line(in_tok, out_tok, cost, ctx_used, ctx_max))
    except Exception:
        pass


def extract_stream_content(line_bytes: bytes) -> str:
    """Performs raw byte-level searching to extract streaming tokens."""
    idx = line_bytes.find(b'"content":"')
    if idx == -1:
        idx = line_bytes.find(b'"text":"')
        if idx == -1:
            return ""
        start = idx + 8
    else:
        start = idx + 11

    end = start
    length = len(line_bytes)
    while end < length:
        char = line_bytes[end]
        if char == 34:  # ASCII for double quote '"'
            break
        if char == 92:  # ASCII for backslash '\'
            end += 2    # Skip escaped character
        else:
            end += 1

    try:
        raw_str_bytes = line_bytes[start:end]
        json_str = b'"' + raw_str_bytes + b'"'
        return json.loads(json_str.decode("utf-8", errors="ignore"))
    except Exception:
        return line_bytes[start:end].decode("utf-8", errors="ignore")


def stream(messages, prefix, gkey, spinner_class, show_stats: bool = True):
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    sf = os.path.join(workspace, ".agent", "session.json")
    
    saved_id = None
    if os.path.exists(sf):
        try:
            with open(sf, "r", encoding="utf-8") as f:
                saved_id = json.load(f).get("last_interaction_id")
        except Exception:
            pass

    model = os.environ.get("CLOUD_MODEL", "gemini-3.5-flash")
    body = {"model": model, "input": messages[-1]["content"] if messages else "", "stream": True}
    if messages and messages[0]["role"] == "system":
        body["system_instruction"] = messages[0]["content"]
    if saved_id:
        body["previous_interaction_id"] = saved_id

    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    headers = {"x-goog-api-key": gkey, "Content-Type": "application/json"}
    req = urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    spinner = spinner_class()

    try:
        spinner.start()
        with urlreq.urlopen(req, timeout=30) as response:
            try:
                cfg_dir = os.path.expanduser("~/.config/local-ai")
                with open(os.path.join(cfg_dir, ".request_log"), "a", encoding="utf-8") as f:
                    f.write(f"{int(time.time())}|gemini-interactions\n")
            except Exception:
                pass
            
            first, acc, resolved_id = True, [], None
            streamer = None
            for line in response:
                dec = line.decode("utf-8").strip()
                if not dec:
                    continue
                if dec.startswith("data:"):
                    dec = dec[5:].strip()
                if dec == "[DONE]":
                    continue
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
                        
                        streamer.update(content)
                        acc.append(content)
                        if speed_test and show_stats:
                            speed_test.count_token(content)
                except Exception:
                    pass
            
            if streamer:
                streamer.stop()
            else:
                print("")

            if speed_test and show_stats:
                speed_test.end()

            ans_text = "".join(acc)
            in_est = (len(body.get("input", "")) + len(body.get("system_instruction", ""))) // 4
            ctx_est = (sum(len(m.get("content") or "") for m in messages) + len(ans_text)) // 4
            _log_turn_usage(model, in_est, len(ans_text) // 4, 0.0, show_stats, ctx_est)

            if resolved_id:
                try:
                    os.makedirs(os.path.dirname(sf), exist_ok=True)
                    with open(sf, "w", encoding="utf-8") as f:
                        json.dump({"last_interaction_id": resolved_id}, f)
                except Exception:
                    pass
            return "".join(acc)
    except urlerr.HTTPError as e:
        spinner.stop()
        if saved_id and e.code in (400, 404):
            try:
                os.remove(sf)
            except Exception:
                pass
        return None
    except Exception:
        spinner.stop()
        return None


_EDIT_TOOLS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a text file from the project. Returns its content.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Path relative to the project root"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Create or overwrite a text file in the project with the given content.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Path relative to the project root"},
            "content": {"type": "string", "description": "Full new file content"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "List files and directories at a path inside the project.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Path relative to the project root, '' for the root"}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "run_command",
        "description": "Run a shell command in the project root. The user must approve it first.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}},
            "required": ["command"]}}},
]

EDIT_SYSTEM_ADD = (
    "\n\n### EDIT MODE (overrides any read-only rules above):\n"
    "You are an active coding agent with write access to the project at {ws}. "
    "Use your tools to inspect and modify files directly instead of describing changes. "
    "After modifying files or executing scripts, reply briefly: what you changed, where, and why."
)

TOOLS_SYSTEM_ADD = (
    "\n\n### WORKING TOOLS:\n"
    "You have operational capabilities to read, write, and execute files: {names}. The project root is {ws} — relative "
    "paths resolve there and run_command executes there."
)

TOOL_VERBS = {
    "read_file": "checking",
    "write_file": "updating",
    "list_dir": "checking",
    "run_command": "executing"
}


def _safe_path(workspace: str, p: str) -> str:
    root = os.path.realpath(workspace)
    return os.path.realpath(os.path.join(root, os.path.expanduser(p or "")))


def _is_outside_workspace(workspace: str, full_path: str) -> bool:
    root = os.path.realpath(workspace)
    return full_path != root and not full_path.startswith(root + os.sep)


def _run_edit_tool(name: str, args: dict, workspace: str, spinner=None) -> str:
    import subprocess
    gates_active = os.environ.get("AI_CONFIRM_GATES", "1") == "1"

    if name == "read_file":
        full = _safe_path(workspace, args.get("path", ""))
        outside = _is_outside_workspace(workspace, full)
        
        if outside or gates_active:
            reason = f"read {full} (OUTSIDE workspace)" if outside else f"read file {args.get('path')}"
            
            if spinner:
                spinner.stop()
                
            if not sys.stdout.isatty() or not ui.confirm_tool(reason):
                return f"[denied] the user blocked reading operations for safety: {reason}"
                
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                return f.read(60000)
        except Exception as e:
            return f"[error] failed to read file: {e}"

    if name == "write_file":
        full = _safe_path(workspace, args.get("path", ""))
        content = args.get("content", "")
        outside = _is_outside_workspace(workspace, full)
        exists = os.path.exists(full)
        
        if full.endswith(".py"):
            import ast
            try:
                ast.parse(content)
            except SyntaxError as e:
                return f"[error] Write blocked. Python syntax verification failed: {e.msg} on line {e.lineno}. Please correct this syntax error and try writing again."
                
        if full.endswith(".json"):
            try:
                json.loads(content)
            except Exception as e:
                return f"[error] Write blocked. JSON validation failed: {e}. Please correct the JSON formatting and try writing again."

        if sys.stdout.isatty():
            if exists:
                try:
                    with open(full, "r", encoding="utf-8", errors="replace") as f:
                        old = f.read()
                    diff = difflib.unified_diff(
                        old.splitlines(),
                        content.splitlines(),
                        fromfile=f"a/{args.get('path')}",
                        tofile=f"b/{args.get('path')}",
                        lineterm=""
                    )
                    diff_text = "\n".join(diff)
                    if diff_text:
                        color_lines = []
                        for line in diff_text.splitlines():
                            if line.startswith("+"):
                                color_lines.append(f"\033[32m{line}\033[0m")
                            elif line.startswith("-"):
                                color_lines.append(f"\033[31m{line}\033[0m")
                            elif line.startswith("@"):
                                color_lines.append(f"\033[36m{line}\033[0m")
                            else:
                                color_lines.append(line)
                        sys.stderr.write("\n" + "\n".join(color_lines) + "\n\n")
                except Exception:
                    sys.stderr.write(f"\033[2m  {args.get('path')} — existing file modification\033[0m\n")
            else:
                sys.stderr.write(f"\033[2m  {args.get('path')} — new file, {len(content.splitlines())} lines\033[0m\n")

        if outside or gates_active:
            verb = "overwrite" if exists else "create"
            where = f"{full} (OUTSIDE workspace)" if outside else args.get("path")
            reason = f"{verb} {where} ({len(content)} chars)"
            
            if spinner:
                spinner.stop()
                
            if not sys.stdout.isatty() or not ui.confirm_tool(reason):
                return f"[denied] the user blocked file write operations: {reason}"

        try:
            os.makedirs(os.path.dirname(full) or workspace, exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            return f"wrote {len(content)} chars to {args.get('path')}"
        except Exception as e:
            return f"[error] failed to write file: {e}"

    if name == "list_dir":
        full = _safe_path(workspace, args.get("path", ""))
        outside = _is_outside_workspace(workspace, full)
        
        if outside or gates_active:
            reason = f"list directory {full} (OUTSIDE workspace)" if outside else f"list files in {args.get('path') or '.'}"
            
            if spinner:
                spinner.stop()
                
            if not sys.stdout.isatty() or not ui.confirm_tool(reason):
                return f"[denied] the user blocked directory listing: {reason}"
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
        except subprocess.TimeoutExpired:
            return "[error] command timed out after 300 seconds"
        finally:
            if spinner:
                spinner.stop()
        out = ((res.stdout or "") + (("\n" + res.stderr) if res.stderr else "")).strip()[:10000]
        if res.returncode != 0:
            return f"(exit {res.returncode})\n{out}" if out else f"(exit {res.returncode}, no output)"
        return out or "(exit 0, no output)"

    return f"[error] unknown tool {name}"


def agentic_turn(messages: list, url: str, headers: dict, body: dict, timeout: int, spinner, show_stats: bool = False) -> str or None:
    """Executes a multi-turn streaming agent round-trip loop supporting parallel tool evaluations."""
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    
    if messages and messages[0]["role"] == "system":
        if "### EDIT MODE" not in messages[0]["content"]:
            messages[0]["content"] += EDIT_SYSTEM_ADD.format(ws=workspace)
            messages[0]["content"] += TOOLS_SYSTEM_ADD.format(
                names="read_file, write_file, list_dir, run_command", ws=workspace)
            
    resolved_model = None
    for _round in range(10):
        body_tools = dict(body)
        body_tools["messages"] = messages
        body_tools["stream"] = True  
        body_tools["tools"] = _EDIT_TOOLS
        
        spinner.start()
        start_time = time.time()
        try:
            res = _session.post(
                url,
                json=body_tools,
                headers={"Content-Type": "application/json", **headers},
                timeout=timeout,
                stream=True
            )
            
            first_chunk = True
            acc_content = []
            tool_calls_map = {}
            streamer = None
            
            for line in res.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8", errors="ignore").strip()
                if not line_str.startswith("data:"):
                    continue
                data_str = line_str[5:].strip()
                if data_str == "[DONE]":
                    break
                    
                try:
                    data = json.loads(data_str)
                    resolved_model = data.get("model") or resolved_model
                    choices = data.get("choices", [{}])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    
                    content = delta.get("content", "")
                    if content:
                        if first_chunk:
                            spinner.stop()  
                            first_chunk = False
                            streamer = RichStreamer(prefix="Agent: ")
                            streamer.start()
                            if speed_test and show_stats:
                                speed_test.start()
                        
                        streamer.update(content)
                        acc_content.append(content)
                        if speed_test and show_stats:
                            speed_test.count_token(content)
                            
                    tool_calls = delta.get("tool_calls", [])
                    for tc in tool_calls:
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {
                                "id": tc.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": tc.get("function", {}).get("name", ""),
                                    "arguments": ""
                                }
                            }
                        if tc.get("function", {}).get("name"):
                            tool_calls_map[idx]["function"]["name"] = tc["function"]["name"]
                        args_chunk = tc.get("function", {}).get("arguments", "")
                        tool_calls_map[idx]["function"]["arguments"] += args_chunk
                except Exception:
                    pass
                    
            if streamer:
                streamer.stop()
            elif not first_chunk:
                print("")

            if speed_test and show_stats and not first_chunk:
                speed_test.end()
                    
            elapsed_time = time.time() - start_time
            ans_text = "".join(acc_content)
            calls = [val for _, val in sorted(tool_calls_map.items())] if tool_calls_map else None
            
            if not calls:
                prompt_chars = sum(len(m.get("content") or "") for m in messages)
                in_tok = prompt_chars // 4
                out_tok = len(ans_text) // 4
                
                _log_turn_usage(resolved_model or body.get("model") or "local-model",
                                in_tok, out_tok, 0.0, show_stats, in_tok + out_tok)
                
                return ans_text
                
            assistant_msg = {"role": "assistant", "content": ans_text or None, "tool_calls": calls}
            messages.append(assistant_msg)
            
            user_aborted = False
            for tc in calls:
                fname = tc.get("function", {}).get("name", "")
                try:
                    args = json.loads(tc.get("function", {}).get("arguments") or "{}")
                except Exception:
                    args = {}
                    
                brief = str(args.get("path") or args.get("command") or "")[:100]
                verb = TOOL_VERBS.get(fname, "working")
                
                if user_aborted:
                    result = "[denied] execution cancelled by user"
                else:
                    _console.print(f"[dim]∗ {verb} • [cyan]{fname}[/cyan] [italic]{brief}[/italic][/dim]")
                    
                    if spinner and fname in ("read_file", "list_dir"):
                        try:
                            spinner.start(verb)
                        except TypeError:
                            spinner.start()
                            if hasattr(spinner, 'text'):
                                spinner.text = verb
                            elif hasattr(spinner, 'message'):
                                spinner.message = verb
                    try:
                        result = _run_edit_tool(fname, args, workspace, spinner)
                        if "[denied]" in result:
                            user_aborted = True  
                    except Exception as e:
                        result = f"[tool error] {e}"
                    finally:
                        if spinner:
                            spinner.stop()
                        
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "name": fname,
                    "content": result
                })
                
            if user_aborted:
                _console.print("[dim][sys] Agent execution halted.[/dim]")
                return ans_text or "Agent: Action cancelled by user."
                
        except Exception as e:
            sys.stderr.write(f"\033[90m[sys] API response error: {e}\033[0m\n")
            return None
        finally:
            spinner.stop()
            
    return None


def stream_response(messages: list, prefix: str = "AI: ", cfg_dir: str = "", show_stats: bool = False, thinking_budget: int = 0, is_agent: bool = False) -> str or None:
    acc = []
    spinner = ui.InlineSpinner()
    try:
        configs = agent_cloud.get_active_configs(messages)

        local_extra = {}
        if thinking_budget and thinking_budget > 0:
            local_extra["thinking_budget_tokens"] = thinking_budget
            local_extra["chat_template_kwargs"] = {"enable_thinking": True}
        else:
            local_extra["chat_template_kwargs"] = {"enable_thinking": False}

        local_body = {
            "messages": messages,
            "stream": True,
            "model": "local-model",
            **local_extra
        }
        
        seen_urls = set()
        unique_configs = []
        for url, headers, body, timeout in configs:
            norm_url = url.replace("127.0.0.1", "localhost")
            if ":8080" in norm_url:
                norm_url = "http://localhost:8080/v1/chat/completions"
                
            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                actual_url = "http://localhost:8080/v1/chat/completions" if ":8080" in url else url
                unique_configs.append((actual_url, headers, body, timeout))
                
        local_url = "http://localhost:8080/v1/chat/completions"
        norm_local = local_url.replace("127.0.0.1", "localhost")
        if norm_local not in seen_urls:
            unique_configs.append((local_url, {}, local_body, 180))
            
        configs = unique_configs

        for url, headers, body, timeout in configs:
            if is_agent:
                ans = agentic_turn(messages, url, headers, body, timeout, spinner, show_stats)
                if ans is not None:
                    return ans
                continue

            req = urlreq.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", **headers},
                method="POST"
            )
            retries = 2
            backoff = 1.5
            while retries >= 0:
                try:
                    spinner.start()
                    with urlreq.urlopen(req, timeout=timeout) as response:
                        try:
                            p = (
                                "gemini" if "generativelanguage" in url else 
                                "openrouter" if "openrouter" in url else 
                                "openai" if "api.openai" in url else 
                                "claude" if "api.anthropic" in url else None
                            )
                            if p and cfg_dir:
                                with open(os.path.join(cfg_dir, ".request_log"), "a", encoding="utf-8") as lf:
                                    lf.write(f"{int(time.time())}|{p}\n")
                        except Exception:
                            pass
                        
                        first, resolved_model = True, None
                        streamer = None
                        for line in response:
                            if not line.startswith(b"data:"):
                                continue
                            
                            content = extract_stream_content(line)
                            if content:
                                if first:
                                    spinner.stop()
                                    first = False
                                    streamer = RichStreamer(prefix=f"{prefix} " if prefix else "")
                                    streamer.start()
                                    if speed_test and show_stats:
                                        speed_test.start()
                                streamer.update(content)
                                acc.append(content)
                                if speed_test and show_stats:
                                    speed_test.count_token(content)
                            else:
                                try:
                                    dec = line.decode("utf-8").strip()
                                    if dec.startswith("data:"):
                                        dec = dec[5:].strip()
                                    if dec and dec != "[DONE]":
                                        data = json.loads(dec)
                                        if "model" in data and not resolved_model:
                                            resolved_model = data["model"]
                                except Exception:
                                    pass
                        if streamer:
                            streamer.stop()
                        else:
                            print("")
                        if speed_test and show_stats:
                            speed_test.end()
                        
                        ans_text = "".join(acc)
                        prompt_chars = sum(len(m.get("content") or "") for m in messages)
                        in_tok = prompt_chars // 4
                        out_tok = len(ans_text) // 4
                        
                        _log_turn_usage(resolved_model or body.get("model") or url.split('/')[2],
                                        in_tok, out_tok, 0.0, show_stats, in_tok + out_tok)

                        return ans_text
                except urlerr.HTTPError as e:
                    spinner.stop()
                    if e.code == 429 and retries > 0:
                        time.sleep(backoff)
                        retries -= 1
                        backoff *= 2
                    elif e.code == 400:
                        sys.stderr.write(f"\n\033[1;31m[API 400 Error]: {e.read().decode('utf-8')}\033[0m\n")
                        break
                    else:
                        host = url.split('/')[2]
                        sys.stderr.write(f"\033[90m[sys] {host} failed: HTTP {e.code}\033[0m\n")
                        break
                except Exception as e:
                    spinner.stop()
                    host = url.split('/')[2]
                    sys.stderr.write(f"\033[90m[sys] {host} failed: {e}\033[0m\n")
                    break
    except KeyboardInterrupt:
        try: 
            spinner.stop()
        except Exception: 
            pass
        sys.stderr.write("\n\r\x1b[2K\r[sys] Interrupted.\n")
        sys.stderr.flush()
        return "".join(acc) if 'acc' in locals() else None
    return None


def get_accurate_token_count(text: str, server_url: str = "http://localhost:8080") -> int:
    try:
        res = _session.post(f"{server_url}/tokenize", json={"content": text}, timeout=3)
        return len(res.json().get("tokens", []))
    except Exception:
        return len(text) // 4


def show_memory_status(messages: list, max_context: int = 8192, server_url: str = "http://localhost:8080") -> None:
    total_toks = sum(get_accurate_token_count(m.get("content") or "", server_url) for m in messages)
    pct = (total_toks / max_context) * 100
    bar_len = 20
    filled = int((total_toks / max_context) * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    
    color = "green" if pct < 70 else "yellow" if pct < 90 else "red"
    
    text_info = Text.assemble(
        ("Context Window: ", "dim"),
        (f"{total_toks}", f"bold {color}"),
        (f"/{max_context} tokens ", "dim"),
        (f"({pct:.1f}%)", f"bold {color}")
    )
    
    panel = Panel(
        Group(
            text_info,
            Text(f"[{bar}]", style=color)
        ),
        title="📊 Memory & Context Status",
        title_align="left",
        border_style="bright_black",
        box=ROUNDED,
        expand=False
    )
    _console.print(panel)


def prune_history(history: list, max_tokens: int = None) -> list:
    """Prunes old messages from conversation history to stay within context windows."""
    if len(history) <= 1:
        return history
    try:
        target_limit = int(os.environ.get("AI_MAX_TOKENS", 8192)) if max_tokens is None else max_tokens
    except Exception:
        target_limit = 8192

    sys_prompt = history[0]
    current_tokens = len(sys_prompt["content"]) // 4
    selected_messages = []

    for msg in reversed(history[1:]):
        approx_tokens = len(msg["content"]) // 4
        if not selected_messages or (current_tokens + approx_tokens <= target_limit):
            selected_messages.append(msg)
            current_tokens += approx_tokens
        else:
            break

    return [sys_prompt] + list(reversed(selected_messages))
