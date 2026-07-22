#!/usr/bin/env python3
# Local-Ai Agent [j5onrf] [v0.9.4.7]

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request as urlreq
from typing import List, Optional, Tuple, Dict, Any
from contextlib import closing

CFG_DIR: str = os.path.expanduser("~/.config/local-ai")
CONTEXT_FILE: str = os.path.join(CFG_DIR, "ai-context.md")
SKILLS_DIR: str = os.path.join(CFG_DIR, "skills")
SESSIONS_DIR: str = os.path.join(CFG_DIR, "projects", "database")

BASE_PROMPT: str = "Read-only local shell assistant.\nIf <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n\n"
BASE_PROMPT_CHAT: str = BASE_PROMPT + "### Conversational Guidelines:\n- Role: Active, natural, and highly articulate conversational assistant.\n- Tone: Professional, warm, objective, and intellectually engaging.\n\n"
BASE_PROMPT_AGENT: str = "Active local project workspace developer agent.\nIf <context> is provided, answer directly using only its facts. Otherwise, answer normally.\n\n"


def _run_cmd(args: List[str], stdin: Optional[str] = None) -> str:
    try:
        res = subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=10)
        return res.stdout.strip() if res.returncode == 0 else ""
    except (subprocess.SubprocessError, OSError):
        return ""


def load_env_file(path: str) -> None:
    if os.path.exists(path):
        try:
            for line in open(path, "r", encoding="utf-8"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.replace("export ", "", 1).split("=", 1)
                    k, v = k.strip(), v.split(" #")[0].strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass


load_env_file(os.path.join(CFG_DIR, ".env"))
sys.path.append(os.path.join(CFG_DIR, "modules"))

try:
    import readline
    readline.parse_and_bind(r'"\e[A": previous-history')
    readline.parse_and_bind(r'"\e[B": next-history')
except ImportError:
    pass

try:
    import agent_context as context
    import agent_core as core
    import agent_skills as skills
    import agent_spell as spell
    import agent_ui as ui
except ImportError as e:
    sys.stderr.write(f"\033[1;31m[CRITICAL]: Failed to load modules: {e}\033[0m\n")
    sys.exit(1)

STOP_WORDS = {"is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"}


def workspace_safe_name(workspace_path: str, home_dir: str) -> str:
    safe = workspace_path[len(home_dir):].lstrip("/") if workspace_path.startswith(home_dir) else workspace_path
    return safe.replace("/", "-").strip("-") or "home"


def workspace_db_counts(safe_name: str) -> Tuple[int, int]:
    turns = _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "get-count", safe_name])
    facts = _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "get-tpm-count", safe_name])
    return int(turns or 0), int(facts or 0)


def sync_md_to_sqlite(workspace: str, workspace_path: str) -> None:
    md_path = os.path.join(workspace_path, ".agent", "tpm.md")
    if os.path.exists(md_path):
        try:
            matches = re.findall(r"\*\s+\*\*([^*]+)\*\*:\s*(.*)", open(md_path, "r", encoding="utf-8").read())
            if matches:
                reconciled = {k.strip().lower(): v.strip() for k, v in matches}
                _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "tpm-reconcile", workspace], json.dumps(reconciled))
        except Exception:
            pass


def _get_state() -> Dict[str, bool]:
    state_path = os.path.join(CFG_DIR, ".state.json")
    default = {"spell_active": True, "show_stats": True, "memory_active": True}
    if os.path.exists(state_path):
        try:
            return {**default, **json.load(open(state_path, "r", encoding="utf-8"))}
        except Exception:
            pass
    return default


def _save_state(key: str, value: bool) -> None:
    state = _get_state()
    state[key] = value
    try:
        json.dump(state, open(os.path.join(CFG_DIR, ".state.json"), "w", encoding="utf-8"), indent=2)
    except Exception:
        pass


