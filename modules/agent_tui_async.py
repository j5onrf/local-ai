#!/usr/bin/env python3
# File: ~/.config/local-ai/modules/agent_tui_async.py
"""Asynchronous uvloop background services for Local-AI Agent TUI."""

import asyncio
import json
import os

async def run_async_cmd(cmd: list[str], cwd: str) -> str:
    """Non-blocking async subprocess executor leveraging libuv C pipes."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await proc.communicate()
        return (stdout or stderr).decode("utf-8", errors="ignore").strip()
    except Exception as e:
        return f"Async command error: {e}"

async def watch_workspace_changes(app) -> None:
    """Async background task watching workspace file changes via uvloop libuv event loop."""
    tpm_file = os.path.join(app.workspace_path, ".agent", "tpm.md")
    last_mtime = os.path.getmtime(tpm_file) if os.path.exists(tpm_file) else 0

    while True:
        await asyncio.sleep(1.5)
        if os.path.exists(tpm_file):
            try:
                mtime = os.path.getmtime(tpm_file)
                if mtime > last_mtime:
                    last_mtime = mtime
                    app.refresh_db_counts()
                    if hasattr(app, "lbl_database"):
                        app.lbl_database.update(f"[dim]DB State[/dim]  {app.get_db_status_string()}")
                    app.notify("[dim]Memory facts updated from disk.[/dim]", sys_prefix=False)
            except Exception:
                pass

async def start_subagent_ipc_hub(app) -> None:
    """Unix Domain Socket IPC hub running on uvloop for multi-terminal sub-agent tracking."""
    sock_path = f"/tmp/local-ai-{app.safe_name}.sock"
    if os.path.exists(sock_path):
        try:
            os.remove(sock_path)
        except Exception:
            pass

    async def handle_subagent_msg(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            data = await reader.read(1024)
            if data:
                payload = json.loads(data.decode("utf-8"))
                sub_id = payload.get("sub_id", "Sub-agent")
                status = payload.get("status", "Active")
                app.notify(f"[dim]⚡ [bold cyan]{sub_id}[/bold cyan]: {status}[/dim]", sys_prefix=False)
        except Exception:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    try:
        server = await asyncio.start_unix_server(handle_subagent_msg, path=sock_path)
        async with server:
            await server.serve_forever()
    except Exception:
        pass
