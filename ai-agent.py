#!/usr/bin/env python3
# Local-Ai Agent [j5onrf] [v0.8.9.10] [06-30-26]

import os
import sys
import re
import json
import time
import subprocess

# Setup configuration constants
CFG_DIR = os.path.expanduser("~/.config/local-ai")
CONTEXT_FILE = os.path.join(CFG_DIR, "ai-context.md")
SKILLS_DIR = os.path.join(CFG_DIR, "skills")
BASE_PROMPT = (
    "Local shell AI assistant (read-only access).\n"
    "Provide direct, natural plain-text answers using any provided system context.\n"
    "No markdown (no bolding, no headers, no bullet lists).\n"
    "Always write full, complete, and helpful sentences.\n\n"
)

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
    import agent_core as core
except ImportError as e:
    sys.stderr.write(f"\033[1;31m[CRITICAL]: Failed to load modular functions: {e}\033[0m\n")
    sys.exit(1)

STOP_WORDS = {
    "is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", 
    "for", "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"
}


def ensure_mysys_exists():
    mysys_path = os.path.join(SKILLS_DIR, "system", "mysys.md")
    if not os.path.exists(mysys_path):
        try:
            generator = os.path.join(CFG_DIR, "tools", "generate-profile")
            subprocess.run([sys.executable, generator], check=False)
        except Exception:
            pass


def find_skill_file(base_dir: str, skill_name: str) -> str or None:
    target_filename = f"{skill_name.lower()}.md"
    for root, _, files in os.walk(base_dir):
        if root[len(base_dir):].count(os.sep) <= 3:
            for f in files:
                if f.lower() == target_filename:
                    return os.path.join(root, f)
    return None


def load_skill_content(skills_str: str) -> str:
    if not skills_str:
        return ""
    contents = []
    for skill in [s.lstrip("-").lower() for s in skills_str.split()]:
        skill_file = find_skill_file(SKILLS_DIR, skill)
        if skill_file:
            if "system" in skill:
                ensure_mysys_exists()
            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    contents.append(f.read().strip())
            except Exception as e:
                sys.stderr.write(f"\033[1;31mError loading skill '{skill}': {e}\033[0m\n")
    return "\n\n".join(contents)


def run_local_tool(cmd: str) -> str:
    try:
        sanitized = re.sub(r'\|\s*(leaf|mdcat|cat|glow)\b.*$', '', cmd.strip()).strip()
        out = subprocess.check_output(sanitized, shell=True, text=True, timeout=15, env={**os.environ, "AI_CONTEXT_RUN": "1"}).strip()
        return f"{out}\n" if out else "Action executed successfully.\n"
    except Exception as e:
        return f"[SYSTEM ERROR] Failed to run local tool: {e}\n"


def get_system_context(query: str) -> str:
    q_tokens = core.tokenize(query, STOP_WORDS)
    if not q_tokens or "\n" in query.strip():
        return ""
    for entry in core.load_context_entries(CONTEXT_FILE, STOP_WORDS):
        ent_tokens = entry.get("tokens", [])
        if any(q_tokens[i:i+len(ent_tokens)] == ent_tokens for i in range(len(q_tokens) - len(ent_tokens) + 1)):
            tool = entry.get("cmd", "")
            if tool.startswith("[TOOL]"):
                tool = tool.replace("[TOOL]", "").strip()
                if " --s" not in tool:
                    if not core.confirm_tool(tool):
                        return ""
                if "system" in tool.lower():
                    ensure_mysys_exists()
                tool = tool.replace(" --s", "").strip()
                for flag in [" --leaf", " --glow", " --cat", " --mdcat"]:
                    tool = tool.replace(flag, "")
                intent_tokens = set(core.tokenize(entry.get("intent", ""), STOP_WORDS))
                args = " ".join([w for w in query.split() if core.tokenize(w, STOP_WORDS) and core.tokenize(w, STOP_WORDS)[0] not in intent_tokens])
                if "$1" in tool or "{}" in tool:
                    tool = tool.replace("$1", args).replace("{}", args).strip()
                sys.stderr.write(f"\033[2m[sys] Executing: {tool}\033[0m\n")
                sys.stderr.flush()
                return run_local_tool(tool)
    return ""


def stream_llm_response(messages: list, prefix: str = "AI: ") -> str or None:
    return core.stream_response(messages, prefix, CFG_DIR)