def background_tpm_update(user_msg: str, assistant_msg: str, workspace: str, workspace_path: str) -> None:
    cleaned = user_msg.lower().strip()
    if len(cleaned) < 8 or cleaned in ("hello", "hi", "hey", "exit", "quit", "q", "/clear", "/reset", "/stats", "/tok", "/m", "/r"):
        return
    try:
        import sqlite3
        db_path = os.path.join(SESSIONS_DIR, f"{workspace}.db")
        existing_facts = ""
        if os.path.exists(db_path):
            with closing(sqlite3.connect(db_path, timeout=5)) as conn:
                cur = conn.cursor()
                cur.execute("SELECT key, value FROM tpm_memories")
                rows = cur.fetchall()
                if rows:
                    existing_facts = "\n".join(f"* {k}: {v}" for k, v in rows)

        sys_p = "You are an asynchronous memory compiler. Analyze turn. Output ONLY flat JSON object of updated facts key-value pairs."
        usr_p = f"### Existing Profile:\n{existing_facts or 'None'}\n\n### Turn:\nUser: {user_msg}\nAssistant: {assistant_msg}\n\nOutput JSON:"

        payload = {"messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}], "temperature": 0.0, "thinking_budget_tokens": 0, "stream": False}
        req = urlreq.Request("http://localhost:8080/v1/chat/completions", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")

        with urlreq.urlopen(req, timeout=5) as resp:
            llm_out = json.loads(resp.read().decode("utf-8"))["choices"][0]["message"].get("content", "").strip()

        llm_out = re.sub(r"^```json\s*|\s*```$", "", llm_out, flags=re.IGNORECASE).strip()
        parsed = json.loads(llm_out)
        if isinstance(parsed, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()):
            mem_tool = f"{CFG_DIR}/modules/ai-agent-memories"
            _run_cmd([sys.executable, mem_tool, "tpm-reconcile", workspace], json.dumps(parsed))
            res_get = _run_cmd([sys.executable, mem_tool, "tpm-get", workspace])
            if res_get:
                md_dir = os.path.join(workspace_path, ".agent")
                os.makedirs(md_dir, exist_ok=True)
                open(os.path.join(md_dir, "tpm.md"), "w", encoding="utf-8").write(res_get + "\n")
    except Exception:
        pass


def clean_exit(safe_name: Optional[str] = None) -> None:
    if safe_name:
        try:
            _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "cleanup-sub", safe_name, str(os.getpid())])
        except Exception:
            pass
    ui._console.print("\n[yellow]Exiting conversation.[/yellow]")
    sys.exit(0)


