#!/usr/bin/env python3
# Base Tracker TUI v0.7.3 [j5onrf] [05-30-26]

import sys
import os
import tty
import termios
import urllib.request
import json
from datetime import datetime

# --- Configuration ---
TRACK_TARGETS = {
    "1": {"name": "Hugging Face: HauhauCS", "type": "huggingface_user", "id": "HauhauCS"},
    "2": {"name": "Hugging Face: Unsloth", "type": "huggingface_org", "id": "unsloth"},
    "3": {"name": "Hugging Face: mradermacher", "type": "huggingface_user", "id": "mradermacher"},
    "4": {"name": "Hugging Face: Bartowski", "type": "huggingface_user", "id": "bartowski"},
    "5": {"name": "Hugging Face: MaziyarPanahi", "type": "huggingface_user", "id": "MaziyarPanahi"},
    "6": {"name": "Hugging Face: Arcee AI", "type": "huggingface_org", "id": "arcee-ai"},
}

LIMIT = 10  # Number of items to show per category

# --- UI Controls ---
def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\033':
            ch += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def print_header(subtitle=""):
    sys.stdout.write("\033[2J\033[H")  # Clear screen and home cursor
    c = [f"\033[3{i}m" for i in range(1, 6)]
    reset = "\033[0m"
    print(f"         {c[0]}╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮{reset}")
    print(f"         {c[1]}│     󰚌  BASETRACK ENGINE    │{reset}")
    print(f"         {c[2]}╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯{reset}")
    if subtitle:
        print(f"               \033[1;35m// {subtitle}\033[0m\n")

def parse_iso_time(iso_str):
    if not iso_str:
        return "Unknown date"
    clean_stamp = iso_str.split('.')[0].replace('Z', '')
    try:
        dt = datetime.fromisoformat(clean_stamp)
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return iso_str

# --- Data Fetcher ---
def fetch_hf_data(username, sort_by):
    """Fetches data from HF API sorted by lastModified or createdAt."""
    url = f"https://huggingface.co/api/models?author={username}&sort={sort_by}&direction=-1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6.0) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return None

