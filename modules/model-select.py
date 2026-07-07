#!/usr/bin/env python3
# model-select.py - Minimalist Model Selector TUI 
import os
import sys
import re
import json
import tty
import termios
import shutil
import subprocess
import requests

ENV_PATH = os.path.expanduser("~/.config/local-ai/.env")
CACHE_PATH = os.path.expanduser("~/.config/local-ai/.openrouter_cache_v2.json")

GEMINI_CURATED = [
    "gemini-3.5-flash",
    "gemini-3.5-pro",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

OR_FREE_DEFAULTS = [
    "openrouter/free",
    "tencent/hy3:free",
    "google/gemini-2.5-flash:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "microsoft/phi-4:free",
    "mistralai/mistral-nemo:free",
    "nvidia/llama-3.1-nemotron-70b-instruct:free"
]

OR_PAID_DEFAULTS = [
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "deepseek/deepseek-r1",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "meta-llama/llama-3.3-70b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "deepseek/deepseek-chat",
    "openai/o3-mini",
    "qwen/qwen-2.5-coder-32b-instruct"
]

# --- REPUTATION-BASED CLASSIFICATION ENGINE ---
def classify_openrouter_models(raw_data):
    if not isinstance(raw_data, list):
        return OR_FREE_DEFAULTS, OR_PAID_DEFAULTS
        
    free_candidates = []
    paid_candidates = []
    
    # Curated leading paid models to look for and bubbles to top of list
    elite_paid_patterns = [
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "deepseek/deepseek-r1",
        "google/gemini-2.5-pro",
        "google/gemini-2.5-flash",
        "meta-llama/llama-3.3-70b-instruct",
        "qwen/qwen-2.5-72b-instruct",
        "deepseek/deepseek-chat",
        "qwen/qwen-2.5-coder-32b-instruct",
        "openai/o3-mini",
        "mistralai/mistral-large",
        "cohere/command-r-plus"
    ]
    
    # Priority organizations for free models
    free_priority_keywords = ["openrouter/free", "tencent", "google", "meta-llama", "deepseek", "qwen", "microsoft", "mistralai"]
    
    for item in raw_data:
        model_id = item.get("id", "")
        if not model_id:
            continue
        if "free" in model_id.lower():
            free_candidates.append(model_id)
        else:
            paid_candidates.append(model_id)
            
    # Process Free Top 20
    def free_sort_key(m):
        m_lower = m.lower()
        if m_lower == "openrouter/free":
            return -100
        for idx, kw in enumerate(free_priority_keywords):
            if kw in m_lower:
                return idx
        return 999
        
    sorted_free = sorted(list(set(free_candidates)), key=free_sort_key)
    top_20_free = sorted_free[:20]
    if "openrouter/free" in top_20_free:
        top_20_free.remove("openrouter/free")
        top_20_free = ["openrouter/free"] + top_20_free
        
    # Process Paid Top 20
    matched_paid = []
    for pattern in elite_paid_patterns:
        for p in paid_candidates:
            if pattern in p:
                matched_paid.append(p)
                
    unique_matched_paid = []
    for m in matched_paid:
        if m not in unique_matched_paid:
            unique_matched_paid.append(m)
            
    remaining_paid = [p for p in paid_candidates if p not in unique_matched_paid]
    top_20_paid = (unique_matched_paid + sorted(remaining_paid))[:20]
    
    return top_20_free, top_20_paid

# --- STORAGE HANDLING ---
def load_env_vars():
    vars_dict = {
        "GEMINI_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "CLOUD_MODEL": "gemini-3.1-flash-lite",
        "OPENROUTER_MODEL": "openrouter/free"
    }
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line_strip = line.strip()
                match = re.match(r"^#?\s*([A-Z0-9_]+)\s*=\s*\"?([^\"]*)\"?$", line_strip)
                if match:
                    key, val = match.groups()
                    if not line_strip.startswith("#") or not vars_dict.get(key):
                        vars_dict[key] = val
    return vars_dict

def update_env(key, value):
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    updated = False
    for i, line in enumerate(lines):
        match = re.match(rf"^#?\s*{key}\s*=\s*.*$", line)
        if match:
            is_commented = line.strip().startswith("#")
            prefix = "#" if is_commented else ""
            lines[i] = f'{prefix}{key}="{value}"\n'
            updated = True
            break
            
    if not updated:
        lines.append(f'{key}="{value}"\n')
        
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

def get_keys_status():
    if not os.path.exists(ENV_PATH):
        return False
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if "GEMINI_API_KEY" in line:
                return not line.strip().startswith("#")
    return False

def toggle_env_api_keys():
    if not os.path.exists(ENV_PATH):
        return False
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    is_commented = False
    for line in lines:
        if "GEMINI_API_KEY" in line:
            if line.strip().startswith("#"):
                is_commented = True
            break

    new_lines = []
    for line in lines:
        if "GEMINI_API_KEY" in line or "OPENROUTER_API_KEY" in line:
            stripped = line.lstrip()
            if is_commented:
                if stripped.startswith("#"):
                    line = stripped[1:]
            else:
                if not stripped.startswith("#"):
                    line = "#" + line
        new_lines.append(line)

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    if shutil.which("notify-send"):
        mode = "Cloud Mode (APIs Enabled)" if is_commented else "Local / Offline Mode (APIs Disabled)"
        subprocess.run(["notify-send", "AI Environment Toggle", f"Switched to {mode}", "-t", "2000"])
        
    return is_commented

def load_cached_lists():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("free", OR_FREE_DEFAULTS), data.get("paid", OR_PAID_DEFAULTS)
        except Exception:
            pass
    return OR_FREE_DEFAULTS, OR_PAID_DEFAULTS

def save_cached_lists(free_list, paid_list):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"free": free_list, "paid": paid_list}, f, indent=2)
    except Exception:
        pass

