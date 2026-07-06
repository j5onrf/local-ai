#!/usr/bin/env python3
# Local-Ai Agent [j5onrf] [v0.8.9.19]

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request as urlreq

# Configuration constants
CFG_DIR = os.path.expanduser("~/.config/local-ai")
CONTEXT_FILE = os.path.join(CFG_DIR, "ai-context.md")
SKILLS_DIR = os.path.join(CFG_DIR, "skills")
SESSIONS_DIR = os.path.join(CFG_DIR, "projects", "database")
BASE_PROMPT = (
    "Read-only local shell assistant.\n"
    "If <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n"
    "Write full, natural sentences without markdown, headers, bolding, or lists.\n\n"
)


def load_env_file(env_path: str) -> None:
    """Reads a local .env file and dynamically loads keys into os.environ if present."""
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("=", 1)
                if len(parts) == 2:
                    key, val = parts[0].strip(), parts[1].strip()
                    # Strip surrounding quotes if present
                    if val.startswith(('"', "'")) and val.endswith(('"', "'")):
                        val = val[1:-1]
                    os.environ[key] = val
    except Exception:
        pass


# Dynamically load the keys into your environment at runtime
load_env_file(os.path.join(CFG_DIR, ".env"))

# Bootstrap custom local modules path
sys.path.append(os.path.join(CFG_DIR, "modules"))

try:
    import readline

    readline.parse_and_bind(r'"\e[A": previous-history')
    readline.parse_and_bind(r'"\e[B": next-history')
except ImportError:
    pass

# Load consolidated core library functions under a single unified namespace
try:
    import agent_context as context
    import agent_core as core
    import agent_skills as skills
    import agent_spell as spell
    import agent_ui as ui
except ImportError as e:
    sys.stderr.write(f"\033[1;31m[CRITICAL]: Failed to load modules: {e}\033[0m\n")
    sys.exit(1)

STOP_WORDS = {
    "is",
    "what",
    "it",
    "do",
    "any",
    "i",
    "have",
    "the",
    "a",
    "an",
    "on",
    "to",
    "for",
    "me",
    "you",
    "my",
    "your",
    "we",
    "us",
    "are",
    "about",
    "in",
    "how",
}


def sync_md_to_sqlite(workspace: str, workspace_path: str) -> None:
    """Parses manual edits from .agent/tpm.md back into SQLite on startup."""
    md_path = os.path.join(workspace_path, ".agent", "tpm.md")
    if not os.path.exists(md_path):
        return
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        matches = re.findall(r"\*\s+\*\*([^*]+)\*\*:\s*(.*)", content)
        if not matches:
            return
        reconciled = {k.strip().lower(): v.strip() for k, v in matches}
        if reconciled:
            # Syncs manual human edits directly back into the SQLite DB
            subprocess.run(
                [
                    sys.executable,
                    os.path.join(CFG_DIR, "modules", "ai-agent-memories"),
                    "tpm-reconcile",
                    workspace,
                ],
                input=json.dumps(reconciled),
                text=True,
                capture_output=True,
            )
    except Exception:
        pass


