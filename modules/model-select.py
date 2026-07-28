#!/usr/bin/env python3
# model-select.py - Fully Dynamic TUI Model Selector driven by OpenRouter Rankings
# Path: ~/.config/local-ai/modules/model-select.py

try: import uvloop; uvloop.install()
except ImportError: pass

import asyncio, json, os, re, select, shutil, subprocess, sys, termios, tty
import urllib.request as urlreq

ENV_PATH = os.path.expanduser("~/.config/local-ai/.env")
CACHE_PATH = os.path.expanduser("~/.config/local-ai/.openrouter_cache_v2.json")

GEMINI_CURATED = ["gemini-3.5-flash-lite", "gemini-3.6-flash"]
OPENAI_CURATED = ["gpt-5.5", "gpt-5", "o3", "o3-mini", "gpt-4o", "gpt-4o-mini"]
CLAUDE_CURATED = ["claude-opus-5", "claude-fable-5", "claude-sonnet-5", "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6"]
GROK_CURATED = ["grok-4.5", "grok-4", "grok-3", "grok-2"]

OR_FREE_DEFAULTS = [
    "openrouter/free", "nvidia/nemotron-3-ultra:free", "poolside/laguna-m.1:free",
    "tencent/hy3:free", "google/gemma-4-26b-a4b:free", "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat:free", "microsoft/phi-4:free", "mistralai/mistral-nemo:free"
]

OR_PAID_DEFAULTS = [
    "deepseek/deepseek-v4-flash", "xiaomi/mimo-v2.5", "minimax/minimax-m3", "tencent/hy3",
    "z-ai/glm-5.2", "deepseek/deepseek-v4-pro", "anthropic/claude-opus-4.7", "anthropic/claude-opus-4.8",
    "stepfun/step-3.7-flash", "anthropic/claude-sonnet-4.6", "openai/gpt-5.5", "anthropic/claude-sonnet-5",
    "xiaomi/mimo-v2.5-pro", "openai/gpt-4o-mini", "openai/gpt-oss-120b"
]

def classify_openrouter_models(raw_data):
    if not isinstance(raw_data, list):
        return OR_FREE_DEFAULTS, OR_PAID_DEFAULTS, GEMINI_CURATED, CLAUDE_CURATED, OPENAI_CURATED, GROK_CURATED

    free_c, paid_c, gemini_c, openai_c, claude_c, grok_c = [], [], [], [], [], []

    for item in raw_data:
        model_id = item.get("id", "")
        if not model_id: continue

        if model_id.startswith("google/gemini"):
            did = model_id.split("/", 1)[1].split(":")[0]
            if did not in gemini_c: gemini_c.append(did)
        elif model_id.startswith("openai/"):
            did = model_id.split("/", 1)[1].split(":")[0]
            if did not in openai_c: openai_c.append(did)
        elif model_id.startswith("anthropic/"):
            did = model_id.split("/", 1)[1].split(":")[0]
            if did not in claude_c: claude_c.append(did)
        elif model_id.startswith("x-ai/"):
            did = model_id.split("/", 1)[1].split(":")[0]
            if did not in grok_c: grok_c.append(did)

        if "google/gemini" in model_id.lower() or "google/gemini" in item.get("name", "").lower():
            continue

        is_free = False
        pricing = item.get("pricing", {})
        if "free" in model_id.lower(): is_free = True
        elif pricing and float(pricing.get("prompt", 0)) == 0 and float(pricing.get("completion", 0)) == 0: is_free = True

        if is_free:
            if model_id not in free_c: free_c.append(model_id)
        else:
            if model_id not in paid_c: paid_c.append(model_id)

    free_c = free_c or OR_FREE_DEFAULTS
    paid_c = paid_c or OR_PAID_DEFAULTS
    gemini_c = gemini_c or GEMINI_CURATED
    openai_c = openai_c or OPENAI_CURATED
    claude_c = claude_c or CLAUDE_CURATED
    grok_c = grok_c or GROK_CURATED

    if "openrouter/free" in free_c: free_c.remove("openrouter/free")
    free_c = ["openrouter/free"] + free_c

    return free_c, paid_c, gemini_c, claude_c, openai_c, grok_c

