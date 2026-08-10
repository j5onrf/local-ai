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


_orig_open = open
_orig_listdir = os.listdir
_orig_scandir = os.scandir
_confirm_gate_fn = None

def _init_kernel_sdk(workspace: str, confirm_gate_fn: Optional[Callable[[str], bool]] = None) -> None:
    global _shell_globals, _shell_instance, _confirm_gate_fn
    if confirm_gate_fn:
        _confirm_gate_fn = confirm_gate_fn
    ws_real = os.path.realpath(workspace)
    
    # 1. Force working directory to workspace
    try: os.chdir(ws_real)
    except OSError: pass

    if ws_real not in sys.path:
        sys.path.insert(0, ws_real)

    if _has_ipython and _shell_instance is None:
        _shell_instance = InteractiveShell.instance()

    def _is_outside(path_str: str) -> bool:
        full = os.path.realpath(path_str if os.path.isabs(path_str) else os.path.join(ws_real, path_str))
        return full != ws_real and not full.startswith(ws_real + os.sep)

    def _check_boundary(path_str: str, op_name: str) -> bool:
        full = os.path.realpath(path_str if os.path.isabs(path_str) else os.path.join(ws_real, path_str))
        if _is_outside(full):
            if _confirm_gate_fn:
                return _confirm_gate_fn(f"OUT-OF-BOUNDS KERNEL {op_name}: {full}")
            import agent_core as core
            return core._confirm_gate(f"OUT-OF-BOUNDS KERNEL {op_name}: {full}", None)
        return True

    # 2. Zero-Trust Overrides for raw Python built-ins inside REPL
    def safe_open(file, mode='r', *args, **kwargs):
        if isinstance(file, (str, bytes, os.PathLike)):
            if not _check_boundary(str(file), "READ" if 'r' in mode else "WRITE"):
                raise PermissionError(f"[denied] Out-of-bounds access blocked: {file}")
        return _orig_open(file, mode, *args, **kwargs)

    def safe_listdir(path='.'):
        if not _check_boundary(str(path), "LIST DIR"):
            raise PermissionError(f"[denied] Out-of-bounds list_dir blocked: {path}")
        full = os.path.realpath(str(path) if os.path.isabs(str(path)) else os.path.join(ws_real, str(path)))
        return _orig_listdir(full)

    def _read_file(path: str) -> str:
        if not _check_boundary(path, "READ"): return "[denied] Out-of-bounds read blocked."
        full = os.path.realpath(path if os.path.isabs(path) else os.path.join(ws_real, path))
        with _orig_open(full, "r", encoding="utf-8", errors="replace") as f: return f.read()

    def _write_file(path: str, content: str) -> str:
        if not _check_boundary(path, "WRITE"): return "[denied] Out-of-bounds write blocked."
        full = os.path.realpath(path if os.path.isabs(path) else os.path.join(ws_real, path))
        os.makedirs(os.path.dirname(full) or ws_real, exist_ok=True)
        with _orig_open(full, "w", encoding="utf-8") as f: f.write(content)
        return f"wrote {len(content)} chars to {path}"

    def _list_dir(path: str = ".") -> List[str]:
        if not _check_boundary(path, "LIST DIR"): return ["[denied] Out-of-bounds list_dir blocked."]
        full = os.path.realpath(path if os.path.isabs(path) else os.path.join(ws_real, path))
        return sorted(_orig_listdir(full))

    def _run_command(cmd: str) -> str:
        res = subprocess.run(cmd, shell=True, cwd=ws_real, capture_output=True, text=True, timeout=120)
        return ((res.stdout or "") + ("\n" + res.stderr if res.stderr else "")).strip()

    def _read_symbol(sym: str) -> str:
        mod_path = os.path.join(CFG_DIR, "tools", "map", "index-map")
        res = subprocess.run([sys.executable, mod_path, "snippet", sym], cwd=ws_real, capture_output=True, text=True, timeout=10)
        return (res.stdout or res.stderr or "").strip()

    def _trace_symbol(sym: str) -> str:
        mod_path = os.path.join(CFG_DIR, "tools", "map", "index-map")
        res = subprocess.run([sys.executable, mod_path, "trace", sym], cwd=ws_real, capture_output=True, text=True, timeout=10)
        return (res.stdout or res.stderr or "").strip()

    def _blast_radius(sym: str) -> str:
        mod_path = os.path.join(CFG_DIR, "tools", "map", "index-map")
        res = subprocess.run([sys.executable, mod_path, "blast-radius", sym], cwd=ws_real, capture_output=True, text=True, timeout=10)
        return (res.stdout or res.stderr or "").strip()

    def _find_symbol(pat: str) -> str:
        mod_path = os.path.join(CFG_DIR, "tools", "map", "index-map")
        res = subprocess.run([sys.executable, mod_path, "search", pat], cwd=ws_real, capture_output=True, text=True, timeout=10)
        return (res.stdout or res.stderr or "").strip()

    def _architecture_overview() -> str:
        mod_path = os.path.join(CFG_DIR, "tools", "map", "index-map")
        res = subprocess.run([sys.executable, mod_path, "architecture"], cwd=ws_real, capture_output=True, text=True, timeout=10)
        return (res.stdout or res.stderr or "").strip()

    sdk = {
        "open": safe_open, "read_file": _read_file, "write_file": _write_file, "list_dir": _list_dir,
        "run_command": _run_command, "read_symbol": _read_symbol, "trace_symbol": _trace_symbol,
        "blast_radius": _blast_radius, "find_symbol": _find_symbol,
        "architecture_overview": _architecture_overview, "workspace": ws_real
    }
    _shell_globals.update(sdk)
    os.listdir = safe_listdir
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
    _init_kernel_sdk(workspace, confirm_gate_fn)
    if denial := inspect_ast_safety(code, workspace, confirm_gate_fn):
        return denial

    stdout_buf = io.StringIO()
    eval_result = None
    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stdout_buf):
            if _shell_instance:
                res = _shell_instance.run_cell(code, store_history=True)
                if res.error_in_exec:
                    traceback.print_exception(type(res.error_in_exec), res.error_in_exec, res.error_in_exec.__traceback__)
                elif hasattr(res, "result") and res.result is not None:
                    eval_result = res.result
            else:
                try:
                    eval_result = eval(code, _shell_globals)
                except SyntaxError:
                    exec(code, _shell_globals)

        out = stdout_buf.getvalue().strip()
        if not out and eval_result is not None:
            out = str(eval_result).strip()
        return (out[:1200] + f"\n... [Snipped {len(out)-1200} chars]") if len(out) > 1500 else (out or "(Cell executed successfully with no output)")
    except PermissionError as e:
        return f"[denied] {e}"
    except Exception as e:
        err_msg = str(e).strip().split("\n")[0]
        return f"[error] Cell execution failed: {err_msg}"


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
