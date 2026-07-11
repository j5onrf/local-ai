#!/usr/bin/env python3
# File: ~/.config/local-ai/modules/agent_skills.py
# Description: Unified library & executable for static, dynamic, and on-demand skills

import os
import sys
import re
import subprocess
import json
import agent_ui as ui
import agent_context as context

def ensure_mysys_exists(skills_dir: str, cfg_dir: str) -> None:
    mysys_path = os.path.join(skills_dir, "system", "mysys.md")
    if not os.path.exists(mysys_path):
        try:
            generator = os.path.join(cfg_dir, "tools", "generate-profile")
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

def load_skill_content(skills_str: str, skills_dir: str, cfg_dir: str) -> str:
    if not skills_str:
        return ""
    contents = []
    for skill in [s.lstrip("-").lower() for s in skills_str.split()]:
        skill_file = find_skill_file(skills_dir, skill)
        if skill_file:
            if "system" in skill:
                ensure_mysys_exists(skills_dir, cfg_dir)
            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    contents.append(f.read().strip())
            except Exception as e:
                sys.stderr.write(f"\033[1;31mError loading skill '{skill}': {e}\033[0m\n")
    return "\n\n".join(contents)

def run_local_tool(cmd: str) -> str:
    try:
        sanitized = re.sub(r'\|\s*(leaf|mdcat|cat|glow)\b.*$', '', cmd.strip()).strip()
        # Dynamic working directory synchronization (forces all tools to run inside your active project)
        workspace_path = os.environ.get("AI_WORKSPACE_PATH") or os.getcwd()
        out = subprocess.check_output(
            sanitized, 
            shell=True, 
            text=True, 
            timeout=15, 
            cwd=workspace_path, 
            env={**os.environ, "AI_CONTEXT_RUN": "1"}
        ).strip()
        return f"{out}\n" if out else "Action executed successfully.\n"
    except subprocess.CalledProcessError:
        # Gracefully handle tool execution failures or user cancellations (Ctrl+C)
        sys.stderr.write(f"\033[1;31m[sys] Tool execution failed or was cancelled.\033[0m\n")
        sys.stderr.flush()
        return "__ABORT_TURN__"
    except Exception as e:
        sys.stderr.write(f"\033[1;31m[sys] Error running tool: {e}\033[0m\n")
        sys.stderr.flush()
        return "__ABORT_TURN__"

def run_interactive_tool(cmd: str) -> str:
    """Runs an interactive terminal tool directly in the user's active foreground shell.
    
    By connecting stdout/stdin directly to the terminal, interactive prompts (like read -p)
    and pagers function natively. Aborts the turn cleanly upon exit.
    """
    try:
        sanitized = re.sub(r'\|\s*(leaf|mdcat|cat|glow)\b.*$', '', cmd.strip()).strip()
        workspace_path = os.environ.get("AI_WORKSPACE_PATH") or os.getcwd()
        # Executes with standard streams connected directly to your active terminal window
        subprocess.run(
            sanitized, 
            shell=True, 
            cwd=workspace_path, 
            env={**os.environ, "AI_CONTEXT_RUN": "1"}
        )
        return "__ABORT_TURN__"
    except Exception as e:
        sys.stderr.write(f"\033[1;31m[sys] Error running interactive tool: {e}\033[0m\n")
        sys.stderr.flush()
        return "__ABORT_TURN__"

def get_system_context(query: str, context_file: str, stop_words: set, skills_dir: str, cfg_dir: str) -> str:
    q_tokens = context.tokenize(query, stop_words)
    if not q_tokens or "\n" in query.strip():
        return ""
    for entry in context.load_context_entries(context_file, stop_words):
        ent_tokens = entry.get("tokens", [])
        if any(q_tokens[i:i+len(ent_tokens)] == ent_tokens for i in range(len(q_tokens) - len(ent_tokens) + 1)):
            tool = entry.get("cmd", "")
            if tool.startswith("[TOOL]"):
                tool = tool.replace("[TOOL]", "").strip()
                
                # --- DYNAMIC FOREGROUND EXECUTION HOOK ---
                # If the tool requires interactive input (read -p) or a pager (less, fzf),
                # we run it natively in the foreground and abort the turn cleanly upon exit.
                if "read -p" in tool or "less" in tool or "fzf" in tool:
                    return run_interactive_tool(tool)
                
                if " --s" not in tool:
                    if not ui.confirm_tool(tool):
                        return "__ABORT_TURN__"
                if "system" in tool.lower():
                    ensure_mysys_exists(skills_dir, cfg_dir)
                tool = tool.replace(" --s", "").strip()
                for flag in [" --leaf", " --glow", " --cat", " --mdcat"]:
                    tool = tool.replace(flag, "")
                intent_tokens = set(context.tokenize(entry.get("intent", ""), stop_words))
                
                # --- PATH-AWARE ARGUMENT PARSER ---
                args_list = []
                for w in query.split():
                    if any(c in w for c in ("/", "~", ".")):
                        args_list.append(w)
                    elif context.tokenize(w, stop_words) and context.tokenize(w, stop_words)[0] not in intent_tokens:
                        args_list.append(w)
                args = " ".join(args_list)
                
                if "$1" in tool or "{}" in tool:
                    tool = tool.replace("$1", args).replace("{}", args).strip()
                sys.stderr.write(f"\033[2m[sys] Executing: {tool}\033[0m\n")
                sys.stderr.flush()
                return run_local_tool(tool)
    return ""