def load_env_vars():
    vars_dict = {
        "GEMINI_API_KEY": "", "OPENROUTER_API_KEY": "", "CLAUDE_API_KEY": "", "OPENAI_API_KEY": "", "XAI_API_KEY": "",
        "GEMINI_MODEL": "gemini-3.5-flash-lite", "OPENROUTER_MODEL": "openrouter/free", "CLAUDE_MODEL": "claude-fable-5",
        "OPENAI_MODEL": "gpt-5.5", "XAI_MODEL": "grok-4.5"
    }
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(r"^#?\s*([A-Z0-9_]+)\s*=\s*\"?([^\"]*)\"?$", line.strip())
                if match:
                    k, v = match.groups()
                    if not line.strip().startswith("#") or not vars_dict.get(k): vars_dict[k] = v
    return vars_dict

def update_env(key, value):
    if not os.path.exists(ENV_PATH): return
    with open(ENV_PATH, "r", encoding="utf-8") as f: lines = f.readlines()
    updated = False
    for i, line in enumerate(lines):
        if re.match(rf"^#?\s*{key}\s*=\s*.*$", line):
            prefix = "#" if line.strip().startswith("#") else ""
            lines[i] = f'{prefix}{key}="{value}"\n'
            updated = True
            break
    if not updated: lines.append(f'{key}="{value}"\n')
    with open(ENV_PATH, "w", encoding="utf-8") as f: f.writelines(lines)

def is_key_active(key):
    if not os.path.exists(ENV_PATH): return False
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                val = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                if val and "your" not in val.lower() and "here" not in val.lower(): return True
    return False

def set_key_commented_state(key, should_comment):
    if not os.path.exists(ENV_PATH): return
    with open(ENV_PATH, "r", encoding="utf-8") as f: lines = f.readlines()
    updated = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if f"{key}=" in stripped or f"{key} =" in stripped:
            assignment = stripped.lstrip("#").strip()
            lines[i] = f"#{assignment}\n" if should_comment else f"{assignment}\n"
            updated = True
            break
    if not updated and not should_comment:
        placeholder_map = {
            "GEMINI_API_KEY": "AIzaSyYourFullGeminiApiKeyHere", "OPENROUTER_API_KEY": "sk-or-v1-YourFullOpenRouterKeyHere",
            "CLAUDE_API_KEY": "your-claude-api-key-here", "OPENAI_API_KEY": "your-openai-api-key-here", "XAI_API_KEY": "xai-your-grok-api-key-here"
        }
        lines.append(f'{key}="{placeholder_map.get(key, "your-key-here")}"\n')
    with open(ENV_PATH, "w", encoding="utf-8") as f: f.writelines(lines)

def toggle_env_api_keys():
    if not os.path.exists(ENV_PATH): return False
    with open(ENV_PATH, "r", encoding="utf-8") as f: lines = f.readlines()
    target_keys = {"GEMINI_API_KEY", "OPENROUTER_API_KEY", "CLAUDE_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY"}
    is_commented = any(line.strip().startswith("#") for line in lines if any(k in line for k in target_keys))
    new_lines = []
    for line in lines:
        matched = next((k for k in target_keys if k in line), None)
        if matched:
            assignment = line.strip().lstrip("#").strip()
            line = f"{assignment}\n" if is_commented else f"#{assignment}\n"
        new_lines.append(line)
    with open(ENV_PATH, "w", encoding="utf-8") as f: f.writelines(new_lines)
    if shutil.which("notify-send"):
        mode = "Cloud Mode (APIs Enabled)" if is_commented else "Local / Offline Mode (APIs Disabled)"
        subprocess.run(["notify-send", "AI Environment Toggle", f"Switched to {mode}", "-t", "2000"])
    return is_commented

def load_cached_lists():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return (data.get("free", OR_FREE_DEFAULTS), data.get("paid", OR_PAID_DEFAULTS),
                        data.get("gemini", GEMINI_CURATED), data.get("claude", CLAUDE_CURATED),
                        data.get("openai", OPENAI_CURATED), data.get("grok", GROK_CURATED))
        except Exception: pass
    return OR_FREE_DEFAULTS, OR_PAID_DEFAULTS, GEMINI_CURATED, CLAUDE_CURATED, OPENAI_CURATED, GROK_CURATED

