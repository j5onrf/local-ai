#!/usr/bin/env python3
"""Ralph Wiggum Autonomous Loop Engine"""

import os, sys
CFG_DIR = os.path.expanduser("~/.config/local-ai")
sys.path.append(os.path.join(CFG_DIR, "modules"))
import agent_core as core

def run_loop(task: str, max_turns: int = 10) -> None:
    workspace = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    spec = os.path.join(workspace, "TASK.md")
    if not task and os.path.exists(spec):
        try:
            with open(spec, "r", encoding="utf-8") as f:
                task = f.read().strip()
        except Exception: pass

    if not task:
        sys.stderr.write("[error] Usage: /task \"<description>\" or create TASK.md in workspace\n")
        return

    sys.stderr.write(f"\033[1;36m[loop]\033[0m Running task loop in {workspace}...\n")
    history = [
        {"role": "system", "content": f"You are an autonomous developer agent at {workspace}.\nExecute the goal step-by-step using tools. When finished, output 'TASK COMPLETE' on a line by itself."},
        {"role": "user", "content": f"### GOAL:\n{task}"}
    ]

    turn = 0
    while turn < max_turns:
        turn += 1
        sys.stderr.write(f"\033[1;33m[loop turn {turn}/{max_turns}]\033[0m\n")
        ans = core.stream_response(history, prefix="Agent:", show_stats=True, is_agent=True)
        if not ans: break
        if "TASK COMPLETE" in ans:
            sys.stderr.write("\033[1;32m[ok] Task complete!\033[0m\n")
            break

if __name__ == "__main__":
    task_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    turns_arg = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 10
    run_loop(task_arg, max_turns=turns_arg)