# --- View Renderer ---
def render_target_view(target_config):
    print_header(f"Fetching Live Streams: {target_config['name']}")
    sys.stdout.flush()

    username = target_config["id"]
    now = datetime.now()
    
    if target_config["type"] in ("huggingface_user", "huggingface_org"):
        modified_models = fetch_hf_data(username, "lastModified")
        created_models = fetch_hf_data(username, "createdAt")
        
        if modified_models is None or created_models is None:
            print("  \033[1;31m⚠️ Error: Could not connect to Hugging Face API.\033[0m")
            input("\n  Press [Enter] to return to menu...")
            return

        # DYNAMIC ALIGNMENT ENGINE
        # Find the longest model name across both lists to set the perfect column width
        all_models = (modified_models[:LIMIT] if modified_models else []) + (created_models[:LIMIT] if created_models else [])
        max_name_len = 30  # Default minimum floor width
        for m in all_models:
            name_len = len(m.get("id", "").split('/')[-1])
            if name_len > max_name_len:
                max_name_len = name_len
                
        # The badge column itself needs a fixed display block width (e.g., 12 chars wide)
        # Printable badge text lengths: " [ UPDATED ]" = 12 chars, " [  NEW  ]" = 10 chars
        # Since ANSI escapes break normal format padding, we construct it raw.
        badge_col_width = 14

        while True:
            print_header(target_config["name"])
            print(f"  Target: huggingface.co/{username} | Snapshots (Max {LIMIT})\n")
            
            # --- SECTION 1: LAST 10 UPDATED ---
            print(" \033[1;34m󰚌  RECENTLY UPDATED / MODIFIED\033[0m")
            divider_len = max_name_len + badge_col_width + 25
            print("\033[90m" + "─" * divider_len + "\033[0m")
            
            if not modified_models:
                print("  No public repositories found.")
            else:
                for idx, model in enumerate(modified_models[:LIMIT], 1):
                    short_name = model.get("id", "Unknown").split('/')[-1]
                    raw_mod_time = model.get("lastModified", "")
                    formatted_time = parse_iso_time(raw_mod_time)
                    
                    # Compute badge state
                    badge_str = ""
                    is_new_update = False
                    if raw_mod_time:
                        try:
                            clean_stamp = raw_mod_time.split('.')[0].replace('Z', '')
                            days_old = (now - datetime.fromisoformat(clean_stamp)).days
                            if days_old <= 7:
                                is_new_update = True
                        except Exception:
                            pass

                    # Build text segment lengths with manual spacing matrix
                    name_padding = " " * (max_name_len - len(short_name))
                    if is_new_update:
                        badge_str = " \033[1;42;30m UPDATED \033[0m"
                        badge_padding = " " * (badge_col_width - 12)
                    else:
                        badge_padding = " " * badge_col_width

                    color = "\033[0m" if idx % 2 == 0 else "\033[38;5;246m"
                    print(f"  {idx:2d}. \033[1;32m{short_name}\033[0m{name_padding}{badge_str}{badge_padding}{color}Modified: {formatted_time}\033[0m")

            print("\n" + "\033[90m" + "─" * divider_len + "\033[0m")
            
            # --- SECTION 2: LAST 10 CREATED ---
            print(" \033[1;33m󰚌  NEWEST REPOSITORIES CREATED\033[0m")
            print("\033[90m" + "─" * divider_len + "\033[0m")
            
            if not created_models:
                print("  No public repositories found.")
            else:
                for idx, model in enumerate(created_models[:LIMIT], 1):
                    short_name = model.get("id", "Unknown").split('/')[-1]
                    raw_create_time = model.get("createdAt", "")
                    formatted_time = parse_iso_time(raw_create_time)
                    
                    badge_str = ""
                    is_brand_new = False
                    if raw_create_time:
                        try:
                            clean_stamp = raw_create_time.split('.')[0].replace('Z', '')
                            days_old = (now - datetime.fromisoformat(clean_stamp)).days
                            if days_old <= 7:
                                is_brand_new = True
                        except Exception:
                            pass

                    name_padding = " " * (max_name_len - len(short_name))
                    if is_brand_new:
                        badge_str = " \033[1;46;30m  NEW  \033[0m"
                        badge_padding = " " * (badge_col_width - 10)
                    else:
                        badge_padding = " " * badge_col_width

                    color = "\033[0m" if idx % 2 == 0 else "\033[38;5;246m"
                    print(f"  {idx:2d}. \033[1;36m{short_name}\033[0m{name_padding}{badge_str}{badge_padding}{color}Created:  {formatted_time}\033[0m")

            print("\033[90m" + "─" * divider_len + "\033[0m")
            print("  [q/Enter] Return to Target Selection")
            sys.stdout.flush()

            key = get_key()
            if key.lower() == 'q' or key == '\r':
                break

# --- Main Runtime Loop ---
def main():
    keys = list(TRACK_TARGETS.keys())
    selected = 0
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while True:
            print_header("Active Platform Tracklist")
            print("  Select an item to run an on-demand update stream verification:\n")
            
            options = [TRACK_TARGETS[k]["name"] for k in keys] + ["Exit Tracking Utility"]
            
            for i, opt in enumerate(options):
                if i == selected:
                    sys.stdout.write(f"  \033[1;36m❯ {opt}\033[0m\n")
                else:
                    sys.stdout.write(f"    {opt}\n")
            sys.stdout.flush()
            
            key = get_key()
            if key == '\033[A':
                selected = (selected - 1) % len(options)
            elif key == '\033[B':
                selected = (selected + 1) % len(options)
            elif key == '\r':
                if selected == len(keys):
                    break
                else:
                    render_target_view(TRACK_TARGETS[keys[selected]])
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