# --- API INTEGRATION ---
def fetch_openrouter_models(api_key):
    try:
        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            return res.json().get("data", [])
    except Exception:
        pass
    return None

# --- CONSOLE TUI DRAWING HELPERS ---
def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A': return 'up'
                elif ch3 == 'B': return 'down'
            return 'esc'
        elif ch in ('\r', '\n'):
            return 'enter'
        elif ch.lower() == 'q':
            return 'q'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def draw_main_menu(selected, gemini_curr, or_curr, message=""):
    sys.stdout.write("\x1b[H\x1b[2J")  # Absolute clear
    
    # Palette definition
    amber = "\033[38;2;230;120;60m"
    green = "\033[1;32m"
    red = "\033[1;31m"
    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[90m"
    
    keys_active = get_keys_status()
    status_text = f"{green}[ ENABLED ]{reset}" if keys_active else f"{red}[ DISABLED ]{reset}"
    
    # Curate display name
    is_or_free = "free" in or_curr.lower()
    or_free_display = f"{green}{or_curr}{reset}" if is_or_free else f"{dim}None selected{reset}"
    or_paid_display = f"{green}{or_curr}{reset}" if not is_or_free else f"{dim}None selected{reset}"
    
    sys.stdout.write(f"\n   {bold}  LOCAL-AI CONFIGURATION{reset}\n")
    sys.stdout.write(f"   {dim}────────────────────────────────────────────────────────────{reset}\n\n")
    
    options = [
        f"🔌  Cloud Connection      {status_text}",
        f"♊  Google Gemini          {green}{gemini_curr}{reset}\n       {dim}Select from curated, lightweight Google endpoints{reset}",
        f"🌐  OpenRouter Free       {or_free_display}\n       {dim}Select from the top 20 most popular free models{reset}",
        f"🌐  OpenRouter Paid       {or_paid_display}\n       {dim}Select from the top 20 industry leading paid engines{reset}",
        f"↺  Refresh API Lists      {dim}Query OpenRouter for new endpoints{reset}",
        f"✕  Save & Close"
    ]
    
    for i, opt in enumerate(options):
        # Spacing adjustment for options with subtitles
        spacing = "\n" if i in (1, 2, 3) else ""
        if i == selected:
            sys.stdout.write(f"   {amber}❯{reset}  {bold}{opt}{reset}\n{spacing}")
        else:
            sys.stdout.write(f"      {opt}\n{spacing}")
            
    sys.stdout.write(f"\n   {dim}────────────────────────────────────────────────────────────{reset}\n")
    if message:
        sys.stdout.write(f"   {message}\n")
    else:
        sys.stdout.write(f"   {dim}Use ▲/▼ Arrows to navigate, Enter to choose, Q to exit.{reset}\n")
    sys.stdout.flush()

def run_selector(title, models, current):
    selected = 0
    if current in models:
        selected = models.index(current)
        
    amber = "\033[38;2;230;120;60m"
    green = "\033[1;32m"
    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[90m"
    
    while True:
        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.write(f"\n   {bold}  SELECT {title.upper()}:{reset}\n")
        sys.stdout.write(f"   {dim}────────────────────────────────────────────────────────────{reset}\n\n")
        
        for i, m_name in enumerate(models):
            active_bullet = f"{amber}❯{reset} " if i == selected else "  "
            if m_name == current:
                display_line = f"{active_bullet}{green}{m_name} {dim}(active){reset}"
            else:
                display_line = f"{active_bullet}{m_name}"
                
            if i == selected:
                display_line = f"{bold}{display_line}{reset}"
                
            sys.stdout.write(f"     {display_line}\n")
            
        sys.stdout.write(f"\n   {dim}────────────────────────────────────────────────────────────{reset}\n")
        sys.stdout.write(f"   {dim}Press Enter to apply, or escape / Q to cancel.{reset}\n")
        sys.stdout.flush()
        
        key = get_key()
        if key == 'up':
            selected = (selected - 1) % len(models)
        elif key == 'down':
            selected = (selected + 1) % len(models)
        elif key == 'enter':
            return models[selected]
        elif key in ('esc', 'q'):
            return None

# --- MAIN ENGINE ---
def main():
    env = load_env_vars()
    gemini_curr = env["CLOUD_MODEL"]
    or_curr = env["OPENROUTER_MODEL"]
    
    or_free_list, or_paid_list = load_cached_lists()
    
    selected_idx = 0
    message = ""
    total_options = 6
    
    try:
        while True:
            draw_main_menu(selected_idx, gemini_curr, or_curr, message)
            message = ""
            key = get_key()
            
            if key == 'up':
                selected_idx = (selected_idx - 1) % total_options
            elif key == 'down':
                selected_idx = (selected_idx + 1) % total_options
            elif key == 'enter':
                if selected_idx == 0:  # Toggle keys
                    is_now_enabled = toggle_env_api_keys()
                    env = load_env_vars()
                    status_text = f"\033[1;32mENABLED\033[0m" if is_now_enabled else f"\033[1;31mDISABLED\033[0m"
                    message = f"✓ Switched Cloud Connection to: {status_text}"
                elif selected_idx == 1:  # Gemini list
                    res = run_selector("Gemini", GEMINI_CURATED, gemini_curr)
                    if res:
                        gemini_curr = res
                        update_env("CLOUD_MODEL", gemini_curr)
                        message = f"✓ Saved CLOUD_MODEL={gemini_curr} in .env"
                elif selected_idx == 2:  # OR Free list
                    res = run_selector("OpenRouter Free", or_free_list, or_curr)
                    if res:
                        or_curr = res
                        update_env("OPENROUTER_MODEL", or_curr)
                        message = f"✓ Saved OPENROUTER_MODEL={or_curr} in .env"
                elif selected_idx == 3:  # OR Paid list
                    res = run_selector("OpenRouter Paid", or_paid_list, or_curr)
                    if res:
                        or_curr = res
                        update_env("OPENROUTER_MODEL", or_curr)
                        message = f"✓ Saved OPENROUTER_MODEL={or_curr} in .env"
                elif selected_idx == 4:  # Refresh API lists
                    message = "\033[1;33m↺ Checking OpenRouter for new endpoints...\033[0m"
                    draw_main_menu(selected_idx, gemini_curr, or_curr, message)
                    raw_data = fetch_openrouter_models(env["OPENROUTER_API_KEY"])
                    if raw_data:
                        or_free_list, or_paid_list = classify_openrouter_models(raw_data)
                        save_cached_lists(or_free_list, or_paid_list)
                        message = f"✓ Successfully synchronized latest model arrays."
                    else:
                        message = "\033[1;31m✗ Connection failed. Keeping cached defaults.\033[0m"
                elif selected_idx == 5:  # Close
                    break
            elif key == 'q':
                break
    finally:
        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
