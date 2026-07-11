#!/usr/bin/env python3
# Local-Ai Agent [j5onrf] [v0.9.2.0]

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

BASE_PROMPT_CHAT = (
    "Read-only local shell assistant.\n"
    "If <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n"
    "Write full, natural sentences without markdown, headers, bolding, or lists.\n\n"
    "### Conversational Guidelines:\n"
    "- Role: Active, natural, and highly articulate conversational assistant.\n"
    "- Tone: Professional, warm, objective, and intellectually engaging.\n\n"
)

BASE_PROMPT_AGENT = (
    "Active local project workspace developer agent.\n"
    "If <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n"
    "Write full, natural sentences without markdown, headers, bolding, or lists.\n\n"
)


def _run_cmd(args: list, stdin: str = None) -> str:
    """Consolidated process execution pipeline to interact with helper scripts."""
    try:
        res = subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=10)
        return res.stdout.strip() if res.returncode == 0 else ""
    except Exception:
        return ""


def load_env_file(path: str) -> None:
    """Safely loads key-value assignments from local environment assets."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        k = k.replace("export ", "", 1).strip()
                        if not v.startswith(('"', "'")):
                            v = v.split(" #")[0]
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


# Initialize localized environmental files at startup
load_env_file(os.path.join(CFG_DIR, ".env"))
sys.path.append(os.path.join(CFG_DIR, "modules"))

try:
    import readline
    readline.parse_and_bind(r'"\e[A": previous-history')
    readline.parse_and_bind(r'"\e[B": next-history')
except ImportError:
    pass

# Unify functional domain namespaces
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
    "is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", 
    "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"
}


def workspace_safe_name(workspace_path: str, home_dir: str) -> str:
    safe = workspace_path[len(home_dir):].lstrip("/") if workspace_path.startswith(home_dir) else workspace_path
    return safe.replace("/", "-").strip("-") or "home"


def workspace_db_counts(safe_name: str) -> tuple:
    turns = _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "get-count", safe_name])
    facts = _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "get-tpm-count", safe_name])
    return int(turns or 0), int(facts or 0)


def sync_md_to_sqlite(workspace: str, workspace_path: str) -> None:
    md_path = os.path.join(workspace_path, ".agent", "tpm.md")
    if os.path.exists(md_path):
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                matches = re.findall(r"\*\s+\*\*([^*]+)\*\*:\s*(.*)", f.read())
            if matches:
                reconciled = {k.strip().lower(): v.strip() for k, v in matches}
                _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "tpm-reconcile", workspace], json.dumps(reconciled))
        except Exception:
            pass

def validate_flat_schema(data: dict) -> bool:
    """Verifies that the decoded JSON is strictly a flat dictionary of non-empty string keys and values."""
    try:
        if not isinstance(data, dict):
            return False
        # Ensure every key and value in the dictionary is a non-empty string
        return all(isinstance(k, str) and k.strip() and isinstance(v, str) for k, v in data.items())
    except Exception:
        return False


def _save_state(key: str, value: bool) -> None:
    """Saves a terminal interface configuration state directly to your local .state.json config file."""
    state_path = os.path.join(CFG_DIR, ".state.json")
    data = {"spell_active": True, "show_stats": True}
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data[key] = value
    try:
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def background_tpm_update(user_msg: str, assistant_msg: str, workspace: str, workspace_path: str):
    cleaned = user_msg.lower().strip()
    if len(cleaned) < 8 or cleaned in ("hello", "hi", "hey", "exit", "quit", "q", "/clear", "/reset", "/stats", "/tok", "/m", "/r"):
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

        user_prompt = f"### Existing Memory Profile:\n{existing_facts or 'None'}\n\n### Latest Turn:\nUser: {user_msg}\nAssistant: {assistant_msg}\n\nIdentify and reconcile any updates. Output JSON:"

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "thinking_budget_tokens": 0,
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

        llm_out = re.sub(r"^```json\s*|\s*```$", "", llm_out, flags=re.IGNORECASE).strip()
        
        # Safely attempt to decode the JSON stream
        try:
            parsed_json = json.loads(llm_out)
        except Exception:
            parsed_json = None

        # Verify the structure is strictly a flat string-to-string dictionary
        if parsed_json and validate_flat_schema(parsed_json):
            mem_tool = f"{CFG_DIR}/modules/ai-agent-memories"
            _run_cmd([sys.executable, mem_tool, "tpm-reconcile", workspace], json.dumps(parsed_json))
            res_get = _run_cmd([sys.executable, mem_tool, "tpm-get", workspace])
            if res_get:
                md_dir = os.path.join(workspace_path, ".agent")
                os.makedirs(md_dir, exist_ok=True)
                with open(os.path.join(md_dir, "tpm.md"), "w", encoding="utf-8") as mdf:
                    mdf.write(res_get + "\n")
    except Exception:
        pass


# Helper to stream and count tokens for the speed-test (updated with reasoning budget support)
def stream_llm_response(
    messages: list, prefix: str = "AI: ", show_stats: bool = True, thinking_budget: int = 0, is_agent: bool = False
) -> str or None:
    return core.stream_response(messages, prefix, CFG_DIR, show_stats, thinking_budget, is_agent)


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
    
    # 1. Select the dynamic base prompt based on workspace or conversational status
    if is_agent:
        base_p = BASE_PROMPT_AGENT
    else:
        # Load the warm chat baseline by default for conversational sessions
        base_p = BASE_PROMPT_CHAT if not skills_list else BASE_PROMPT
    
    active_system_prompt = (
        skill_content
        if (is_agent and skill_content)
        else (
            base_p
            + (
                f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n"
                if skill_content
                else ""
            )
        )
    )

    workspace_path = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    home_dir = os.path.expanduser("~")
    safe_name = workspace_safe_name(workspace_path, home_dir)

    chat_history = [{"role": "system", "content": active_system_prompt}]
    pending_query = " ".join(args[1:]) if len(args) > 1 else None
    clean_name = " ".join(skills_list)

    # Load persistent configurations from localized .state.json, defaulting both to True (Enabled)
    spell_active = True
    show_stats = True
    state_path = os.path.join(CFG_DIR, ".state.json")
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                spell_active = data.get("spell_active", True)
                show_stats = data.get("show_stats", True)
        except Exception:
            pass
            
    memory_active = True
    
    # Reasoning parameters
    reasoning_active = False # Disabled by default inside CLI chat loops
    reasoning_budget = 500   # Default budget allocation when active

    if is_agent:
        sync_md_to_sqlite(safe_name, workspace_path)

    db_turns, tpm_count = workspace_db_counts(safe_name) if is_agent else (0, 0)
    ui.draw_session_box(workspace_path, home_dir, is_agent, db_turns, tpm_count, memory_active, active_system_prompt, clean_name)

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
                # --- SPELLCHECKER TOGGLE (/spell or /sp) ---
                if query in ("/spell", "/sp"):
                    spell_active = not spell_active
                    # Commit the change persistently to your local state file
                    _save_state("spell_active", spell_active)
                    print(f"\033[1;32m[sys] Spellchecker {'enabled' if spell_active else 'disabled'}.\033[0m\n")
                    continue
                # --- UNIFIED MEMORY LAYER TOGGLE (/m) ---
                if query == "/m":
                    memory_active = not memory_active
                    print(
                        f"\033[1;33m[sys] Long-term memory and TPM reconciliation {'enabled' if memory_active else 'disabled'}.\033[0m\n"
                    )
                    continue

                # --- CONFIRMATION GATES TOGGLE (/g) ---
                if query == "/g":
                    gates_active = os.environ.get("AI_CONFIRM_GATES", "1") == "1"
                    new_state = "0" if gates_active else "1"
                    os.environ["AI_CONFIRM_GATES"] = new_state
                    status = "enabled" if new_state == "1" else "disabled (autonomous mode active)"
                    print(f"\033[1;33m[sys] Agent confirmation gates {status}.\033[0m\n")
                    continue

                # --- REASONING TOGGLE (/r <tokens> or /r) ---
                parts = query.split()
                if parts and parts[0] == "/r":
                    if len(parts) > 1:
                        try:
                            val = int(parts[1])
                            if val > 0:
                                reasoning_active, reasoning_budget = True, val
                                print(f"\033[1;33m[sys] Deep reasoning (thinking mode) enabled (budget: {reasoning_budget} tokens).\033[0m\n")
                            else:
                                reasoning_active = False
                                print("\033[1;33m[sys] Deep reasoning (thinking mode) disabled.\033[0m\n")
                        except ValueError:
                            print("\033[1;31m[sys] Invalid token count. Use /r <number> (e.g., /r 500) or simply /r to toggle.\033[0m\n")
                    else:
                        reasoning_active = not reasoning_active
                        status = f"enabled (budget: {reasoning_budget} tokens)" if reasoning_active else "disabled"
                        print(f"\033[1;33m[sys] Deep reasoning (thinking mode) {status}.\033[0m\n")
                    continue

                # --- STATS ON-DEMAND TOGGLE ---
                if query == "/stats":
                    show_stats = not show_stats
                    _save_state("show_stats", show_stats)  # <-- Executes the save
                    print(
                        f"\033[1;32m[sys] Generation statistics {'enabled' if show_stats else 'disabled'}.\033[0m\n"
                    )
                    continue

                # --- NATIVE FULL SESSION CLEAR ---
                if query.lower() in ("/clear", "/reset"):
                    chat_history = [
                        {"role": "system", "content": active_system_prompt},
                        {"role": "assistant", "content": "Agent: Workspace loaded. Awaiting instructions."},
                    ]
                    for path in (os.path.join(workspace_path, ".agent", "session.json"),
                                 os.path.join(workspace_path, ".agent", "tpm.md"),
                                 os.path.join(workspace_path, "history.md")):
                        try:
                            if os.path.exists(path):
                                os.remove(path)
                        except Exception:
                            pass
                    _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "clear", safe_name])
                    _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "tpm-clear", safe_name])
                    print("\033[1;32m[sys] Conversation history, cloud session, and local TPM memory cleared.\033[0m\n")
                    continue

                if query == "/tok":
                    subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "show-tok"], input=json.dumps(chat_history), text=True)
                    continue

                if spell_active and not query.startswith(("/", "-", "#", "```")):
                    action, query = spell.check_query_spelling(query, ui.get_key)
                    if action == "EDIT":
                        try:
                            readline.set_startup_hook(lambda: readline.insert_text(query))
                        except Exception:
                            pass
                        continue
                    elif action == "DISABLE":
                        spell_active = False

            if query.startswith(("/skill", "/s")) or query.startswith(("/skill ", "/s ")):
                res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/agent_skills.py", safe_name, query], input=json.dumps(chat_history), stdout=subprocess.PIPE, text=True)
                if res.stdout.strip():
                    try:
                        chat_history = json.loads(res.stdout.strip())
                    except Exception as e:
                        print(f"Error loading session: {e}")
                continue

            if query.startswith("-save"):
                _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "save", safe_name, query.replace("-save", "").strip()], json.dumps(chat_history))
                continue

            if query in ("-load", "-timeline"):
                try:
                    res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "load", safe_name], stdin=sys.stdin, stdout=subprocess.PIPE, text=True)
                    if res.stdout.strip():
                        chat_history = json.loads(res.stdout.strip())
                        print(f"\033[1;32m[session-mgr] Restored session ({len(chat_history) - 1} turns loaded).\033[0m\n")
                    else:
                        print(f"\033[1;31m[session-mgr] Load aborted.\033[0m\n")
                except Exception as e:
                    print(f"Error loading session: {e}")
                continue

            past_memory, tpm_context = "", ""
            is_init_map = query.startswith(("#", "[", "{")) or "\n" in query or "last_interaction_id" in query or "index-map" in query
            if is_agent and memory_active and not is_init_map:
                try:
                    res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "get-context", safe_name, query], stdout=subprocess.PIPE, text=True)
                    if res.returncode == 2:
                        pending_query = None
                        continue
                    if res.returncode == 3:
                        memory_active = False
                    past_memory = res.stdout.strip()
                except Exception:
                    pass
                tpm_context = _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "tpm-get", safe_name])

            if re.match(r"^/?([ftba])(?:\s+(\d+))?$", query.lower()):
                think_bin = f"{CFG_DIR}/modules/chat"
                if os.path.exists(think_bin):
                    try:
                        subprocess.run([sys.executable, think_bin, query], input=json.dumps(chat_history), text=True)
                        continue
                    except Exception as e:
                        sys.stderr.write(f"\033[1;31m[Warning] chat failed: {e}\033[0m\n")
                else:
                    sys.stderr.write("\033[1;31mError: chat tool not found\033[0m\n")
                continue

            if is_init_map:
                prompt = f"### SYSTEM INSTRUCTIONS (CRITICAL OVERRIDE):\n{active_system_prompt}\n\n### CODESPACE MAP:\n{query}"
            else:
                # Secure Bypass: Do not trigger codebase tools or file reads on the startup initialization turn
                if query.startswith("init") and "--init" in query:
                    sys_ctx = ""
                else:
                    sys_ctx = skills.get_system_context(query, CONTEXT_FILE, STOP_WORDS, SKILLS_DIR, CFG_DIR)
                
                if sys_ctx == "__ABORT_TURN__":
                    sys_ctx = ""

                comb_ctx = "\n\n".join(filter(None, [tpm_context, past_memory, sys_ctx]))
                prompt = f"<context>\n{comb_ctx}\n</context>\n\nUser Question: {query}" if comb_ctx else f"User Question: {query}"

            chat_history.append({"role": "user", "content": prompt})
            if not is_init_map:
                try:
                    readline.add_history(query)
                except Exception:
                    pass

            # Explicitly passes your dynamic show_stats state parameter and reasoning budget
            ans = stream_llm_response(
                chat_history,
                prefix="Agent:" if is_agent else "AI:",
                show_stats=show_stats,
                thinking_budget=reasoning_budget if reasoning_active else 0,
                is_agent=is_agent,
            )
            if ans:
                chat_history.append({"role": "assistant", "content": ans})
                if is_agent:
                    _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "log-turn", safe_name, query, ans])
                    match = re.search(r"Run:\s*((?:trace symbol|blast radius|read function|find symbol)\s+\S+|architecture overview)", ans)
                    if match:
                        try:
                            readline.set_startup_hook(lambda: readline.insert_text(match.group(1).strip()))
                        except Exception:
                            pass

                    if memory_active and not is_init_map:
                        threading.Thread(target=background_tpm_update, args=(query, ans, safe_name, workspace_path), daemon=True).start()

                    if not is_init_map:
                        hist_file = os.path.join(workspace_path, "history.md")
                        try:
                            mode = "a" if os.path.exists(hist_file) else "w"
                            with open(hist_file, mode, encoding="utf-8") as hf:
                                if mode == "w":
                                    hf.write(f"# Workspace History: {os.path.basename(os.path.dirname(workspace_path))}\n\n")
                                hf.write(f"## [{time.strftime('%Y-%m-%d %H:%M')}] User:\n{query}\n\n### Agent:\n{ans}\n\n---\n\n")
                        except Exception:
                            pass
    except KeyboardInterrupt:
        print("\n\r\033[1;33mExiting conversation.\033[0m")
        sys.exit(0)


def run_direct_query(args: list):
    query_parts = args[1:]
    skill_content = ""
    if query_parts and query_parts[-1].startswith("-"):
        skill_content = skills.load_skill_content(query_parts[-1].lstrip("-").lower(), SKILLS_DIR, CFG_DIR)
        query_parts = query_parts[:-1]

    active_system_prompt = BASE_PROMPT + (f"### Active Skill/Role Instructions:\n{skill_content}\n" if skill_content else "")
    query = " ".join(query_parts)
    sys_ctx = skills.get_system_context(query, CONTEXT_FILE, STOP_WORDS, SKILLS_DIR, CFG_DIR)

    if sys_ctx == "__ABORT_TURN__":
        sys.exit(130)

    messages = [
        {"role": "system", "content": active_system_prompt},
        {"role": "user", "content": (f"<context>\n{sys_ctx}\n</context>\n\n" if sys_ctx else "") + f"User Question: {query}"},
    ]
    stream_llm_response(messages, prefix="AI:", show_stats=False)
    sys.exit(0)


def run_matching_search(args: list):
    user_input = re.sub(r"[`$]", "", " ".join(args)).strip()
    if not user_input or args[0].startswith("--"):
        sys.exit(0)
    if re.search(r"[\[\]{}()='\",;|#<>]", user_input):
        shell_name = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
        sys.stderr.write(f"zsh: command not found: {user_input}\n" if "zsh" in shell_name else f"bash: {user_input}: command not found\n")
        sys.exit(127)
    matched = context.jaccard_search(user_input, CONTEXT_FILE, STOP_WORDS)
    if matched:
        print("\n".join(f"{line.split('|||', 1)[0]}|||{context.clean_tool_prefix(line.split('|||', 1)[1])}" for line in matched.split("\n")))
        sys.exit(0)
    shell_name = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    sys.stderr.write(f"zsh: command not found: {user_input}\n" if "zsh" in shell_name else f"bash: {user_input}: command not found\n")
    sys.exit(127)


def main():
    try:
        args = sys.argv[1:]
        if args:
            if args[0] == "--interactive" and len(args) >= 2:
                ui.run_interactive_selection(
                    " ".join(args[1:]),
                    lambda q: context.jaccard_search(q, CONTEXT_FILE, STOP_WORDS),
                    context.clean_tool_prefix,
                    lambda n: sys.stderr.write(f"zsh: command not found: {n}\n" if "zsh" in os.path.basename(os.environ.get("SHELL", "")) else f"bash: {n}: command not found\n"),
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
            run_direct_query(["--talk"])
    except KeyboardInterrupt:
        sys.stderr.write("\nCancelled.\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
