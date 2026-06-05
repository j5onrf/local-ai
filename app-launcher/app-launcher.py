#!/usr/bin/env python3
# Ultra-Lightweight Terminal App Launcher v0.1.3

import os
import sys
import glob
import re
import subprocess
import tty
import termios
import select

def get_apps():
    """Scan and parse desktop entry files dynamically resolving XDG data paths."""
    apps = []
    
    # Dynamically resolve active system and local application directories
    xdg_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/share:/usr/local/share").split(":")
    paths = []
    for d in xdg_dirs:
        if d.strip():
            paths.append(os.path.join(d.strip(), "applications", "*.desktop"))
    # Add local user applications
    paths.append(os.path.expanduser("~/.local/share/applications/*.desktop"))
    
    seen_execs = set()
    
    for path_pattern in paths:
        for filepath in glob.glob(path_pattern):
            try:
                with open(filepath, "r", errors="ignore") as f:
                    content = f.read()
                if "[Desktop Entry]" not in content:
                    continue
                
                # Parse strictly inside the [Desktop Entry] section to prevent Action blocks from overwriting
                entry = {}
                in_desktop_entry = False
                
                for line in content.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    # Section header check
                    if line.startswith("[") and line.endswith("]"):
                        if line == "[Desktop Entry]":
                            in_desktop_entry = True
                        else:
                            # Stop parsing once we leave the primary entry block (ignores secondary Actions)
                            in_desktop_entry = False
                        continue
                    
                    if in_desktop_entry and "=" in line:
                        k, v = line.split("=", 1)
                        entry[k.strip()] = v.strip()
                
                if entry.get("Type") != "Application":
                    continue
                if entry.get("NoDisplay") == "true":
                    continue
                
                name = entry.get("Name")
                exec_cmd = entry.get("Exec")
                
                if name and exec_cmd:
                    # Strip standard desktop field codes (%f, %F, %u, %U, etc.)
                    clean_exec = re.sub(r"%[fFuUiIcKkvd]", "", exec_cmd).strip()
                    clean_exec = clean_exec.strip('"').strip("'")
                    
                    if clean_exec and clean_exec not in seen_execs:
                        seen_execs.add(clean_exec)
                        apps.append({"name": name, "exec": clean_exec})
            except Exception:
                pass
    apps.sort(key=lambda x: x["name"].lower())
    return apps

def get_key():
    """Capture raw terminal keystrokes in non-blocking raw mode."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        r = os.read(fd, 1)
        if r == b'\x1b' and select.select([fd], [], [], 0.05)[0]:
            r += os.read(fd, 2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return r

def main():
    apps = get_apps()
    query = ""
    selected_idx = 0
    
    # Hide terminal cursor during interactive selection
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while True:
            # Dynamically filter matches based on query
            filtered = [a for a in apps if query.lower() in a["name"].lower()]
            
            # Constrain selection index
            if selected_idx >= len(filtered):
                selected_idx = max(0, len(filtered) - 1)
            
            # Reposition cursor and clear screen using standard ANSI escapes
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write("\033[1;36m🚀 App Launcher\033[0m\n")
            sys.stdout.write(f"\033[1;30mSearch:\033[0m {query}_\n")
            sys.stdout.write("\033[90m────────────────────────────────────────\033[0m\n")
            
            # Display vertical sliding window of top 10 matches
            start_idx = max(0, selected_idx - 5)
            end_idx = min(len(filtered), start_idx + 10)
            
            for i in range(start_idx, end_idx):
                app = filtered[i]
                if i == selected_idx:
                    sys.stdout.write(f"\033[1;32m❯ {app['name']}\033[0m \033[90m({app['exec']})\033[0m\n")
                else:
                    sys.stdout.write(f"  {app['name']}\n")
            
            if not filtered:
                sys.stdout.write("\033[1;31mNo matching applications found.\033[0m\n")
                
            sys.stdout.flush()
            
            # Wait for keystroke
            key = get_key()
            
            # ENTER: Detach process and launch
            if key in (b'\r', b'\n'):
                if filtered:
                    target = filtered[selected_idx]
                    with open(os.devnull, 'wb') as devnull:
                        # start_new_session completely detaches the child process from parent TTY
                        subprocess.Popen(target["exec"], shell=True, stdout=devnull, stderr=devnull, close_fds=True, start_new_session=True)
                    sys.stdout.write("\033[2J\033[H")
                    sys.stdout.flush()
                break
                
            # ESC or CTRL+C: Safe exit
            elif key in (b'\x1b', b'\x03'):
                sys.stdout.write("\033[2J\033[H")
                sys.stdout.flush()
                break
                
            # BACKSPACE
            elif key in (b'\x7f', b'\x08'):
                query = query[:-1]
                selected_idx = 0
                
            # ARROW UP
            elif key == b'\x1b[A':
                if filtered:
                    selected_idx = (selected_idx - 1) % len(filtered)
                    
            # ARROW DOWN
            elif key == b'\x1b[B':
                if filtered:
                    selected_idx = (selected_idx + 1) % len(filtered)
                    
            # Printable characters
            elif len(key) == 1 and 32 <= ord(key) < 127:
                query += key.decode("utf-8")
                selected_idx = 0
    finally:
        # Restore native cursor settings on exit
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
