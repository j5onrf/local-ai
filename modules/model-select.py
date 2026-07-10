#!/usr/bin/env python3
# model-select.py - Fully Dynamic TUI Model Selector driven by OpenRouter Rankings
import os
import sys
import re
import json
import tty
import termios
import shutil
import subprocess
import select
import requests

ENV_PATH = os.path.expanduser("~/.config/local-ai/.env")
CACHE_PATH = os.path.expanduser("~/.config/local-ai/.openrouter_cache_v2.json")

# Fallback defaults used on cold-boots before first API refresh
GEMINI_CURATED = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

OPENAI_CURATED = [
    "gpt-5.5",
    "gpt-5",
    "o3",
    "o3-mini",
    "gpt-4o",
    "gpt-4o-mini"
]

CLAUDE_CURATED = [
    "claude-fable-5",
    "claude-sonnet-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6"
]

GROK_CURATED = [
    "grok-4.5",
    "grok-4",
    "grok-3",
    "grok-2"
]

OR_FREE_DEFAULTS = [
    "openrouter/free",
    "nvidia/nemotron-3-ultra:free",
    "poolside/laguna-m.1:free",
    "tencent/hy3:free",
    "google/gemma-4-26b-a4b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat:free",
    "microsoft/phi-4:free",
    "mistralai/mistral-nemo:free"
]

OR_PAID_DEFAULTS = [
    "deepseek/deepseek-v4-flash",
    "xiaomi/mimo-v2.5",
    "minimax/minimax-m3",
    "tencent/hy3",
    "z-ai/glm-5.2",
    "deepseek/deepseek-v4-pro",
    "anthropic/claude-opus-4.7",
    "anthropic/claude-opus-4.8",
    "stepfun/step-3.7-flash",
    "anthropic/claude-sonnet-4.6",
    "openai/gpt-5.5",
    "anthropic/claude-sonnet-5",
    "xiaomi/mimo-v2.5-pro",
    "openai/gpt-4o-mini",
    "openai/gpt-oss-120b"
]

# --- DYNAMIC RANKINGS CLASSIFICATION ENGINE ---
def classify_openrouter_models(raw_data):
    """Parses live API listings, categorizing and mapping identifiers for all platforms."""
    if not isinstance(raw_data, list):
        return OR_FREE_DEFAULTS, OR_PAID_DEFAULTS, GEMINI_CURATED, CLAUDE_CURATED, OPENAI_CURATED, GROK_CURATED
        
    free_candidates = []
    paid_candidates = []
    gemini_candidates = []
    openai_candidates = []
    claude_candidates = []
    grok_candidates = []
    
    for item in raw_data:
        model_id = item.get("id", "")
        if not model_id:
            continue
            
        # Parse direct API endpoints from OpenRouter namespace rules
        if model_id.startswith("google/gemini"):
            direct_id = model_id.split("/", 1)[1]
            direct_id = direct_id.split(":")[0]  # Strip parameters
            if direct_id not in gemini_candidates:
                gemini_candidates.append(direct_id)
        elif model_id.startswith("openai/"):
            direct_id = model_id.split("/", 1)[1]
            direct_id = direct_id.split(":")[0]
            if direct_id not in openai_candidates:
                openai_candidates.append(direct_id)
        elif model_id.startswith("anthropic/"):
            direct_id = model_id.split("/", 1)[1]
            direct_id = direct_id.split(":")[0]
            if direct_id not in claude_candidates:
                claude_candidates.append(direct_id)
        elif model_id.startswith("x-ai/"):
            direct_id = model_id.split("/", 1)[1]
            direct_id = direct_id.split(":")[0]
            if direct_id not in grok_candidates:
                grok_candidates.append(direct_id)
            
        # Filter OpenRouter-specific UI lists (skipping duplicate Gemini routes)
        if "google/gemini" in model_id.lower() or "google/gemini" in item.get("name", "").lower():
            continue
            
        is_free = False
        pricing = item.get("pricing", {})
        if "free" in model_id.lower():
            is_free = True
        elif pricing:
            prompt_cost = float(pricing.get("prompt", 0))
            completion_cost = float(pricing.get("completion", 0))
            if prompt_cost == 0 and completion_cost == 0:
                is_free = True
                
        if is_free:
            if model_id not in free_candidates:
                free_candidates.append(model_id)
        else:
            if model_id not in paid_candidates:
                paid_candidates.append(model_id)
                
    # Fallback to standard hardcoded curated lines if connection yielded empty results
    free_candidates = free_candidates or OR_FREE_DEFAULTS
    paid_candidates = paid_candidates or OR_PAID_DEFAULTS
    gemini_candidates = gemini_candidates or GEMINI_CURATED
    openai_candidates = openai_candidates or OPENAI_CURATED
    claude_candidates = claude_candidates or CLAUDE_CURATED
    grok_candidates = grok_candidates or GROK_CURATED
    
    # Always prioritize default OpenRouter free routing at the top
    if "openrouter/free" in free_candidates:
        free_candidates.remove("openrouter/free")
    free_candidates = ["openrouter/free"] + free_candidates
    
    return free_candidates, paid_candidates, gemini_candidates, claude_candidates, openai_candidates, grok_candidates