def run_interactive_chat(args: list):
    is_agent = (args[0] == "--talk-chat")
    skills_list = []
    active_skill = os.environ.get("AI_ACTIVE_SKILL")
    if active_skill:
        skills_list.extend([s.lstrip("-").lower() for s in active_skill.split()])
    for arg in args:
        if arg.startswith("-") and arg not in ("--talk", "--talk-chat"):
            skills_list.append(arg.lstrip("-").lower())
    skills_list = list(dict.fromkeys(skills_list))
    
    skill_content = load_skill_content(" ".join(skills_list))
    active_system_prompt = skill_content if (is_agent and skill_content) else (BASE_PROMPT + (f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n" if skill_content else ""))
    
    workspace_path = os.environ.get("AI_WORKSPACE_PATH", os.getcwd())
    home_dir = os.path.expanduser("~")
    safe_name = workspace_path[len(home_dir):].lstrip("/") if workspace_path.startswith(home_dir) else workspace_path
    safe_name = safe_name.replace("/", "-").strip("-") or "home"
    
    chat_history = [{"role": "system", "content": active_system_prompt}]
    pending_query = " ".join(args[1:]) if len(args) > 1 else None
    clean_name = " ".join(skills_list)
    
    # Spellcheck is disabled by default in workspaces, but active in chat
    spell_active = not is_agent
    memory_active = True
    
    db_turns = 0
    if is_agent:
        try:
            res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "get-count", safe_name], capture_output=True, text=True)
            db_turns = int(res.stdout.strip())
        except Exception:
            pass
        
    core.draw_session_box(workspace_path, home_dir, is_agent, db_turns, active_system_prompt, clean_name)
    
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
                    spell_active = (query == "/e")
                    print(f"\033[1;33m[sys] Spellchecker {'enabled' if spell_active else 'disabled'}.\033[0m\n")
                    continue
                if query == "/m":
                    memory_active = not memory_active
                    print(f"\033[1;33m[sys] Memory recall {'enabled' if memory_active else 'disabled'}.\033[0m\n")
                    continue
                if query == "/tok":
                    subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "show-tok"], input=json.dumps(chat_history), text=True)
                    continue
                if spell_active and not query.startswith(("/", "-", "#", "```")):
                    action, query = core.check_query_spelling(query, core.get_key)
                    if action == "EDIT":
                        try:
                            readline.set_startup_hook(lambda: readline.insert_text(query))
                        except Exception:
                            pass
                        continue
                    elif action == "DISABLE":
                        spell_active = False
                    
            if query.startswith(("/skill", "/s")) or query.startswith(("/skill ", "/s ")):
                res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-skills", safe_name, query], input=json.dumps(chat_history), stdout=subprocess.PIPE, text=True)
                if res.stdout.strip():
                    try:
                        chat_history = json.loads(res.stdout.strip())
                    except Exception as e:
                        print(f"Error loading session: {e}")
                continue
            if query.startswith("-save"):
                subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "save", safe_name, query.replace("-save", "").strip()], input=json.dumps(chat_history), text=True)
                continue
            if query in ("-load", "-timeline"):
                res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "load", safe_name], stdin=sys.stdin, stdout=subprocess.PIPE, text=True)
                if res.stdout.strip():
                    try:
                        chat_history = json.loads(res.stdout.strip())
                        print(f"\033[1;32m[session-mgr] Restored session ({len(chat_history)-1} turns loaded).\033[0m\n")
                    except Exception as e:
                        print(f"Error loading session: {e}")
                else:
                    print(f"\033[1;31m[session-mgr] Load aborted.\033[0m\n")
                continue
                
            past_memory = ""
            is_init_map = query.startswith(("#", "[", "{")) or "\n" in query or "last_interaction_id" in query or "index-map" in query
            if is_agent and memory_active and not is_init_map:
                res = subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "get-context", safe_name, query], stdout=subprocess.PIPE, text=True)
                if res.returncode == 2:
                    pending_query = None
                    continue
                if res.returncode == 3:
                    memory_active = False
                past_memory = res.stdout.strip()
                
            if re.match(r'^/?([ftba])(?:\s+(\d+))?$', query.lower()):
                think_bin = f"{CFG_DIR}/modules/chat"
                if os.path.exists(think_bin):
                    try:
                        subprocess.run([sys.executable, think_bin, query], input=json.dumps(chat_history), text=True)
                    except Exception as e:
                        sys.stderr.write(f"\033[1;31m[Warning] chat failed: {e}\033[0m\n")
                else:
                    sys.stderr.write("\033[1;31mError: chat tool not found\033[0m\n")
                continue
                
            if is_init_map:
                prompt = f"### SYSTEM INSTRUCTIONS (CRITICAL OVERRIDE):\n{active_system_prompt}\n\n### CODESPACE MAP:\n{query}"
            else:
                sys_ctx = get_system_context(query)
                comb_ctx = (f"{past_memory}\n\n" if past_memory else "") + sys_ctx
                prompt = (f"### Real-time System Context:\n{comb_ctx}\n\n" if comb_ctx else "") + f"User Question: {query}"
                
            chat_history.append({"role": "user", "content": prompt})
            if not is_init_map:
                try:
                    readline.add_history(query)
                except Exception:
                    pass
            ans = stream_llm_response(core.prune_history(chat_history), prefix="Agent:" if is_agent else "AI:")
            if ans:
                chat_history.append({"role": "assistant", "content": ans})
                if is_agent:
                    subprocess.run([sys.executable, f"{CFG_DIR}/modules/ai-agent-sessions", "log-turn", safe_name, query, ans])
                    if not is_init_map:
                        hist_file = os.path.join(workspace_path, "history.md")
                        try:
                            mode = "a" if os.path.exists(hist_file) else "w"
                            with open(hist_file, mode, encoding="utf-8") as hf:
                                if mode == "w":
                                    hf.write(f"# Workspace History: {os.path.basename(os.path.dirname(hist_file))}\n\n")
                                hf.write(f"## [{time.strftime('%Y-%m-%d %H:%M')}] User:\n{query}\n\n### Agent:\n{ans}\n\n---\n\n")
                        except Exception:
                            pass
    except KeyboardInterrupt:
        print("\n\r\033[1;33mExiting conversation.\033[0m")
        sys.exit(0)