def save_cached_lists(free_l, paid_l, gemini_l, claude_l, openai_l, grok_l):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"free": free_l, "paid": paid_l, "gemini": gemini_l, "claude": claude_l, "openai": openai_l, "grok": grok_l}, f, indent=2)
    except Exception: pass

async def async_fetch_openrouter_models(api_key):
    def _fetch():
        try:
            url = "https://openrouter.ai/api/v1/models?sort=top-weekly"
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            req = urlreq.Request(url, headers=headers)
            with urlreq.urlopen(req, timeout=8) as res:
                if res.status == 200:
                    return json.loads(res.read().decode("utf-8")).get("data", [])
        except Exception: pass
        return None
    return await asyncio.to_thread(_fetch)

async def async_get_key():
    fd = sys.stdin.fileno()
    def _read():
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch_bytes = os.read(fd, 1)
            if not ch_bytes: return None
            ch = ch_bytes.decode('utf-8', errors='ignore')
            if ch == '\x1b':
                rlist, _, _ = select.select([fd], [], [], 0.05)
                if rlist:
                    seq_bytes = os.read(fd, 2)
                    seq = seq_bytes.decode('utf-8', errors='ignore')
                    if seq in ('[A', 'OA'): return 'up'
                    elif seq in ('[B', 'OB'): return 'down'
                    elif seq in ('[C', 'OC'): return 'right'
                    elif seq in ('[D', 'OD'): return 'left'
                return 'esc'
            elif ch in ('\r', '\n'): return 'enter'
            elif ch in ('\x7f', '\x08'): return 'backspace'
            elif ch.lower() == 'q': return 'q'
            return ch
        finally: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return await asyncio.to_thread(_read)

def draw_main_menu(selected, gemini_curr, claude_curr, openai_curr, grok_curr, or_curr, message=""):
    sys.stdout.write("\x1b[H\x1b[2J")
    amber, green, red, reset, bold, dim = "\033[38;2;230;120;60m", "\033[1;32m", "\033[1;31m", "\033[0m", "\033[1m", "\033[90m"

    gemini_act, or_act, claude_act, openai_act, grok_act = (is_key_active(k) for k in ["GEMINI_API_KEY", "OPENROUTER_API_KEY", "CLAUDE_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY"])
    keys_active = any([gemini_act, or_act, claude_act, openai_act, grok_act])
    status_text = f"{green}[ ENABLED ]{reset}" if keys_active else f"{red}[ DISABLED ]{reset}"

    gemini_disp = f"{green}{gemini_curr}{reset}" if gemini_act else f"{red}DISABLED (grayed out){reset}"
    openai_disp = f"{green}{openai_curr}{reset}" if openai_act else f"{red}DISABLED (grayed out){reset}"
    claude_disp = f"{green}{claude_curr}{reset}" if claude_act else f"{red}DISABLED (grayed out){reset}"
    grok_disp = f"{green}{grok_curr}{reset}" if grok_act else f"{red}DISABLED (grayed out){reset}"

    is_or_free = "free" in or_curr.lower()
    or_free_disp = f"{green}{or_curr}{reset}" if (or_act and is_or_free) else f"{dim}None selected{reset}"
    or_paid_disp = f"{green}{or_curr}{reset}" if (or_act and not is_or_free) else f"{dim}None selected{reset}"

    sys.stdout.write(f"\n   {bold}  LOCAL-AI CONFIGURATION{reset}\n   {dim}────────────────────────────────────────────────────────────{reset}\n\n")

    options = [
        f"🔌  Cloud Connection      {status_text}",
        f"♊  Google Gemini          {gemini_disp}\n       {dim}Select from curated, lightweight Google endpoints{reset}",
        f"🍎  OpenAI Subscription    {openai_disp}\n       {dim}Select from direct, high-performance OpenAI engines{reset}",
        f"☕  Anthropic Claude       {claude_disp}\n       {dim}Select from direct, industry-leading Claude models{reset}",
        f"🚀  x.AI Grok              {grok_disp}\n       {dim}Select from direct, ultra-high-speed Grok engines{reset}",
        f"🌐  OpenRouter Free       {or_free_disp}\n       {dim}Select from the top 20 most popular free models{reset}",
        f"🌐  OpenRouter Paid       {or_paid_disp}\n       {dim}Select from the top 20 industry leading paid engines{reset}",
        f"↺  Refresh API Lists      {dim}Query OpenRouter for current model rankings{reset}",
        f"✕  Save & Close"
    ]

    for i, opt in enumerate(options):
        spacing = "\n" if i in (1, 2, 3, 4, 5, 6) else ""
        prefix = f"   {amber}❯{reset}  {bold}" if i == selected else "      "
        sys.stdout.write(f"{prefix}{opt}{reset}\n{spacing}")

    sys.stdout.write(f"\n   {dim}────────────────────────────────────────────────────────────{reset}\n")
    sys.stdout.write(f"   {message or f'{dim}Use ▲/▼ Arrows to navigate, Enter to choose, Q to exit.{reset}'}\n")
    sys.stdout.flush()