# --- STORAGE HANDLING ---
def load_env_vars():
    vars_dict = {
        "GEMINI_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "CLAUDE_API_KEY": "",
        "OPENAI_API_KEY": "",
        "XAI_API_KEY": "",
        "CLOUD_MODEL": "gemini-3.1-flash-lite",
        "OPENROUTER_MODEL": "openrouter/free",
        "CLAUDE_MODEL": "claude-fable-5",
        "OPENAI_MODEL": "gpt-5.5",
        "XAI_MODEL": "grok-4.5"
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

def is_key_active(key):
    if not os.path.exists(ENV_PATH):
        return False
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                return True
    return False

def set_key_commented_state(key, should_comment):
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    updated = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if f"{key}=" in stripped or f"{key} =" in stripped:
            assignment = stripped.lstrip("#").strip()
            lines[i] = f"#{assignment}\n" if should_comment else f"{assignment}\n"
            updated = True
            break
            
    # If the key does not exist at all, append a default placeholder to activate it
    if not updated and not should_comment:
        placeholder_map = {
            "GEMINI_API_KEY": "AIzaSyYourFullGeminiApiKeyHere",
            "OPENROUTER_API_KEY": "sk-or-v1-YourFullOpenRouterKeyHere",
            "CLAUDE_API_KEY": "your-claude-api-key-here",
            "OPENAI_API_KEY": "your-openai-api-key-here",
            "XAI_API_KEY": "xai-your-grok-api-key-here"
        }
        val = placeholder_map.get(key, "your-key-here")
        lines.append(f'{key}="{val}"\n')
        
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

def toggle_env_api_keys():
    if not os.path.exists(ENV_PATH):
        return False
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    is_commented = False
    target_keys = {"GEMINI_API_KEY", "OPENROUTER_API_KEY", "CLAUDE_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY"}
    
    for line in lines:
        for k in target_keys:
            if k in line:
                if line.strip().startswith("#"):
                    is_commented = True
                break

    new_lines = []
    for line in lines:
        matched_key = None
        for k in target_keys:
            if k in line:
                matched_key = k
                break
        if matched_key:
            stripped = line.strip()
            assignment = stripped.lstrip("#").strip()
            if is_commented:
                line = f"{assignment}\n"
            else:
                line = f"#{assignment}\n"
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
                free = data.get("free", OR_FREE_DEFAULTS)
                paid = data.get("paid", OR_PAID_DEFAULTS)
                gemini = data.get("gemini", GEMINI_CURATED)
                claude = data.get("claude", CLAUDE_CURATED)
                openai = data.get("openai", OPENAI_CURATED)
                grok = data.get("grok", GROK_CURATED)
                return free, paid, gemini, claude, openai, grok
        except Exception:
            pass
    return OR_FREE_DEFAULTS, OR_PAID_DEFAULTS, GEMINI_CURATED, CLAUDE_CURATED, OPENAI_CURATED, GROK_CURATED

def save_cached_lists(free_list, paid_list, gemini_list, claude_list, openai_list, grok_list):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "free": free_list,
                "paid": paid_list,
                "gemini": gemini_list,
                "claude": claude_list,
                "openai": openai_list,
                "grok": grok_list
            }, f, indent=2)
    except Exception:
        pass