# --- DYNAMIC ON-DEMAND SKILL SELECTOR TUI ---

def load_skill_blueprints(dept_skills_dir: str, stop_words: set) -> list:
    blueprints = []
    if os.path.exists(dept_skills_dir):
        for r, _, fs in os.walk(dept_skills_dir):
            for f in fs:
                if f.endswith(".md"):
                    path = os.path.join(r, f)
                    try:
                        # Read file lines
                        with open(path, "r", encoding="utf-8") as sf:
                            lines = [line.strip() for line in sf.readlines()]
                        
                        if not lines:
                            continue

                        first_line = lines[0]
                        
                        # Find the first valid description line (skipping headers, lists, and YAML tags)
                        desc_line = ""
                        for line in lines:
                            # Skip empty lines, headers, lists, blockquotes, and YAML metadata (e.g., "name: pirate")
                            if (line 
                                and not line.startswith(("#", "---", ">", "*", "-", "import "))
                                and not re.match(r'^\w+:\s', line)):
                                desc_line = line
                                break

                        # 1. Parse legacy/strict format if present: "# [SKILL] Name ---> intents"
                        if first_line.startswith("# [SKILL]") and "--->" in first_line:
                            header, intents = first_line.split("--->", 1)
                            skill_name = header.replace("# [SKILL]", "").strip()
                            intent_list = [i.strip() for i in intents.split(",") if i.strip()]
                        else:
                            # 2. Fallback: Parse dynamically from the file's header or filename
                            base_name = os.path.splitext(f)[0]  # e.g., "pirate-talk"
                            
                            # Extract skill name from first header, otherwise clean up the filename
                            first_header = next((l.replace("#", "").strip() for l in lines if l.startswith("#")), None)
                            if first_header:
                                skill_name = first_header
                            else:
                                skill_name = base_name.replace("-", " ").replace("_", " ").title()
                            
                            # Extract search intents from the filename and the skill name
                            filename_tokens = re.split(r"[-_]", base_name.lower())
                            skill_name_tokens = context.tokenize(skill_name, stop_words)
                            intent_list = list(set(filename_tokens + skill_name_tokens))

                        rel_path = os.path.relpath(path, dept_skills_dir)
                        blueprints.append({
                            "name": skill_name.lower(),
                            "path": path,
                            "rel_path": rel_path,
                            "desc": desc_line if desc_line else "No description provided.",
                            "intents": intent_list,
                            "tokens": context.tokenize(" ".join(intent_list), stop_words)
                        })
                    except Exception:
                        pass
    return blueprints