def run_direct_query(args: list):
    """Executes a direct shell query command without entering full chat loop."""
    query_parts = args[1:]
    active_system_prompt = BASE_PROMPT
    if query_parts and query_parts[-1].startswith("-"):
        skill_content = load_skill_content(query_parts[-1].lstrip("-").lower())
        if skill_content:
            active_system_prompt += f"\n\n### Active Skill/Role Instructions:\n{skill_content}\n"
        query_parts = query_parts[:-1]
    query = " ".join(query_parts)
    sys_ctx = get_system_context(query)
    messages = [
        {"role": "system", "content": active_system_prompt},
        {"role": "user", "content": (f"### Real-time System Context:\n{sys_ctx}\n\n" if sys_ctx else "") + f"User Question: {query}"}
    ]
    stream_llm_response(messages, prefix="AI:")
    sys.exit(0)


def run_matching_search(args: list):
    """Handles single terminal queries, attempting local tool execution first."""
    user_input = re.sub(r"[`$]", "", " ".join(args)).strip()
    if not user_input or args[0].startswith("--"):
        sys.exit(0)
    if re.search(r"[\[\]{}()='\",;|#<>]", user_input):
        shell_name = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
        sys.stderr.write(f"zsh: command not found: {user_input}\n" if "zsh" in shell_name else f"bash: {user_input}: command not found\n")
        sys.exit(127)
    matched = core.jaccard_search(user_input, CONTEXT_FILE, STOP_WORDS)
    if matched:
        print("\n".join(f"{line.split('|||', 1)[0]}|||{core.clean_tool_prefix(line.split('|||', 1)[1])}" for line in matched.split("\n")))
        sys.exit(0)
    shell_name = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    sys.stderr.write(f"zsh: command not found: {user_input}\n" if "zsh" in shell_name else f"bash: {user_input}: command not found\n")
    sys.exit(127)


def main():
    """Main program entry point orchestrating CLI args and flows."""
    try:
        args = sys.argv[1:]
        if args:
            if args[0] == "--interactive" and len(args) >= 2:
                core.run_interactive_selection(
                    " ".join(args[1:]),
                    lambda q: core.jaccard_search(q, CONTEXT_FILE, STOP_WORDS),
                    core.clean_tool_prefix,
                    lambda n: sys.stderr.write(f"zsh: command not found: {n}\n" if "zsh" in os.path.basename(os.environ.get("SHELL", "")) else f"bash: {n}: command not found\n"),
                    ensure_mysys_exists
                )
                sys.exit(0)
            if args[0] in ("--talk", "--talk-chat"):
                if args[0] == "--talk-chat" or len(args) == 1:
                    run_interactive_chat(args)
                else:
                    run_direct_query(args)
                sys.exit(0)
            run_matching_search(args)
    except KeyboardInterrupt:
        sys.stderr.write("\nCancelled.\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