def run_interactive_chat(args: List[str]) -> None:
    is_agent = args[0] == "--talk-chat"
    skills_list = []
    active_skill = os.environ.get("AI_ACTIVE_SKILL")
    if active_skill:
        skills_list.extend([s.lstrip("-").lower() for s in active_skill.split()])
    for arg in args:
        if arg.startswith("-") and arg not in ("--talk", "--talk-chat"):
            skills_list.append(arg.lstrip("-").lower())
    skills_list = list(dict.fromkeys(skills_list))

    skill_content = skills.load_skill_content(" ".join(skills_list), SKILLS_DIR, CFG_DIR)
    base_p = BASE_PROMPT_AGENT if is_agent else (BASE_PROMPT_CHAT if not skills_list else BASE_PROMPT)
    active_system_prompt = skill_content if (is_agent and skill_content) else (base_p + (f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n" if skill_content else ""))

    workspace_path = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    home_dir = os.path.expanduser("~")
    safe_name = workspace_safe_name(workspace_path, home_dir)

    chat_history = [{"role": "system", "content": active_system_prompt}]
    pending_query = " ".join(args[1:]) if len(args) > 1 else None
    clean_name = " ".join(skills_list)

    st = _get_state()
    spell_active, show_stats, memory_active = st["spell_active"], st["show_stats"], st["memory_active"]
    reasoning_active, reasoning_budget = False, 500

    if is_agent:
        sync_md_to_sqlite(safe_name, workspace_path)

    db_turns, tpm_count = workspace_db_counts(safe_name) if is_agent else (0, 0)
    sub_id = None
    if is_agent:
        try:
            sub_str = _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "get-sub-id", safe_name, str(os.getpid())])
            if sub_str.isdigit() and int(sub_str) > 0:
                sub_id = int(sub_str)
        except Exception:
            pass

    ui.draw_session_box(workspace_path, home_dir, is_agent, db_turns, tpm_count, memory_active, active_system_prompt, clean_name, sub_id=sub_id)

    try:
        while True:
            if pending_query:
                query, pending_query = pending_query, None
            else:
                try:
                    query = input("\033[1;30m❯\033[0m ").strip()
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
                    clean_exit(safe_name if is_agent else None)

                # Slash Help Command
                if query.lower() in ("/help", "/h"):
                    ui.show_help()
                    continue

                if query == "/tui":
                    ui._console.print("[dim yellow][sys] Suspending chat. Launching TUI...[/dim yellow]")
                    time.sleep(0.5)
                    try:
                        subprocess.run([sys.executable, f"{CFG_DIR}/modules/agent_tui.py"])
                    except Exception as e:
                        ui._console.print(f"[red][sys] Failed TUI: {e}[/red]\n")
                    continue

                if query in ("/spell", "/sp"):
                    spell_active = not spell_active
                    _save_state("spell_active", spell_active)
                    ui._console.print(f"[green][sys] Spellchecker {'enabled' if spell_active else 'disabled'}.[/green]\n")
                    continue
                
                if query == "/m":
                    memory_active = not memory_active
                    _save_state("memory_active", memory_active)
                    ui._console.print(f"[green][sys] Memory {'enabled' if memory_active else 'disabled'}.[/green]\n")
                    continue

                if query == "/g":
                    gates_active = os.environ.get("AI_CONFIRM_GATES", "1") == "1"
                    os.environ["AI_CONFIRM_GATES"] = "0" if gates_active else "1"
                    ui._console.print(f"[yellow][sys] Confirmation gates {'disabled (autonomous)' if gates_active else 'enabled'}.[/yellow]\n")
                    continue

                # Main Thinking Toggle & Budget Handler
                parts = query.split()
                if parts and parts[0] in ("/t", "/thinking"):
                    if len(parts) > 1:
                        sub = parts[1].lower()
                        if sub in ("hide", "off", "mute", "quiet"):
                            os.environ["AI_SHOW_THINKING"] = "0"
                            ui._console.print("[yellow][sys] Thinking display hidden (thinking mode remains active).[/yellow]\n")
                            continue
                        elif sub in ("show", "on", "visible"):
                            os.environ["AI_SHOW_THINKING"] = "1"
                            ui._console.print("[yellow][sys] Thinking display enabled.[/yellow]\n")
                            continue
                        elif sub in ("toggle", "t"):
                            curr = os.environ.get("AI_SHOW_THINKING", "1") == "1"
                            os.environ["AI_SHOW_THINKING"] = "0" if curr else "1"
                            ui._console.print(f"[yellow][sys] Thinking display {'hidden' if curr else 'enabled'}.[/yellow]\n")
                            continue
                        else:
                            try:
                                val = int(parts[1])
                                reasoning_active, reasoning_budget = val > 0, max(0, val)
                                ui._console.print(f"[yellow][sys] Deep reasoning {'enabled' if reasoning_active else 'disabled'} (budget: {reasoning_budget} tokens).[/yellow]\n")
                            except ValueError:
                                ui._console.print("[red][sys] Usage: /t [number|show|hide|toggle][/red]\n")
                            continue
                    else:
                        reasoning_active = not reasoning_active
                        ui._console.print(f"[yellow][sys] Deep reasoning {'enabled' if reasoning_active else 'disabled'} (budget: {reasoning_budget} tokens).[/yellow]\n")
                    continue

                if query == "/stats":
                    show_stats = not show_stats
                    _save_state("show_stats", show_stats)  
                    ui._console.print(f"[green][sys] Stats {'enabled' if show_stats else 'disabled'}.[/green]\n")
                    continue

                if query in ("/sync", "/re"):
                    sys.stdout.write("\033[2m[sys] Syncing codespace map...\033[0m\r")
                    sys.stdout.flush()
                    subprocess.run([sys.executable, f"{CFG_DIR}/tools/map/index-map", workspace_path])
                    txt_path = os.path.join(workspace_path, f"index-map-{os.path.basename(workspace_path)}.txt")
                    if os.path.exists(txt_path):
                        try:
                            new_map = open(txt_path, "r", encoding="utf-8").read().strip()
                            updated = False
                            for msg in chat_history:
                                if "### CODESPACE MAP:" in msg["content"]:
                                    msg["content"] = msg["content"].split("### CODESPACE MAP:")[0] + f"### CODESPACE MAP:\n{new_map}"
                                    updated = True
                            if not updated:
                                chat_history[0]["content"] += f"\n\n### CODESPACE MAP:\n{new_map}"
                            ui._console.print("\r\x1b[K[green][sys] Map synchronized.[/green]\n")
                        except Exception as e:
                            ui._console.print(f"\r\x1b[K[red][sys] Sync failed: {e}[/red]\n")
                    continue

                if query.lower() in ("/clear", "/reset"):
                    chat_history = [{"role": "system", "content": active_system_prompt}, {"role": "assistant", "content": "Agent: Workspace loaded. Awaiting instructions."}]
                    for p in (os.path.join(workspace_path, ".agent", "session.json"), os.path.join(workspace_path, ".agent", "tpm.md"), os.path.join(workspace_path, "history.md")):
                        if os.path.exists(p):
                            try:
                                os.remove(p)
                            except Exception:
                                pass
                    _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "clear", safe_name])
                    _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-memories", "tpm-clear", safe_name])
                    ui._console.print("[green][sys] Session and memory cleared.[/green]\n")
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

            if query.startswith(("/", "-")) and (query.startswith(("/skill", "/s")) or query.startswith(("/skill ", "/s "))):
                res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/agent_skills.py", safe_name, query], input=json.dumps(chat_history), stdout=subprocess.PIPE, text=True)
                if res.stdout.strip():
                    try:
                        chat_history = json.loads(res.stdout.strip())
                    except Exception as e:
                        ui._console.print(f"[red]Error loading session: {e}[/red]")
                continue

            if query.startswith("-save"):
                _run_cmd([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "save", safe_name, query.replace("-save", "").strip()], json.dumps(chat_history))
                continue

            if query in ("-load", "-timeline"):
                try:
                    res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "load", safe_name], stdin=sys.stdin, stdout=subprocess.PIPE, text=True)
                    if res.stdout.strip():
                        chat_history = json.loads(res.stdout.strip())
                        ui._console.print(f"[green][session-mgr] Restored session ({len(chat_history) - 1} turns loaded).[/green]\n")
                except Exception as e:
                    ui._console.print(f"[red]Error loading session: {e}[/red]")
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
                        _save_state("memory_active", False)
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
                continue

            if is_init_map:
                prompt = f"### SYSTEM INSTRUCTIONS (CRITICAL OVERRIDE):\n{active_system_prompt}\n\n### CODESPACE MAP:\n{query}"
            else:
                sys_ctx = "" if query.startswith("init") and "--init" in query else skills.get_system_context(query, CONTEXT_FILE, STOP_WORDS, SKILLS_DIR, CFG_DIR)
                if sys_ctx == "__ABORT_TURN__":
                    continue
                comb_ctx = "\n\n".join(filter(None, [tpm_context, past_memory, sys_ctx]))
                prompt = f"<context>\n{comb_ctx}\n</context>\n\nUser Question: {query}" if comb_ctx else f"User Question: {query}"

            chat_history.append({"role": "user", "content": prompt})
            if not is_init_map:
                try:
                    readline.add_history(query)
                except Exception:
                    pass

            ans = core.stream_response(chat_history, prefix="Agent:" if is_agent else "AI:", show_stats=show_stats, thinking_budget=reasoning_budget if reasoning_active else 0, is_agent=is_agent)
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
        clean_exit(safe_name if is_agent else None)