def run_skill_selector(workspace: str, raw_cmd: str, dept_skills_dir: str, stop_words: set) -> None:
    try:
        history_data = sys.stdin.read().strip()
        chat_history = json.loads(history_data)
    except Exception as e:
        sys.stderr.write(f"\033[1;31m[skill-mgr] Failed to load history: {e}\033[0m\n")
        sys.exit(1)

    parts = raw_cmd.strip().split(maxsplit=1)
    search_query = parts[1].strip() if len(parts) > 1 else ""
    skills = load_skill_blueprints(dept_skills_dir, stop_words)
    current_idx = 0

    sys.stderr.write("\033[?25l")  # Hide terminal cursor
    sys.stderr.flush()
    
    try:
        while True:
            # 1. Dynamically calculate candidates matching the active search query
            candidates = []
            for s in skills:
                if not search_query:
                    candidates.append((1.0, s))
                else:
                    q_tokens = set(context.tokenize(search_query, stop_words))
                    s_tokens = set(s["tokens"])
                    score = len(q_tokens & s_tokens) / len(q_tokens | s_tokens) if (q_tokens & s_tokens) else 0.0
                    sq_lower = search_query.lower()
                    if sq_lower in s["name"] or sq_lower in os.path.basename(s["path"]).lower() or any(sq_lower in i for i in s["intents"]):
                        score = max(score, 0.8)
                    if score > 0.0:
                        candidates.append((score, s))

            candidates.sort(key=lambda x: -x[0])
            num_opts = len(candidates)

            # Ensure selection pointer stays within bounds
            if num_opts > 0 and current_idx >= num_opts:
                current_idx = 0

            # 2. Render the TUI Frame
            if num_opts == 0:
                # No matches found for current search buffer
                sys.stderr.write(f"\r\x1b[K\033[1;30m[00/00]\033[0m ❯ \x1b[1;31m[No matches]\x1b[0m for: \033[1;33m{search_query}\033[0m\n")
                sys.stderr.write(f"\r\x1b[K\033[3m   \"Backspace to delete\"\033[0m [Esc to exit]: ")
                sys.stderr.flush()
            else:
                _, selected_skill = candidates[current_idx]
                idx_str = f"{current_idx + 1:02d}/{num_opts:02d}"
                filter_indicator = f" \033[90m| Filter: \033[1;33m{search_query}\033[0m" if search_query else ""
                
                sys.stderr.write(f"\r\x1b[K\033[1;30m[\033[1;32m{idx_str}\033[1;30m]\033[0m ❯ \x1b[1;36m[skill]\x1b[0m \033[1;32m{selected_skill['name']}\033[0m \033[90m({selected_skill['rel_path']}){filter_indicator}\033[0m\n")
                sys.stderr.write(f"\r\x1b[K\033[3m   \"{selected_skill['desc']}\"\033[0m [↵ load  Type to filter  Esc]: ")
                sys.stderr.flush()
            
            # 3. Read Keypress
            key = ui.get_key()
            
            # Escape / Ctrl+C / Quit
            if key in ('\x03', '\x1b'):
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n")
                break
                
            # Enter / Load Selected Skill
            elif key in ('\r', ''):
                if num_opts > 0:
                    _, selected_skill = candidates[current_idx]
                    try:
                        with open(selected_skill["path"], "r") as sf: 
                            skill_body = sf.read().strip()
                        chat_history[0]["content"] += f"\n\n### Loaded On-Demand Skill: {selected_skill['name']}\n{skill_body}\n"
                        sys.stderr.write(f"\r\x1b[K\x1b[1A\r\x1b[K\033[2;32m[sys] Skill '{selected_skill['name']}' successfully loaded.\033[0m\n")
                        print(json.dumps(chat_history))
                    except Exception as e:
                        sys.stderr.write(f"\r\x1b[K\x1b[1A\r\x1b[K\033[1;31m[sys] Failed to load skill: {e}\033[0m\n")
                else:
                    sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KNo skill selected.\n")
                break
                
            # Arrow Keys Navigation
            elif key in ('\x1b[A', '\x1b[B'):
                if num_opts > 0:
                    current_idx = (current_idx + (1 if key == '\x1b[B' else -1) + num_opts) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
                
            # Backspace
            elif key in ('\x7f', '\x08'):
                if len(search_query) > 0:
                    search_query = search_query[:-1]
                    current_idx = 0
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
                
            # Printable Characters (Dynamic search filter append)
            elif len(key) == 1 and key.isprintable():
                search_query += key
                current_idx = 0
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
            else:
                # Discard unknown escapes
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
                
    except KeyboardInterrupt:
        sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n")
        sys.stderr.flush()
        sys.exit(130)
    finally:
        sys.stderr.write("\033[?25h")  # Show terminal cursor
        sys.stderr.flush()


if __name__ == "__main__":
    # Setup config directories for standalone execution when invoked by ai-agent.py
    CFG_DIR = os.path.expanduser("~/.config/local-ai")
    DEPT_SKILLS_DIR = os.path.join(CFG_DIR, "skills", "dept")
    STOP_WORDS = {"is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"}
    
    if len(sys.argv) < 3:
        sys.exit(1)
    run_skill_selector(sys.argv[1], sys.argv[2], DEPT_SKILLS_DIR, STOP_WORDS)
