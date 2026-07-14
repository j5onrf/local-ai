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

# Safe, optional loading of spend ledger module
try:
    import agent_usage as usage_log
except ImportError:
    usage_log = None

# Create a shared Session object to manage active connection pooling
_session = requests.Session()

# --- OPTIONAL SPEED-TEST HOOK ---
try:
    import speed_test
except ImportError:
    speed_test = None


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


# --- FAST-PATH BYTE EXTRACTOR ---
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


# --- CASCADING COMPLETION ENGINES ---
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
                            if sys.stdout.isatty():
                                sys.stdout.write("\r\x1b[2K\r" + (f"\033[1;32m{prefix}\033[0m " if prefix else ""))
                                sys.stdout.flush()
                            first = False
                            if speed_test and show_stats:
                                speed_test.start()
                        print(content, end="", flush=True)
                        acc.append(content)
                        if speed_test and show_stats:
                            speed_test.count_token(content)
                except Exception:
                    pass
            print("")
            if speed_test and show_stats:
                speed_test.end()

            ans_text = "".join(acc)
            in_est = (len(body.get("input", "")) + len(body.get("system_instruction", ""))) // 4
            ctx_est = (sum(len(m.get("content", "")) for m in messages) + len(ans_text)) // 4
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


# --- ACTIVE WORKSPACE EDITING AGENT RULES ---
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
    """Canonicalizes target paths safely to evaluate directories."""
    root = os.path.realpath(workspace)
    return os.path.realpath(os.path.join(root, os.path.expanduser(p or "")))


def _is_outside_workspace(workspace: str, full_path: str) -> bool:
    """Verifies if a specific path boundary is outside your allowed project workspace."""
    root = os.path.realpath(workspace)
    return full_path != root and not full_path.startswith(root + os.sep)


def _run_edit_tool(name: str, args: dict, workspace: str, spinner=None) -> str:
    """Runs a single local filesystem tool, evaluating security gating profiles."""
    import subprocess
    gates_active = os.environ.get("AI_CONFIRM_GATES", "1") == "1"

    if name == "read_file":
        full = _safe_path(workspace, args.get("path", ""))
        outside = _is_outside_workspace(workspace, full)
        
        # Hard Security: Always prompt if requesting items outside active projects
        if outside or gates_active:
            reason = f"read {full} (OUTSIDE workspace)" if outside else f"read file {args.get('path')}"
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
        
        # Local Syntactic Guardrail: Verify Python syntax before committing writes
        if full.endswith(".py"):
            import ast
            try:
                ast.parse(content)
            except SyntaxError as e:
                return f"[error] Write blocked. Python syntax verification failed: {e.msg} on line {e.lineno}. Please correct this syntax error and try writing again."
                
        # Local Syntactic Guardrail: Verify JSON formatting before committing writes
        if full.endswith(".json"):
            try:
                json.loads(content)
            except Exception as e:
                return f"[error] Write blocked. JSON validation failed: {e}. Please correct the JSON formatting and try writing again."

        # Colorized Unified Terminal Diff Output
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

        # Confirm before writes
        if outside or gates_active:
            verb = "overwrite" if exists else "create"
            where = f"{full} (OUTSIDE workspace)" if outside else args.get("path")
            reason = f"{verb} {where} ({len(content)} chars)"
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
            if not ui.confirm_tool(f"execute: $ {cmd}"):
                return "[denied] user rejected command execution"
        else:
            sys.stderr.write(f"\033[2m  Executing command autonomously: $ {cmd}\033[0m\n")

        # Standard login shell to load developer environment profiles
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
    """Executes a multi-turn non-streaming agent round-trip loop supporting tool evaluations."""
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    
    # Inject workspace agent configurations to active system instructions in-place
    if messages and messages[0]["role"] == "system":
        if "### EDIT MODE" not in messages[0]["content"]:
            messages[0]["content"] += EDIT_SYSTEM_ADD.format(ws=workspace)
            messages[0]["content"] += TOOLS_SYSTEM_ADD.format(
                names="read_file, write_file, list_dir, run_command", ws=workspace)
            
    resolved_model = None
    for _round in range(10):
        body_tools = dict(body)
        body_tools["messages"] = messages  # CRUCIAL: Send mutated conversation thread containing tool answers
        body_tools["stream"] = False      # Multi-turn tool execution operates in non-streaming batch mode
        body_tools["tools"] = _EDIT_TOOLS
        
        spinner.start()
        # Record start time to calculate network latency and t/s metrics
        start_time = time.time()
        try:
            # Reuses the warm pooled _session connection to bypass socket handshake latency
            res = _session.post(
                url,
                json=body_tools,
                headers={"Content-Type": "application/json", **headers},
                timeout=timeout
            )
            resp = res.json()
        except Exception as e:
            sys.stderr.write(f"\033[90m[sys] API response error: {e}\033[0m\n")
            return None
        finally:
            spinner.stop()
            
        elapsed_time = time.time() - start_time
        resolved_model = resp.get("model") or resolved_model
        choices = resp.get("choices") or [{}]
        msg = choices[0].get("message") or {}
        calls = msg.get("tool_calls")
        
        # If no tool calls are returned, agent processing is complete
        if not calls:
            ans = msg.get("content") or ""
            if sys.stdout.isatty():
                sys.stdout.write("\r\x1b[2K\rAgent: ")
            print(ans)
            
            # Print calculated speed and latency metrics for the final workspace completion turn
            prompt_chars = sum(len(m.get("content", "")) for m in messages)
            in_tok = prompt_chars // 4
            out_tok = len(ans) // 4
            
            # Extract server-side generation timings if returned by llama-server
            timings = resp.get("timings") or {}
            pred_ms = timings.get("predicted_ms")
            if pred_ms and isinstance(pred_ms, (int, float)):
                generation_time = pred_ms / 1000.0
            else:
                generation_time = elapsed_time
            
            if show_stats and sys.stdout.isatty():
                tps = out_tok / generation_time if generation_time > 0 else 0
                sys.stdout.write(f"\033[90m [{out_tok} tokens | {generation_time:.2f}s | {tps:.2f} t/s]\033[0m\n")
                sys.stdout.flush()
            
            # Log and display token and context metrics for the workspace turn
            _log_turn_usage(resolved_model or body.get("model") or "local-model",
                            in_tok, out_tok, 0.0, show_stats, in_tok + out_tok)
            
            return ans
            
        # Append the assistant's intent to use tools
        messages.append(msg)
        
        for tc in calls:
            fname = tc.get("function", {}).get("name", "")
            try:
                args = json.loads(tc.get("function", {}).get("arguments") or "{}")
            except Exception:
                args = {}
                
            brief = str(args.get("path") or args.get("command") or "")[:100]
            verb = TOOL_VERBS.get(fname, "working")
            print(f"\033[2m∗ {verb} · {fname} {brief}\033[0m")
            
            if spinner and fname in ("read_file", "list_dir"):
                spinner.start(verb)
            try:
                result = _run_edit_tool(fname, args, workspace, spinner)
            except Exception as e:
                result = f"[tool error] {e}"
            finally:
                if spinner:
                    spinner.stop()
                    
            # Record the tool output so the model sees the execution result in its next loop iteration
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "name": fname,
                "content": result
            })
            
    return None


