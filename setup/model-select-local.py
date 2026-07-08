#!/usr/bin/env python3
# model-select-local.py - Standalone Local Offline Model Selector
import os
import sys
import re
import tty
import termios
import shutil
import subprocess
import select
import time

MODELS_DIR = "/home/user/models"
SERV_DIR = "/home/user/models/serv"

# Map local GGUF filenames to their respective launch scripts
LOCAL_MODELS = [
    {
        "name": "Qwen 3.5 2B (Ultra-Light)",
        "file": "Qwen3.5-2B.gguf",
        "script": "q2b.sh"
    },
    {
        "name": "Qwen 3.6 35B (4-bit Uncensored)",
        "file": "Qwen3.6-35B-A3B.gguf",
        "script": "q35b.sh"
    },
        {
        "name": "Qwen 3.6 35B (4-bit Reasoning-On)",
        "file": "Qwen3.6-35B-A3B.gguf",
        "script": "q35b-on.sh"
    }
]

# --- PROCESS STATUS DETECTION ---
def get_current_running_model():
    """Checks the system processes to identify the currently running GGUF model."""
    try:
        output = subprocess.check_output(["pgrep", "-af", "llama-server"]).decode()
        for line in output.splitlines():
            # Parse command line execution to extract model path
            match = re.search(r"-m\s+([^\s]+)", line)
            if match:
                model_path = match.group(1)
                return os.path.basename(model_path)
    except Exception:
        pass
    return None

