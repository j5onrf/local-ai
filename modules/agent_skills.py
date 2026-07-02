# File: ~/.config/local-ai/modules/agent_skills.py
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
        out = subprocess.check_output(sanitized, shell=True, text=True, timeout=15, env={**os.environ, "AI_CONTEXT_RUN": "1"}).strip()
        return f"{out}\n" if out else "Action executed successfully.\n"
    except Exception as e:
        return f"[SYSTEM ERROR] Failed to run local tool: {e}\n"

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
                if " --s" not in tool:
                    if not ui.confirm_tool(tool):
                        return ""
                if "system" in tool.lower():
                    ensure_mysys_exists(skills_dir, cfg_dir)
                tool = tool.replace(" --s", "").strip()
                for flag in [" --leaf", " --glow", " --cat", " --mdcat"]:
                    tool = tool.replace(flag, "")
                intent_tokens = set(context.tokenize(entry.get("intent", ""), stop_words))
                
                # --- PATH-AWARE ARGUMENT PARSER FIX ---
                # Preserves directory paths (containing /, ~, or .) and prevents Jaccard token-stripping
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