def stream_response(messages: list, prefix: str = "AI: ", cfg_dir: str = "", show_stats: bool = False, thinking_budget: int = 0, is_agent: bool = False) -> str or None:
    acc = []
    spinner = ui.InlineSpinner()
    try:
        # Load API connections dynamically from the external cloud mapping module
        configs = agent_cloud.get_active_configs(messages)

        # Set up local model payload with universal template reasoning overrides
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
        
        # Append the local endpoint to the bottom of the execution order list
        configs.append(("http://localhost:8080/v1/chat/completions", {}, local_body, 180))

        for url, headers, body, timeout in configs:
            # If running as active agentic workspace session, route through multi-round tool execution loop
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
                        for line in response:
                            if not line.startswith(b"data:"):
                                continue
                            
                            content = extract_stream_content(line)
                            if content:
                                if first:
                                    spinner.stop()
                                    if sys.stdout.isatty():
                                        sys.stdout.write("\r\x1b[2K\r" + (f"\033[1;32m{prefix}\033[0m " if prefix else ""))
                                        sys.stdout.flush()
                                    first = False
                                    if speed_test and show_stats:
                                        speed_test.start()
                                print(content, end="", flush=True)
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
                        print("")
                        if speed_test and show_stats:
                            speed_test.end()
                        
                        ans_text = "".join(acc)
                        prompt_chars = sum(len(m.get("content", "")) for m in messages)
                        in_tok = prompt_chars // 4
                        out_tok = len(ans_text) // 4
                        
                        # Process daily billing ledger calculations
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
        try: spinner.stop()
        except Exception: pass
        sys.stderr.write("\n\r\x1b[2K\r[sys] Interrupted.\n")
        sys.stderr.flush()
        return "".join(acc) if 'acc' in locals() else None
    return None


def get_accurate_token_count(text: str, server_url: str = "http://localhost:8080") -> int:
    try:
        # Use the pooled _session object to drastically reduce connection handshake latency
        res = _session.post(f"{server_url}/tokenize", json={"content": text}, timeout=3)
        return len(res.json().get("tokens", []))
    except Exception:
        return len(text) // 4


def show_memory_status(messages: list, max_context: int = 8192, server_url: str = "http://localhost:8080") -> None:
    total_toks = sum(get_accurate_token_count(m.get("content", ""), server_url) for m in messages)
    pct = (total_toks / max_context) * 100
    bar_len = 20
    filled = int((total_toks / max_context) * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    sys.stderr.write(f"\n\033[2m[sys] Context Window: {total_toks}/{max_context} tokens\033[0m\n")
    sys.stderr.write(f"\033[2m[sys] Usage: [{bar}] {pct:.1f}%\033[0m\n")
    sys.stderr.write(f"\033[2m[sys] Remaining: {max_context - total_toks} tokens\033[0m\n\n")
    sys.stderr.flush()
    
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