# --- POWER CLEAN ENGINE (PORTED FROM YOUR SCRIPT) ---
def stop_all_engines():
    """SIGTERM targets, polls to ensure termination, escalates to SIGKILL, and flushes RAM caches."""
    targets = ["llama-server", "llama-cli"]
    for target in targets:
        try:
            pids = subprocess.check_output(["pgrep", "-x", target]).decode().split()
        except Exception:
            pids = []
            
        if pids:
            # 1. Clean stop (SIGTERM)
            for pid in pids:
                try:
                    os.kill(int(pid), 15)
                except Exception:
                    pass
            
            # 2. Wait up to 2 seconds for memory mapping to release
            terminated = False
            for _ in range(20):
                time.sleep(0.1)
                try:
                    subprocess.check_output(["pgrep", "-x", target])
                except Exception:
                    terminated = True
                    break
                    
            # 3. Force stop (SIGKILL) if hanging
            if not terminated:
                for pid in pids:
                    try:
                        os.kill(int(pid), 9)
                    except Exception:
                        pass
                        
    # 4. Clean up terminal agent processes
    subprocess.run(["pkill", "-f", "AI "], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "uvicorn"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 5. Drop file caches to free physical memory immediately
    try:
        subprocess.run(["sudo", "sync"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run("echo 3 | sudo tee /proc/sys/vm/drop_caches", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "AI Engine", "All Engines & Windows Shutdown", "-i", "system-shutdown"])

# --- PROCESS LAUNCHING ---
def launch_local_server(script_name):
    """Detaches execution into a background group to keep server running post-TUI exit."""
    script_path = os.path.join(SERV_DIR, script_name)
    if not os.path.exists(script_path):
        return False
    try:
        subprocess.Popen(
            [script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Completely detach session
        )
        return True
    except Exception:
        return False

# --- INPUT CAPTURING ---
def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch_bytes = os.read(fd, 1)
        if not ch_bytes:
            return None
        ch = ch_bytes.decode('utf-8', errors='ignore')
        if ch == '\x1b':
            rlist, _, _ = select.select([fd], [], [], 0.05)
            if rlist:
                seq_bytes = os.read(fd, 2)
                seq = seq_bytes.decode('utf-8', errors='ignore')
                if seq == '[A': return 'up'
                elif seq == '[B': return 'down'
            return 'esc'
        elif ch in ('\r', '\n'):
            return 'enter'
        elif ch.lower() == 'q':
            return 'q'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# --- GRAPHICAL INTERFACE REDRAWING ---
def draw_menu(selected, active_model, message=""):
    sys.stdout.write("\x1b[H\x1b[2J")
    
    amber = "\033[38;2;230;120;60m"
    green = "\033[1;32m"
    red = "\033[1;31m"
    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[90m"
    
    sys.stdout.write(f"\n   {bold}  LOCAL-AI OFFLINE WORKSPACE{reset}\n")
    sys.stdout.write(f"   {dim}────────────────────────────────────────────────────────────{reset}\n\n")
    
    for i, model in enumerate(LOCAL_MODELS):
        is_active = (model["file"] == active_model)
        status_suffix = f" {green}(active){reset}" if is_active else ""
        
        opt_text = f"Run {model['name']}{status_suffix}\n       {dim}Start backend container for {model['file']}{reset}"
        
        if i == selected:
            sys.stdout.write(f"   {amber}❯{reset}  {bold}{opt_text}{reset}\n\n")
        else:
            sys.stdout.write(f"      {opt_text}\n\n")
            
    # Draw additional options
    stop_idx = len(LOCAL_MODELS)
    exit_idx = len(LOCAL_MODELS) + 1
    
    # Render Free-RAM Option
    if selected == stop_idx:
        sys.stdout.write(f"   {amber}❯{reset}  {bold}🚫  Unload All Local Models {dim}(Free System RAM){reset}\n\n")
    else:
        sys.stdout.write(f"      🚫  Unload All Local Models {dim}(Free System RAM){reset}\n\n")
        
    # Render Exit Option
    if selected == exit_idx:
        sys.stdout.write(f"   {amber}❯{reset}  {bold}✕   Close Settings{reset}\n")
    else:
        sys.stdout.write(f"      ✕   Close Settings\n")
        
    sys.stdout.write(f"\n   {dim}────────────────────────────────────────────────────────────{reset}\n")
    if message:
        sys.stdout.write(f"   {message}\n")
    else:
        sys.stdout.write(f"   {dim}Use ▲/▼ Arrows to choose local server, Enter to initialize.{reset}\n")
    sys.stdout.flush()

# --- MAIN EXECUTION PIPELINE ---
def main():
    selected = 0
    total_options = len(LOCAL_MODELS) + 2
    message = ""
    
    try:
        while True:
            active_model = get_current_running_model()
            draw_menu(selected, active_model, message)
            message = ""
            key = get_key()
            
            if key == 'up':
                selected = (selected - 1) % total_options
            elif key == 'down':
                selected = (selected + 1) % total_options
            elif key == 'enter':
                if selected < len(LOCAL_MODELS):  # Switch and launch model
                    target_model = LOCAL_MODELS[selected]
                    
                    if target_model["file"] == active_model:
                        message = f"\033[1;33mℹ {target_model['file']} is already active and running.\033[0m"
                        continue
                        
                    message = "\033[1;33m↺ Releasing current server and flushing RAM pages...\033[0m"
                    draw_menu(selected, active_model, message)
                    
                    # Stop running servers
                    stop_all_engines()
                    
                    # Launch target
                    if launch_local_server(target_model["script"]):
                        message = f"\033[1;32m✓ Initialized {target_model['name']} on Port 8080.\033[0m"
                    else:
                        message = f"\033[1;31m✗ Failed to execute {target_model['script']}.\033[0m"
                        
                elif selected == len(LOCAL_MODELS):  # Clean exit/Stop all
                    message = "\033[1;33m↺ Shutting down active local engines...\033[0m"
                    draw_menu(selected, active_model, message)
                    stop_all_engines()
                    message = "\033[1;32m✓ Engines stopped. Local RAM cleared successfully.\033[0m"
                elif selected == len(LOCAL_MODELS) + 1:  # Close settings
                    break
            elif key == 'q':
                break
    finally:
        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