def fetch_openrouter_models(api_key):
    try:
        url = "https://openrouter.ai/api/v1/models?sort=top-weekly"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        res = requests.get(url, headers=headers, timeout=8)
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
        tty.setraw(fd)
        ch_bytes = os.read(fd, 1)
        if not ch_bytes:
            return None
        ch = ch_bytes.decode('utf-8', errors='ignore')
        if ch == '\x1b':
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                seq_bytes = os.read(fd, 2)
                seq = seq_bytes.decode('utf-8', errors='ignore')
                if seq == '[A': return 'up'
                elif seq == '[B': return 'down'
                elif seq == '[C': return 'right'
                elif seq == '[D': return 'left'
            return 'esc'
        elif ch in ('\r', '\n'):
            return 'enter'
        elif ch in ('\x7f', '\x08'):
            return 'backspace'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def draw_main_menu(selected, gemini_curr, claude_curr, openai_curr, grok_curr, or_curr, message=""):
    sys.stdout.write("\x1b[H\x1b[2J")
    
    amber = "\033[38;2;230;120;60m"
    green = "\033[1;32m"
    red = "\033[1;31m"
    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[90m"
    
    gemini_active = is_key_active("GEMINI_API_KEY")
    or_active = is_key_active("OPENROUTER_API_KEY")
    claude_active = is_key_active("CLAUDE_API_KEY")
    openai_active = is_key_active("OPENAI_API_KEY")
    grok_active = is_key_active("XAI_API_KEY")
    
    keys_active = gemini_active or or_active or claude_active or openai_active or grok_active
    status_text = f"{green}[ ENABLED ]{reset}" if keys_active else f"{red}[ DISABLED ]{reset}"
    
    gemini_display = f"{green}{gemini_curr}{reset}" if gemini_active else f"{red}DISABLED{reset}"
    openai_display = f"{green}{openai_curr}{reset}" if openai_active else f"{red}DISABLED{reset}"
    claude_display = f"{green}{claude_curr}{reset}" if claude_active else f"{red}DISABLED{reset}"
    grok_display = f"{green}{grok_curr}{reset}" if grok_active else f"{red}DISABLED{reset}"
    
    is_or_free = "free" in or_curr.lower()
    or_free_display = f"{green}{or_curr}{reset}" if (or_active and is_or_free) else f"{dim}None selected{reset}"
    or_paid_display = f"{green}{or_curr}{reset}" if (or_active and not is_or_free) else f"{dim}None selected{reset}"
    
    sys.stdout.write(f"\n   {bold}  LOCAL-AI CONFIGURATION{reset}\n")
    sys.stdout.write(f"   {dim}────────────────────────────────────────────────────────────{reset}\n\n")
    
    options = [
        f"🔌  Cloud Connection      {status_text}",
        f"♊  Google Gemini          {gemini_display}\n       {dim}Select from curated, lightweight Google endpoints{reset}",
        f"🍎  OpenAI Subscription    {openai_display}\n       {dim}Select from direct, high-performance OpenAI engines{reset}",
        f"☕  Anthropic Claude       {claude_display}\n       {dim}Select from direct, industry-leading Claude models{reset}",
        f"🚀  x.AI Grok              {grok_display}\n       {dim}Select from direct, ultra-high-speed Grok engines{reset}",
        f"🌐  OpenRouter Free       {or_free_display}\n       {dim}Select from the top 20 most popular free models{reset}",
        f"🌐  OpenRouter Paid       {or_paid_display}\n       {dim}Select from the top 20 industry leading paid engines{reset}",
        f"↺  Refresh API Lists      {dim}Query OpenRouter for current model rankings{reset}",
        f"✕  Save & Close"
    ]
    
    for i, opt in enumerate(options):
        # Dynamically map spacing offsets to fit the new selection lineup
        spacing = "\n" if i in (1, 2, 3, 4, 5, 6) else ""
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

def run_selector(title, full_models_list, current, key_name):
    state = {
        "showing_all": False,
        "search_query": ""
    }
    
    def get_filtered_list():
        if not state["search_query"]:
            return full_models_list
        return [m for m in full_models_list if state["search_query"].lower() in m.lower()]
        
    def get_menu_options():
        filtered = get_filtered_list()
        sub_list = filtered if (state["showing_all"] or state["search_query"]) else filtered[:20]
        return [f"🚫 Turn Off {title}"] + sub_list
        
    menu_options = get_menu_options()
    selected = 0
    is_active = is_key_active(key_name)
    if is_active and current in menu_options:
        selected = menu_options.index(current)
        
    amber = "\033[38;2;230;120;60m"
    green = "\033[1;32m"
    red = "\033[1;31m"
    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[90m"
    max_visible = 14
    
    while True:
        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.write(f"\n   {bold}  SELECT {title.upper()}:{reset}\n")
        sys.stdout.write(f"   {dim}────────────────────────────────────────────────────────────{reset}\n\n")
        
        if state["search_query"]:
            sys.stdout.write(f"   🔍  Filter: {green}{state['search_query']}{amber}_{reset}\n\n")
            
        start = max(0, selected - max_visible // 2)
        end = min(len(menu_options), start + max_visible)
        if end - start < max_visible:
            start = max(0, end - max_visible)
            
        for i in range(start, end):
            opt_name = menu_options[i]
            active_bullet = f"{amber}❯{reset} " if i == selected else "  "
            
            if i == 0:
                if not is_active:
                    display_line = f"{active_bullet}{red}{opt_name} {dim}(currently disabled){reset}"
                else:
                    display_line = f"{active_bullet}{opt_name}"
            else:
                if opt_name == current and is_active:
                    display_line = f"{active_bullet}{green}{opt_name} {dim}(active){reset}"
                else:
                    display_line = f"{active_bullet}{opt_name}"
                
            if i == selected:
                display_line = f"{bold}{display_line}{reset}"
                
            sys.stdout.write(f"     {display_line}\n")
            
        more_above = start > 0
        more_below = end < len(menu_options)
        
        if more_below and more_above:
            indicator = " ▲ ▼ "
        elif more_below:
            indicator = " ▼ more below "
        elif more_above:
            indicator = " ▲ more above "
        else:
            indicator = ""
            
        total_len = 60
        if indicator:
            pad_len = (total_len - len(indicator)) // 2
            div_char = "─"
            divider_line = f"   {dim}{div_char * pad_len}{amber}{indicator}{dim}{div_char * (total_len - pad_len - len(indicator))}{reset}"
        else:
            divider_line = f"   {dim}────────────────────────────────────────────────────────────{reset}"
            
        sys.stdout.write(f"\n{divider_line}\n")
        
        if state["search_query"]:
            hint = f"Found {len(menu_options) - 1} matches. Backspace to edit, Esc to clear filter."
        elif not state["showing_all"]:
            hint = f"Showing Top 20. Press ► (Right Arrow) to view all {len(full_models_list)} models."
        else:
            hint = f"Showing All {len(full_models_list)} models. Press ◄ (Left Arrow) to return to Top 20."
            
        sys.stdout.write(f"   {dim}{hint}{reset}\n")
        sys.stdout.write(f"   {dim}Press Enter to apply, or type characters to filter instantly.{reset}\n")
        sys.stdout.flush()
        
        key = get_key()
        if key == 'up':
            selected = (selected - 1) % len(menu_options)
        elif key == 'down':
            selected = (selected + 1) % len(menu_options)
        elif key == 'backspace':
            if state["search_query"]:
                state["search_query"] = state["search_query"][:-1]
                selected = 0
                menu_options = get_menu_options()
        elif key == 'esc':
            if state["search_query"]:
                state["search_query"] = ""
                selected = 0
                menu_options = get_menu_options()
            else:
                return None
        elif key == 'right' and not state["showing_all"]:
            state["showing_all"] = True
            selected_model = menu_options[selected]
            menu_options = get_menu_options()
            if selected_model in menu_options:
                selected = menu_options.index(selected_model)
            else:
                selected = min(selected, len(menu_options) - 1)
        elif key == 'left' and state["showing_all"]:
            state["showing_all"] = False
            selected_model = menu_options[selected]
            menu_options = get_menu_options()
            if selected_model in menu_options:
                selected = menu_options.index(selected_model)
            else:
                selected = min(selected, len(menu_options) - 1)
        elif key == 'enter':
            if selected == 0:
                return "DISABLE"
            return menu_options[selected]
        elif isinstance(key, str) and len(key) == 1:
            if key.isalnum() or key in ('-', ':', '/', '.', '_'):
                state["search_query"] += key
                selected = 0
                menu_options = get_menu_options()

# --- MAIN ENGINE ---
def main():
    # Hide terminal cursor on entry
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    env = load_env_vars()
    gemini_curr = env["CLOUD_MODEL"]
    openai_curr = env.get("OPENAI_MODEL", "gpt-5.5")
    claude_curr = env.get("CLAUDE_MODEL", "claude-fable-5")
    grok_curr = env.get("XAI_MODEL", "grok-4.5")
    or_curr = env["OPENROUTER_MODEL"]
    
    or_free_list, or_paid_list, gemini_list, claude_list, openai_list, grok_list = load_cached_lists()
    
    if "openrouter/free" in or_free_list:
        or_free_list.remove("openrouter/free")
    or_free_list = ["openrouter/free"] + or_free_list
    
    selected_idx = 0
    message = ""
    total_options = 9
    
    try:
        while True:
            draw_main_menu(selected_idx, gemini_curr, claude_curr, openai_curr, grok_curr, or_curr, message)
            message = ""
            key = get_key()
            
            if key == 'up':
                selected_idx = (selected_idx - 1) % total_options
            elif key == 'down':
                selected_idx = (selected_idx + 1) % total_options
            elif key == 'enter':
                if selected_idx == 0:  # Toggle Cloud Connections (Master Switch)
                    is_now_enabled = toggle_env_api_keys()
                    env = load_env_vars()
                    status_text = f"\033[1;32mENABLED\033[0m" if is_now_enabled else f"\033[1;31mDISABLED\033[0m"
                    message = f"✓ Switched Cloud Connection to: {status_text}"
                elif selected_idx == 1:  # Gemini
                    res = run_selector("Gemini", gemini_list, gemini_curr, "GEMINI_API_KEY")
                    if res == "DISABLE":
                        set_key_commented_state("GEMINI_API_KEY", True)
                        message = "✓ Gemini disabled."
                    elif res:
                        gemini_curr = res
                        set_key_commented_state("GEMINI_API_KEY", False)
                        update_env("CLOUD_MODEL", gemini_curr)
                        message = f"✓ Saved CLOUD_MODEL={gemini_curr} and re-enabled Gemini API Key."
                elif selected_idx == 2:  # OpenAI
                    res = run_selector("OpenAI", openai_list, openai_curr, "OPENAI_API_KEY")
                    if res == "DISABLE":
                        set_key_commented_state("OPENAI_API_KEY", True)
                        message = "✓ OpenAI disabled."
                    elif res:
                        openai_curr = res
                        set_key_commented_state("OPENAI_API_KEY", False)
                        update_env("OPENAI_MODEL", openai_curr)
                        message = f"✓ Saved OPENAI_MODEL={openai_curr} and re-enabled OpenAI API Key."
                elif selected_idx == 3:  # Claude
                    res = run_selector("Claude", claude_list, claude_curr, "CLAUDE_API_KEY")
                    if res == "DISABLE":
                        set_key_commented_state("CLAUDE_API_KEY", True)
                        message = "✓ Claude disabled."
                    elif res:
                        claude_curr = res
                        set_key_commented_state("CLAUDE_API_KEY", False)
                        update_env("CLAUDE_MODEL", claude_curr)
                        message = f"✓ Saved CLAUDE_MODEL={claude_curr} and re-enabled Claude API Key."
                elif selected_idx == 4:  # Grok
                    res = run_selector("Grok", grok_list, grok_curr, "XAI_API_KEY")
                    if res == "DISABLE":
                        set_key_commented_state("XAI_API_KEY", True)
                        message = "✓ Grok disabled."
                    elif res:
                        grok_curr = res
                        set_key_commented_state("XAI_API_KEY", False)
                        update_env("XAI_MODEL", grok_curr)
                        message = f"✓ Saved XAI_MODEL={grok_curr} and re-enabled Grok API Key."
                elif selected_idx == 5:  # OR Free
                    res = run_selector("OpenRouter Free", or_free_list, or_curr, "OPENROUTER_API_KEY")
                    if res == "DISABLE":
                        set_key_commented_state("OPENROUTER_API_KEY", True)
                        message = "✓ OpenRouter disabled."
                    elif res:
                        or_curr = res
                        set_key_commented_state("OPENROUTER_API_KEY", False)
                        update_env("OPENROUTER_MODEL", or_curr)
                        message = f"✓ Saved OPENROUTER_MODEL={or_curr} and re-enabled OpenRouter Key."
                elif selected_idx == 6:  # OR Paid
                    res = run_selector("OpenRouter Paid", or_paid_list, or_curr, "OPENROUTER_API_KEY")
                    if res == "DISABLE":
                        set_key_commented_state("OPENROUTER_API_KEY", True)
                        message = "✓ OpenRouter disabled."
                    elif res:
                        or_curr = res
                        set_key_commented_state("OPENROUTER_API_KEY", False)
                        update_env("OPENROUTER_MODEL", or_curr)
                        message = f"✓ Saved OPENROUTER_MODEL={or_curr} and re-enabled OpenRouter Key."
                elif selected_idx == 7:  # Refresh API lists
                    message = "\033[1;33m↺ Checking OpenRouter for current model rankings...\033[0m"
                    draw_main_menu(selected_idx, gemini_curr, claude_curr, openai_curr, grok_curr, or_curr, message)
                    raw_data = fetch_openrouter_models(env["OPENROUTER_API_KEY"])
                    if raw_data:
                        or_free_list, or_paid_list, gemini_list, claude_list, openai_list, grok_list = classify_openrouter_models(raw_data)
                        save_cached_lists(or_free_list, or_paid_list, gemini_list, claude_list, openai_list, grok_list)
                        message = f"✓ Dynamic model rankings & provider APIs synchronized."
                    else:
                        message = "\033[1;31m✗ Connection failed. Keeping cached defaults."
                elif selected_idx == 8:  # Close
                    break
            elif key == 'q':
                break
    finally:
        sys.stdout.write("\x1b[H\x1b[2J")
        # Restore terminal cursor on exit
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