def background_tpm_update(
    user_msg: str, assistant_msg: str, workspace: str, workspace_path: str
):
    """Asynchronously extracts, reconciles, and commits user facts to SQLite and tpm.md."""
    cleaned = user_msg.lower().strip()
    if len(cleaned) < 8 or cleaned in (
        "hello",
        "hi",
        "hey",
        "exit",
        "quit",
        "q",
        "/clear",
        "/reset",
        "/stats",
        "/tok",
        "/m",
    ):
        return
    try:
        import sqlite3
        from contextlib import closing

        db_path = os.path.join(SESSIONS_DIR, f"{workspace}.db")
        existing_facts = ""
        if os.path.exists(db_path):
            with closing(sqlite3.connect(db_path, timeout=5)) as conn:
                cur = conn.cursor()
                cur.execute("SELECT key, value FROM tpm_memories")
                rows = cur.fetchall()
                if rows:
                    existing_facts = "\n".join(f"* {k}: {v}" for k, v in rows)

        system_prompt = (
            "You are an asynchronous memory compiler. Analyze the latest user message and assistant response.\n"
            "Extract any new facts, occupations, locations, style preferences, or software tool configurations the user explicitly shared.\n"
            'Output ONLY a flat JSON object of the updated key-value pairs (e.g., {"editor": "Zed", "role": "CEO"}).\n'
            "If a fact contradicts or updates an existing fact in the memory profile, override it with the new value.\n"
            "Do not include markdown, explanations, or code blocks. Output '{}' if no new facts or updates are found."
        )

        user_prompt = (
            f"### Existing Memory Profile:\n{existing_facts or 'None'}\n\n"
            f"### Latest Turn:\nUser: {user_msg}\nAssistant: {assistant_msg}\n\n"
            f"Identify and reconcile any updates. Output JSON:"
        )

        # Call local llama-server directly with a fast, non-reasoning background payload
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "thinking_budget_tokens": 0,  # Turn off thinking for maximum background speed
            "stream": False,
        }

        req = urlreq.Request(
            "http://localhost:8080/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlreq.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            llm_out = res_data["choices"][0]["message"].get("content", "").strip()

        llm_out = re.sub(
            r"^```json\s*|\s*```$", "", llm_out, flags=re.IGNORECASE
        ).strip()
        parsed_json = json.loads(llm_out)

        if parsed_json and isinstance(parsed_json, dict):
            # Commit to SQLite
            subprocess.run(
                [
                    sys.executable,
                    f"{CFG_DIR}/modules/ai-agent-memories",
                    "tpm-reconcile",
                    workspace,
                ],
                input=json.dumps(parsed_json),
                text=True,
                capture_output=True,
            )
            # Sync directly out to your local human-readable tpm.md flat file
            res_get = subprocess.run(
                [
                    sys.executable,
                    f"{CFG_DIR}/modules/ai-agent-memories",
                    "tpm-get",
                    workspace,
                ],
                capture_output=True,
                text=True,
            )
            if res_get.stdout.strip():
                md_dir = os.path.join(workspace_path, ".agent")
                os.makedirs(md_dir, exist_ok=True)
                with open(os.path.join(md_dir, "tpm.md"), "w", encoding="utf-8") as mdf:
                    mdf.write(res_get.stdout.strip() + "\n")
    except Exception:
        pass


# Helper to stream and count tokens for the speed-test
def stream_llm_response(
    messages: list, prefix: str = "AI: ", show_stats: bool = True
) -> str or None:
    return core.stream_response(messages, prefix, CFG_DIR, show_stats)


def run_interactive_chat(args: list):
    is_agent = args[0] == "--talk-chat"
    skills_list = []
    active_skill = os.environ.get("AI_ACTIVE_SKILL")
    if active_skill:
        skills_list.extend([s.lstrip("-").lower() for s in active_skill.split()])
    for arg in args:
        if arg.startswith("-") and arg not in ("--talk", "--talk-chat"):
            skills_list.append(arg.lstrip("-").lower())
    skills_list = list(dict.fromkeys(skills_list))

    skill_content = skills.load_skill_content(
        " ".join(skills_list), SKILLS_DIR, CFG_DIR
    )
    active_system_prompt = (
        skill_content
        if (is_agent and skill_content)
        else (
            BASE_PROMPT
            + (
                f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n"
                if skill_content
                else ""
            )
        )
    )

    workspace_path = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    home_dir = os.path.expanduser("~")
    safe_name = (
        workspace_path[len(home_dir) :].lstrip("/")
        if workspace_path.startswith(home_dir)
        else workspace_path
    )
    safe_name = safe_name.replace("/", "-").strip("-") or "home"

    chat_history = [{"role": "system", "content": active_system_prompt}]
    pending_query = " ".join(args[1:]) if len(args) > 1 else None
    clean_name = " ".join(skills_list)

    spell_active = not is_agent
    memory_active = True
    show_stats = True  # Keeps stats enabled by default inside chat sessions

    # Unify memory sync: Synchronize manual human edits from tpm.md back into SQLite
    if is_agent:
        sync_md_to_sqlite(safe_name, workspace_path)

    db_turns = 0
    tpm_count = 0
    if is_agent:
        try:
            res = subprocess.run(
                [
                    sys.executable,
                    f"{CFG_DIR}/modules/ai-agent-sessions",
                    "get-count",
                    safe_name,
                ],
                capture_output=True,
                text=True,
            )
            db_turns = int(res.stdout.strip())
        except Exception:
            pass
        try:
            # Query the database to retrieve the count of active compiled facts
            res_tpm = subprocess.run(
                [
                    sys.executable,
                    f"{CFG_DIR}/modules/ai-agent-memories",
                    "get-tpm-count",
                    safe_name,
                ],
                capture_output=True,
                text=True,
            )
            tpm_count = int(res_tpm.stdout.strip())
        except Exception:
            pass

    ui.draw_session_box(
        workspace_path,
        home_dir,
        is_agent,
        db_turns,
        tpm_count,
        memory_active,
        active_system_prompt,
        clean_name,
    )

    try:
        while True:
            if pending_query:
                query, pending_query = pending_query, None
            else:
                try:
                    query = input("\x01\033[1;30m\x02❯\x01\033[0m\x02 ").strip()
                except EOFError:
                    break
                finally:
                    try:
                        readline.set_startup_hook(None)
                    except Exception:
                        pass
                if not query:
                    continue
                if query.lower() in ("exit", "quit", "q"):
                    print("\r\033[1;33mExiting conversation.\033[0m")
                    sys.exit(0)
                if query in ("/d", "/e"):
                    spell_active = query == "/e"
                    print(
                        f"\033[1;33m[sys] Spellchecker {'enabled' if spell_active else 'disabled'}.\033[0m\n"
                    )
                    continue

                # --- UNIFIED MEMORY LAYER TOGGLE (/m) ---
                if query == "/m":
                    memory_active = not memory_active
                    print(
                        f"\033[1;33m[sys] Long-term memory and TPM reconciliation {'enabled' if memory_active else 'disabled'}.\033[0m\n"
                    )
                    continue

                # --- STATS ON-DEMAND TOGGLE ---
                if query == "/stats":
                    show_stats = not show_stats
                    print(
                        f"\033[1;33m[sys] Generation statistics {'enabled' if show_stats else 'disabled'}.\033[0m\n"
                    )
                    continue

                # --- NATIVE FULL SESSION CLEAR ---
                if query.lower() in ("/clear", "/reset"):
                    # 1. Clear local Python history array and pre-fill the startup greeting to prevent loops
                    chat_history = [
                        {"role": "system", "content": active_system_prompt},
                        {
                            "role": "assistant",
                            "content": "Agent: Workspace loaded. Awaiting instructions.",
                        },
                    ]

                    # 2. Clear Google/Cloud session by deleting session.json
                    try:
                        sf = os.path.join(workspace_path, ".agent", "session.json")
                        if os.path.exists(sf):
                            os.remove(sf)
                        md_file = os.path.join(workspace_path, ".agent", "tpm.md")
                        if os.path.exists(md_file):
                            os.remove(md_file)
                        # Delete the physical workspace history file as well
                        hist_file = os.path.join(workspace_path, "history.md")
                        if os.path.exists(hist_file):
                            os.remove(hist_file)
                    except Exception:
                        pass

                    # 3. Clear both semantic turns and the compiled TPM facts table in SQLite
                    try:
                        subprocess.run(
                            [
                                sys.executable,
                                f"{CFG_DIR}/modules/ai-agent-sessions",
                                "clear",
                                safe_name,
                            ],
                            capture_output=True,
                        )
                        subprocess.run(
                            [
                                sys.executable,
                                f"{CFG_DIR}/modules/ai-agent-memories",
                                "tpm-clear",
                                safe_name,
                            ],
                            capture_output=True,
                        )
                    except Exception:
                        pass

                    print(
                        "\033[1;32m[sys] Conversation history, cloud session, and local TPM memory cleared.\033[0m\n"
                    )
                    continue

                if query == "/tok":
                    subprocess.run(
                        [
                            sys.executable,
                            f"{CFG_DIR}/modules/ai-agent-sessions",
                            "show-tok",
                        ],
                        input=json.dumps(chat_history),
                        text=True,
                    )
                    continue
                if spell_active and not query.startswith(("/", "-", "#", "```")):
                    action, query = spell.check_query_spelling(query, ui.get_key)
                    if action == "EDIT":
                        try:
                            readline.set_startup_hook(
                                lambda: readline.insert_text(query)
                            )
                        except Exception:
                            pass
                        continue
                    elif action == "DISABLE":
                        spell_active = False

            if query.startswith(("/skill", "/s")) or query.startswith(
                ("/skill ", "/s ")
            ):
                res = subprocess.run(
                    [
                        sys.executable,
                        f"{CFG_DIR}/modules/agent_skills.py",
                        safe_name,
                        query,
                    ],
                    input=json.dumps(chat_history),
                    stdout=subprocess.PIPE,
                    text=True,
                )
                if res.stdout.strip():
                    try:
                        chat_history = json.loads(res.stdout.strip())
                    except Exception as e:
                        print(f"Error loading session: {e}")
                continue
            if query.startswith("-save"):
                subprocess.run(
                    [
                        sys.executable,
                        f"{CFG_DIR}/modules/ai-agent-sessions",
                        "save",
                        safe_name,
                        query.replace("-save", "").strip(),
                    ],
                    input=json.dumps(chat_history),
                    text=True,
                )
                continue
            if query in ("-load", "-timeline"):
                res = subprocess.run(
                    [
                        sys.executable,
                        f"{CFG_DIR}/modules/ai-agent-sessions",
                        "load",
                        safe_name,
                    ],
                    stdin=sys.stdin,
                    stdout=subprocess.PIPE,
                    text=True,
                )
                if res.stdout.strip():
                    try:
                        chat_history = json.loads(res.stdout.strip())
                        print(
                            f"\033[1;32m[session-mgr] Restored session ({len(chat_history) - 1} turns loaded).\033[0m\n"
                        )
                    except Exception as e:
                        print(f"Error loading session: {e}")
                else:
                    print(f"\033[1;31m[session-mgr] Load aborted.\033[0m\n")
                    continue

            past_memory = ""
            tpm_context = ""
            is_init_map = (
                query.startswith(("#", "[", "{"))
                or "\n" in query
                or "last_interaction_id" in query
                or "index-map" in query
            )
            if is_agent and memory_active and not is_init_map:
                # 1. Fetch semantic semantic memory
                res = subprocess.run(
                    [
                        sys.executable,
                        f"{CFG_DIR}/modules/ai-agent-memories",
                        "get-context",
                        safe_name,
                        query,
                    ],
                    stdout=subprocess.PIPE,
                    text=True,
                )
                if res.returncode == 2:
                    pending_query = None
                    continue
                if res.returncode == 3:
                    memory_active = False
                past_memory = res.stdout.strip()

                # 2. Fetch compiled, resolved Temporal Personality Memory (TPM)
                res_tpm = subprocess.run(
                    [
                        sys.executable,
                        f"{CFG_DIR}/modules/ai-agent-memories",
                        "tpm-get",
                        safe_name,
                    ],
                    stdout=subprocess.PIPE,
                    text=True,
                )
                tpm_context = res_tpm.stdout.strip()

            if re.match(r"^/?([ftba])(?:\s+(\d+))?$", query.lower()):
                think_bin = f"{CFG_DIR}/modules/chat"
                if os.path.exists(think_bin):
                    try:
                        subprocess.run(
                            [sys.executable, think_bin, query],
                            input=json.dumps(chat_history),
                            text=True,
                        )
                        continue
                    except Exception as e:
                        sys.stderr.write(
                            f"\033[1;31m[Warning] chat failed: {e}\033[0m\n"
                        )
                        continue
                else:
                    sys.stderr.write("\033[1;31mError: chat tool not found\033[0m\n")
                    continue

            if is_init_map:
                prompt = f"### SYSTEM INSTRUCTIONS (CRITICAL OVERRIDE):\n{active_system_prompt}\n\n### CODESPACE MAP:\n{query}"
            else:
                sys_ctx = skills.get_system_context(
                    query, CONTEXT_FILE, STOP_WORDS, SKILLS_DIR, CFG_DIR
                )

                # --- NATIVE ABORT INTERCEPTOR ---
                # If a tool was cancelled, empty the context and let the AI answer natively
                if sys_ctx == "__ABORT_TURN__":
                    sys_ctx = ""

                comb_ctx = (
                    (f"{tpm_context}\n\n" if tpm_context else "")
                    + (f"{past_memory}\n\n" if past_memory else "")
                    + sys_ctx
                )
                prompt = (
                    f"<context>\n{comb_ctx}\n</context>\n\n" if comb_ctx else ""
                ) + f"User Question: {query}"

            chat_history.append({"role": "user", "content": prompt})
            if not is_init_map:
                try:
                    readline.add_history(query)
                except Exception:
                    pass
            # Explicitly passes your dynamic show_stats state parameter
            ans = stream_llm_response(
                core.prune_history(chat_history),
                prefix="Agent:" if is_agent else "AI:",
                show_stats=show_stats,
            )
            if ans:
                chat_history.append({"role": "assistant", "content": ans})
                if is_agent:
                    subprocess.run(
                        [
                            sys.executable,
                            f"{CFG_DIR}/modules/ai-agent-sessions",
                            "log-turn",
                            safe_name,
                            query,
                            ans,
                        ]
                    )
                    # Match clean, executable intents in the assistant's response
                    match = re.search(
                        r"Run:\s*((?:trace symbol|blast radius|read function|find symbol)\s+\S+|architecture overview)",
                        ans,
                    )
                    if match:
                        suggested_intent = match.group(1).strip()
                        try:
                            import readline

                            readline.set_startup_hook(
                                lambda: readline.insert_text(suggested_intent)
                            )
                        except Exception:
                            pass
                    # ----------------------------------------

                    # --- SPIN BACKGROUND RECONCILIATION THREAD ---
                    # Asynchronously updates your local Temporal Personality Memory (TPM)
                    if memory_active and not is_init_map:
                        threading.Thread(
                            target=background_tpm_update,
                            args=(query, ans, safe_name, workspace_path),
                            daemon=True,
                        ).start()

                    if not is_init_map:
                        hist_file = os.path.join(workspace_path, "history.md")
                        try:
                            mode = "a" if os.path.exists(hist_file) else "w"
                            with open(hist_file, mode, encoding="utf-8") as hf:
                                if mode == "w":
                                    hf.write(
                                        f"# Workspace History: {os.path.basename(os.path.dirname(workspace_path))}\n\n"
                                    )
                                hf.write(
                                    f"## [{time.strftime('%Y-%m-%d %H:%M')}] User:\n{query}\n\n### Agent:\n{ans}\n\n---\n\n"
                                )
                        except Exception:
                            pass
    except KeyboardInterrupt:
        print("\n\r\033[1;33mExiting conversation.\033[0m")
        sys.exit(0)


def run_direct_query(args: list):
    """Executes a direct shell query command, explicitly disabling the speed test output."""
    query_parts = args[1:]
    skill_content = ""
    if query_parts and query_parts[-1].startswith("-"):
        skill_content = skills.load_skill_content(
            query_parts[-1].lstrip("-").lower(), SKILLS_DIR, CFG_DIR
        )
        query_parts = query_parts[:-1]

    active_system_prompt = BASE_PROMPT + (
        f"### Active Skill/Role Instructions:\n{skill_content}\n"
        if skill_content
        else ""
    )
    query = " ".join(query_parts)
    sys_ctx = skills.get_system_context(
        query, CONTEXT_FILE, STOP_WORDS, SKILLS_DIR, CFG_DIR
    )

    # If a tool was cancelled or failed, completely abort the completion turn and return to prompt
    if sys_ctx == "__ABORT_TURN__":
        sys.exit(130)

    messages = [
        {"role": "system", "content": active_system_prompt},
        {
            "role": "user",
            "content": (f"<context>\n{sys_ctx}\n</context>\n\n" if sys_ctx else "")
            + f"User Question: {query}",
        },
    ]
    # Passes show_stats=False so direct queries remain silent
    stream_llm_response(messages, prefix="AI:", show_stats=False)
    sys.exit(0)


def run_matching_search(args: list):
    """Handles single terminal queries, attempting local tool execution first."""
    user_input = re.sub(r"[`$]", "", " ".join(args)).strip()
    if not user_input or args[0].startswith("--"):
        sys.exit(0)
    if re.search(r"[\[\]{}()='\",;|#<>]", user_input):
        shell_name = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
        sys.stderr.write(
            f"zsh: command not found: {user_input}\n"
            if "zsh" in shell_name
            else f"bash: {user_input}: command not found\n"
        )
        sys.exit(127)
    matched = context.jaccard_search(user_input, CONTEXT_FILE, STOP_WORDS)
    if matched:
        print(
            "\n".join(
                f"{line.split('|||', 1)[0]}|||{context.clean_tool_prefix(line.split('|||', 1)[1])}"
                for line in matched.split("\n")
            )
        )
        sys.exit(0)
    shell_name = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    sys.stderr.write(
        f"zsh: command not found: {user_input}\n"
        if "zsh" in shell_name
        else f"bash: {user_input}: command not found\n"
    )
    sys.exit(127)


def main():
    """Main program entry point orchestrating CLI args and flows."""
    try:
        args = sys.argv[1:]
        if args:
            if args[0] == "--interactive" and len(args) >= 2:
                ui.run_interactive_selection(
                    " ".join(args[1:]),
                    lambda q: context.jaccard_search(q, CONTEXT_FILE, STOP_WORDS),
                    context.clean_tool_prefix,
                    lambda n: sys.stderr.write(
                        f"zsh: command not found: {n}\n"
                        if "zsh" in os.path.basename(os.environ.get("SHELL", ""))
                        else f"bash: {n}: command not found\n"
                    ),
                    lambda: skills.ensure_mysys_exists(SKILLS_DIR, CFG_DIR),
                )
                sys.exit(0)
            if args[0] in ("--talk", "--talk-chat"):
                if args[0] == "--talk-chat" or len(args) == 1:
                    run_interactive_chat(args)
                else:
                    run_direct_query(args)
                sys.exit(0)
            run_matching_search(args)
        else:
            # Fallback for empty arguments
            run_direct_query(["--talk"])
    except KeyboardInterrupt:
        sys.stderr.write("\nCancelled.\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