async def run_selector(title, full_models_list, current, key_name):
    state = {"showing_all": False, "search_query": ""}
    def get_menu_options():
        filtered = full_models_list if not state["search_query"] else [m for m in full_models_list if state["search_query"].lower() in m.lower()]
        return [f"🚫 Turn Off {title}"] + (filtered if (state["showing_all"] or state["search_query"]) else filtered[:20])

    menu_options = get_menu_options()
    selected = menu_options.index(current) if (is_key_active(key_name) and current in menu_options) else 0
    amber, green, red, reset, bold, dim, max_v = "\033[38;2;230;120;60m", "\033[1;32m", "\033[1;31m", "\033[0m", "\033[1m", "\033[90m", 14

    while True:
        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.write(f"\n   {bold}  SELECT {title.upper()}:{reset}\n   {dim}────────────────────────────────────────────────────────────{reset}\n\n")
        if state["search_query"]: sys.stdout.write(f"   🔍  Filter: {green}{state['search_query']}{amber}_{reset}\n\n")

        start = max(0, min(selected - max_v // 2, len(menu_options) - max_v))
        end = min(len(menu_options), start + max_v)

        for i in range(start, end):
            opt = menu_options[i]
            bullet = f"{amber}❯{reset} " if i == selected else "  "
            line = f"{bullet}{red}{opt} {dim}(disabled){reset}" if (i == 0 and not is_key_active(key_name)) else f"{bullet}{green}{opt} {dim}(active){reset}" if (opt == current and is_key_active(key_name)) else f"{bullet}{opt}"
            sys.stdout.write(f"     {bold if i == selected else ''}{line}{reset}\n")

        m_above, m_below = start > 0, end < len(menu_options)
        ind = " ▲ ▼ " if (m_above and m_below) else " ▼ more below " if m_below else " ▲ more above " if m_above else ""
        div = f"   {dim}{'─'*25}{amber}{ind}{dim}{'─'*25}{reset}" if ind else f"   {dim}────────────────────────────────────────────────────────────{reset}"
        sys.stdout.write(f"\n{div}\n")

        hint = f"Found {len(menu_options) - 1} matches. Backspace to edit, Esc to clear." if state["search_query"] else f"Showing Top 20. Press ► (Right Arrow) for all {len(full_models_list)} models." if not state["showing_all"] else f"Showing All {len(full_models_list)} models. Press ◄ (Left Arrow) for Top 20."
        sys.stdout.write(f"   {dim}{hint}{reset}\n   {dim}Press Enter to apply, or type characters to filter instantly.{reset}\n")
        sys.stdout.flush()

        key = await async_get_key()
        if key == 'up': selected = (selected - 1) % len(menu_options)
        elif key == 'down': selected = (selected + 1) % len(menu_options)
        elif key == 'backspace':
            if state["search_query"]: state["search_query"] = state["search_query"][:-1]; selected = 0; menu_options = get_menu_options()
        elif key == 'esc':
            if state["search_query"]: state["search_query"] = ""; selected = 0; menu_options = get_menu_options()
            else: return None
        elif key == 'right' and not state["showing_all"]:
            state["showing_all"] = True; selected_m = menu_options[selected]; menu_options = get_menu_options()
            selected = menu_options.index(selected_m) if selected_m in menu_options else 0
        elif key == 'left' and state["showing_all"]:
            state["showing_all"] = False; selected_m = menu_options[selected]; menu_options = get_menu_options()
            selected = menu_options.index(selected_m) if selected_m in menu_options else 0
        elif key == 'enter': return "DISABLE" if selected == 0 else menu_options[selected]
        elif isinstance(key, str) and len(key) == 1 and (key.isalnum() or key in ('-', ':', '/', '.', '_')):
            state["search_query"] += key; selected = 0; menu_options = get_menu_options()

async def async_main():
    sys.stdout.write("\033[?25l"); sys.stdout.flush()
    env = load_env_vars()
    gemini_curr, openai_curr, claude_curr, grok_curr, or_curr = env["GEMINI_MODEL"], env.get("OPENAI_MODEL", "gpt-5.5"), env.get("CLAUDE_MODEL", "claude-fable-5"), env.get("XAI_MODEL", "grok-4.5"), env["OPENROUTER_MODEL"]
    or_free_list, or_paid_list, gemini_list, claude_list, openai_list, grok_list = load_cached_lists()

    if "openrouter/free" in or_free_list: or_free_list.remove("openrouter/free")
    or_free_list = ["openrouter/free"] + or_free_list

    selected_idx, message, total_options = 0, "", 9

    try:
        while True:
            draw_main_menu(selected_idx, gemini_curr, claude_curr, openai_curr, grok_curr, or_curr, message)
            message = ""
            key = await async_get_key()

            if key == 'up': selected_idx = (selected_idx - 1) % total_options
            elif key == 'down': selected_idx = (selected_idx + 1) % total_options
            elif key == 'enter':
                if selected_idx == 0:
                    is_now_enabled = toggle_env_api_keys()
                    env = load_env_vars()
                    status_text = "\033[1;32mENABLED\033[0m" if is_now_enabled else "\033[1;31mDISABLED\033[0m"
                    message = f"✓ Switched Cloud Connection to: {status_text}"
                elif selected_idx in (1, 2, 3, 4, 5, 6):
                    target_map = {
                        1: ("Gemini", gemini_list, gemini_curr, "GEMINI_API_KEY", "GEMINI_MODEL"),
                        2: ("OpenAI", openai_list, openai_curr, "OPENAI_API_KEY", "OPENAI_MODEL"),
                        3: ("Claude", claude_list, claude_curr, "CLAUDE_API_KEY", "CLAUDE_MODEL"),
                        4: ("Grok", grok_list, grok_curr, "XAI_API_KEY", "XAI_MODEL"),
                        5: ("OpenRouter Free", or_free_list, or_curr, "OPENROUTER_API_KEY", "OPENROUTER_MODEL"),
                        6: ("OpenRouter Paid", or_paid_list, or_curr, "OPENROUTER_API_KEY", "OPENROUTER_MODEL"),
                    }
                    title, lst, curr, k_name, m_name = target_map[selected_idx]
                    res = await run_selector(title, lst, curr, k_name)
                    if res == "DISABLE": set_key_commented_state(k_name, True); message = f"✓ {title} disabled."
                    elif res:
                        set_key_commented_state(k_name, False); update_env(m_name, res)
                        if selected_idx == 1: gemini_curr = res
                        elif selected_idx == 2: openai_curr = res
                        elif selected_idx == 3: claude_curr = res
                        elif selected_idx == 4: grok_curr = res
                        else: or_curr = res
                        message = f"✓ Saved {m_name}={res} and re-enabled {title} API Key."
                elif selected_idx == 7:
                    message = "\033[1;33m↺ Checking OpenRouter for current model rankings...\033[0m"
                    draw_main_menu(selected_idx, gemini_curr, claude_curr, openai_curr, grok_curr, or_curr, message)
                    raw_data = await async_fetch_openrouter_models(env["OPENROUTER_API_KEY"])
                    if raw_data:
                        or_free_list, or_paid_list, gemini_list, claude_list, openai_list, grok_list = classify_openrouter_models(raw_data)
                        save_cached_lists(or_free_list, or_paid_list, gemini_list, claude_list, openai_list, grok_list)
                        message = "✓ Dynamic model rankings & provider APIs synchronized."
                    else: message = "\033[1;31m✗ Connection failed. Keeping cached defaults."
                elif selected_idx == 8: break
            elif key == 'q': break
    finally:
        sys.stdout.write("\x1b[H\x1b[2J\033[?25h")
        sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(async_main())
