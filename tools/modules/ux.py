# File: /home/j5/.config/local-ai/tools/modules/ux.py
# Description: On-demand terminal UI, input handlers, and layout helpers

import sys, re, os, json, threading, time, tty, termios, select

class InlineSpinner:
    def __init__(self): self.chars, self.active, self.thread = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", False, None
    def _spin(self):
        idx = 0
        while self.active:
            try: sys.stderr.write(f"\r\033[1;32m{self.chars[idx % 12]}\033[0m "); sys.stderr.flush()
            except: pass
            idx, _ = idx + 1, time.sleep(0.08)
        sys.stderr.write("\r\x1b[2K\r"); sys.stderr.flush()
    def start(self): self.active, self.thread = True, threading.Thread(target=self._spin, daemon=True); self.thread.start()
    def stop(self): self.active = False; (self.thread.join() if self.thread else None)

def get_key():
    fd = sys.stdin.fileno()
    try: old = termios.tcgetattr(fd)
    except:
        try: return os.read(fd, 1).decode("utf-8", errors="ignore")
        except: return ""
    try:
        tty.setraw(fd); r = os.read(fd, 1)
        if r == b'\x1b' and select.select([fd], [], [], 0.05)[0]: r += os.read(fd, 2)
    finally: termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return r.decode("utf-8", errors="ignore")

def prune_history(history, max_tokens=None):
    if len(history) <= 1: return history
    try: max_tokens = int(os.environ.get("AI_MAX_TOKENS", 8192)) if max_tokens is None else max_tokens
    except: max_tokens = 8192
    sys_prompt = history[0]
    curr, selected = len(sys_prompt["content"]) // 4, []
    for m in reversed(history[1:]):
        toks = len(m["content"]) // 4
        if not selected or curr + toks <= max_tokens:
            selected.append(m); curr += toks
        else: break
    return [sys_prompt] + list(reversed(selected))

def draw_session_box(workspace_path, home_dir, is_agent, db_turns, active_system_prompt, clean_name):
    version = ""
    main_script_path = os.path.join(os.path.expanduser("~"), ".config", "local-ai", "ai-agent.py")
    try: version = re.search(r"Local-Ai Agent\s+(v[0-9.]+)", open(main_script_path, encoding="utf-8").readlines()[1], re.I).group(1)
    except: pass

    display_dir = workspace_path
    if display_dir.startswith(home_dir):
        display_dir = display_dir.replace(home_dir, "~", 1)
    if len(display_dir) > 28:
        display_dir = "..." + display_dir[-25:]

    gkey = os.environ.get("GEMINI_API_KEY")
    okey = os.environ.get("OPENROUTER_API_KEY")
    if gkey:
        model_name = os.environ.get("CLOUD_MODEL", "gemini-3.1-flash-lite")
    elif okey:
        model_name = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
    else:
        model_name = "local-model"

    box_width = 46
    title_line = f" >_ Local-AI Agent ({version})" if version else " >_ Local-AI Agent"
    model_line = f" model:     {model_name}"
    dir_line   = f" directory: {display_dir}"
    skill_line = f" skill:     {clean_name}" if clean_name else " skill:     default"
    mem_line   = f" database:  {db_turns} turns (asleep)" if is_agent else f" database:  stateless"
    
    print("\033[1;36m╭" + "─" * box_width + "╮\033[0m")
    print(f"\033[1;36m│\033[0m \033[1;37m{title_line:<{box_width-1}}\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m{' ':<{box_width}}\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[2m{model_line:<{box_width-1}}\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[2m{dir_line:<{box_width-1}}\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[2m{skill_line:<{box_width-1}}\033[1;36m│\033[0m")
    print(f"\033[1;36m│\033[0m \033[2m{mem_line:<{box_width-1}}\033[1;36m│\033[0m")
    print("\033[1;36m╰" + "─" * box_width + "╯\033[0m")
    
    # Updated startup context line to use the legible 2m dim styling
    print(f"\033[2m[sys] Startup context: {len(active_system_prompt)//4:,} tokens | Ctrl+C to exit.\033[0m\n")

def run_interactive_selection(intent, jaccard_search, clean_tool_prefix, print_stock_error, ensure_mysys_exists):
    if re.search(r'[\[\]{}()=\'"",;|<>#]', intent): print_stock_error(intent); sys.exit(127)
    matched_base = jaccard_search(intent)
    if not matched_base: print_stock_error(intent); sys.exit(127)
    options = matched_base.split("\n")
    num_opts, current_idx = len(options), 0
    sys.stderr.write("\033[?25l"); sys.stderr.flush()
    try:
        while True:
            current_intent, current_cmd = options[current_idx].split("|||", 1)
            current_cmd = clean_tool_prefix(current_cmd)
            is_danger = current_cmd.startswith("DANGER_FLAGGED:")
            cmd_to_show = current_cmd.replace("DANGER_FLAGGED:", "")
            display_cmd = cmd_to_show.replace(" >/dev/null 2>&1", "").replace(os.path.expanduser("~"), "~")
            idx_str = f"{current_idx + 1:02d}/{num_opts:02d}"
            if is_danger:
                sys.stderr.write(f"\r\x1b[K\033[1;31m▲ WARNING: Destructive payload detected\033[0m\n\r\x1b[K\033[2m[\033[1;31m{idx_str}\033[0;2m]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n\r\x1b[K\033[2m::\033[0m execute payload? [y/N]: ")
            else:
                sys.stderr.write(f"\r\x1b[K\033[1;32m[{idx_str}]\033[0m ❯ \x1b[1;36m[{current_intent}]\x1b[0m {display_cmd}\n\r\x1b[K\033[2m::\033[0m ↵ run  Esc: ")
            sys.stderr.flush()
            key = get_key()
            if key in ('\x03', '\x1b') or (not is_danger and key not in ('\r', '', '\x1b[A', '\x1b[B')):
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n"); sys.stderr.flush(); break
            if is_danger:
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K\x1b[1A\r\x1b[K"); sys.stderr.flush()
                if key.lower() == 'y':
                    if "system" in cmd_to_show: ensure_mysys_exists()
                    sys.stdout.write(cmd_to_show)
                else: sys.stderr.write("Aborted safely.\n")
                sys.stdout.flush(); break
            if key in ('\r', ''):
                sys.stderr.write("\n"); sys.stderr.flush()
                if "system" in cmd_to_show: ensure_mysys_exists()
                sys.stdout.write(cmd_to_show); sys.stdout.flush(); break
            elif key in ('\x1b[A', '\x1b[B'):
                current_idx = (current_idx + (1 if key == '\x1b[B' else -1) + num_opts) % num_opts
                sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[K")
        sys.exit(0)
    except KeyboardInterrupt:
        sys.stderr.write("\r\x1b[K\x1b[1A\r\x1b[KCancelled.\n"); sys.stderr.flush(); sys.exit(130)
    finally: sys.stderr.write("\033[?25h"); sys.stderr.flush()
