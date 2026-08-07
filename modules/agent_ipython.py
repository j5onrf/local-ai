#!/usr/bin/env python3
"""Local-AI Standalone IPython Kernel & RLM Harness Module"""

import ast, contextlib, io, json, os, sys, subprocess, traceback
from typing import Dict, Any, List, Optional, Tuple, Callable

CFG_DIR = os.path.expanduser("~/.config/local-ai")

try:
    import agent_core as core
except ImportError:
    core = None

_shell_globals: Dict[str, Any] = {}
_shell_instance = None

try:
    from IPython.core.interactiveshell import InteractiveShell
    _has_ipython = True
except ImportError:
    _has_ipython = False


def is_ipython_enabled() -> bool:
    return core.get_state().get("ipython_mode", False) if core else False


def toggle_ipython_mode(enable: Optional[bool] = None) -> bool:
    new_st = (not is_ipython_enabled()) if enable is None else enable
    if core: core.save_state("ipython_mode", new_st)
    return new_st


def _init_kernel_sdk(workspace: str) -> None:
    global _shell_globals, _shell_instance
    if workspace not in sys.path:
        sys.path.insert(0, workspace)

    if _has_ipython and _shell_instance is None:
        _shell_instance = InteractiveShell.instance()

    if "read_file" in _shell_globals: return

    def _read_file(path: str) -> str:
        full = os.path.realpath(path if os.path.isabs(path) else os.path.join(workspace, path))
        with open(full, "r", encoding="utf-8", errors="replace") as f: return f.read()

    def _write_file(path: str, content: str) -> str:
        full = os.path.realpath(path if os.path.isabs(path) else os.path.join(workspace, path))
        os.makedirs(os.path.dirname(full) or workspace, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f: f.write(content)
        return f"wrote {len(content)} chars to {path}"

    def _list_dir(path: str = ".") -> List[str]:
        full = os.path.realpath(path if os.path.isabs(path) else os.path.join(workspace, path))
        return sorted(os.listdir(full))

    def _run_command(cmd: str) -> str:
        res = subprocess.run(cmd, shell=True, cwd=workspace, capture_output=True, text=True, timeout=120)
        return ((res.stdout or "") + ("\n" + res.stderr if res.stderr else "")).strip()

    def _read_symbol(sym: str) -> str:
        mod_path = os.path.join(CFG_DIR, "tools", "map", "index-map")
        res = subprocess.run([sys.executable, mod_path, "snippet", sym], cwd=workspace, capture_output=True, text=True, timeout=10)
        return (res.stdout or res.stderr or "").strip()

    sdk = {
        "read_file": _read_file, "write_file": _write_file, "list_dir": _list_dir,
        "run_command": _run_command, "read_symbol": _read_symbol, "workspace": workspace
    }
    _shell_globals.update(sdk)
    if _shell_instance:
        _shell_instance.user_ns.update(sdk)


def inspect_ast_safety(code: str, workspace: str, confirm_gate_fn: Optional[Callable[[str], bool]] = None) -> Optional[str]:
    if not confirm_gate_fn or os.environ.get("AI_CONFIRM_GATES", "1") == "0": return None
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn_name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
                if fn_name in ("run_command", "system", "Popen", "exec", "eval", "remove", "rmtree"):
                    if not confirm_gate_fn(f"PYTHON KERNEL: {fn_name}() cell execution"):
                        return "[denied] Execution halted by user gate."
    except SyntaxError as e:
        return f"[error] Python syntax error in code cell: {e}"
    return None


def run_cell(code: str, workspace: str, confirm_gate_fn: Optional[Callable[[str], bool]] = None) -> str:
    _init_kernel_sdk(workspace)
    if denial := inspect_ast_safety(code, workspace, confirm_gate_fn):
        return denial

    stdout_buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stdout_buf):
            if _shell_instance:
                res = _shell_instance.run_cell(code, store_history=True)
                if res.error_in_exec:
                    traceback.print_exception(type(res.error_in_exec), res.error_in_exec, res.error_in_exec.__traceback__)
            else:
                exec(code, _shell_globals)
        out = stdout_buf.getvalue().strip()
        return (out[:1200] + f"\n... [Snipped {len(out)-1200} chars]") if len(out) > 1500 else (out or "(Cell executed successfully with no output)")
    except Exception as e:
        return f"[error] Cell execution failed: {e}\n{traceback.format_exc()}"


IPYTHON_TOOL = [{
    "type": "function",
    "function": {
        "name": "exec_python",
        "description": "Execute Python code in the live persistent kernel. Data, variables, and imports stay in memory across cells.",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code cell to execute."}},
            "required": ["code"]
        }
    }
}]


def get_active_tools() -> List[Dict[str, Any]]:
    return IPYTHON_TOOL if is_ipython_enabled() else getattr(core, "EDIT_TOOLS", [])