def run_direct_query(args: List[str]) -> None:
    query_parts = args[1:]
    skill_content = ""
    if query_parts and query_parts[-1].startswith("-"):
        skill_content = skills.load_skill_content(query_parts[-1].lstrip("-").lower(), SKILLS_DIR, CFG_DIR)
        query_parts = query_parts[:-1]

    active_p = BASE_PROMPT + (f"### Active Skill/Role Instructions:\n{skill_content}\n" if skill_content else "")
    query = " ".join(query_parts)
    sys_ctx = skills.get_system_context(query, CONTEXT_FILE, STOP_WORDS, SKILLS_DIR, CFG_DIR)
    if sys_ctx == "__ABORT_TURN__":
        sys.exit(130)

    messages = [{"role": "system", "content": active_p}, {"role": "user", "content": (f"<context>\n{sys_ctx}\n</context>\n\n" if sys_ctx else "") + f"User Question: {query}"}]
    core.stream_response(messages, prefix="AI:", show_stats=False)
    sys.exit(0)


def run_matching_search(args: List[str]) -> None:
    user_input = re.sub(r"[`$]", "", " ".join(args)).strip()
    if not user_input or args[0].startswith("--"):
        sys.exit(0)
        
    # Catch /help or /h typed directly in Bash/Zsh prompt
    if user_input.lower() in ("/help", "/h"):
        ui.show_help()
        sys.exit(0)

    shell_name = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    err_msg = f"zsh: command not found: {user_input}\n" if "zsh" in shell_name else f"bash: {user_input}: command not found\n"
    if re.search(r"[\[\]{}()='\",;|#<>]", user_input):
        sys.stderr.write(err_msg)
        sys.exit(127)
    matched = context.jaccard_search(user_input, CONTEXT_FILE, STOP_WORDS)
    if matched:
        print("\n".join(f"{line.split('|||', 1)[0]}|||{context.clean_tool_prefix(line.split('|||', 1)[1])}" for line in matched.split("\n")))
        sys.exit(0)
    sys.stderr.write(err_msg)
    sys.exit(127)


def main() -> None:
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
