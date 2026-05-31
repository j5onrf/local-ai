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
    "3": {"name": "Hugging Face: Microsoft", "type": "huggingface_user", "id": "microsoft"},
    
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
    
    # Handles both 'huggingface_user' and 'huggingface_org' using the author query filter
    if target_config["type"] in ("huggingface_user", "huggingface_org"):
        modified_models = fetch_hf_data(username, "lastModified")
        created_models = fetch_hf_data(username, "createdAt")
        
        if modified_models is None or created_models is None:
            print("  \033[1;31m⚠️ Error: Could not connect to Hugging Face API.\033[0m")
            input("\n  Press [Enter] to return to menu...")
            return

        while True:
            print_header(target_config["name"])
            print(f"  Target: huggingface.co/{username} | Snapshots (Max {LIMIT})\n")
            
            # --- SECTION 1: LAST 10 UPDATED ---
            print(" \033[1;34m󰚌  RECENTLY UPDATED / MODIFIED\033[0m")
            print("\033[90m" + "─" * 70 + "\033[0m")
            if not modified_models:
                print("  No public repositories found.")
            else:
                for idx, model in enumerate(modified_models[:LIMIT], 1):
                    model_id = model.get("id", "Unknown")
                    short_name = model_id.split('/')[-1]
                    formatted_time = parse_iso_time(model.get("lastModified", ""))
                    color = "\033[0m" if idx % 2 == 0 else "\033[38;5;246m"
                    print(f"  {idx:2d}. \033[1;32m{short_name:<30}\033[0m {color}Modified: {formatted_time}\033[0m")

            print("\n" + "\033[90m" + "─" * 70 + "\033[0m")
            
            # --- SECTION 2: LAST 10 CREATED ---
            print(" \033[1;33m󰚌  NEWEST REPOSITORIES CREATED\033[0m")
            print("\033[90m" + "─" * 70 + "\033[0m")
            if not created_models:
                print("  No public repositories found.")
            else:
                for idx, model in enumerate(created_models[:LIMIT], 1):
                    model_id = model.get("id", "Unknown")
                    short_name = model_id.split('/')[-1]
                    formatted_time = parse_iso_time(model.get("createdAt", ""))
                    color = "\033[0m" if idx % 2 == 0 else "\033[38;5;246m"
                    print(f"  {idx:2d}. \033[1;36m{short_name:<30}\033[0m {color}Created:  {formatted_time}\033[0m")

            print("\033[90m" + "─" * 70 + "\033[0m")
            print("  [q/Enter] Return to Target Selection")
            sys.stdout.flush()

            key = get_key()
            if key.lower() == 'q' or key == '\r':
                break

# --- Main Runtime Loop ---
def main():
    keys = list(TRACK_TARGETS.keys())
    selected = 0
    
    # Hide cursor
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
            if key == '\033[A':  # Up Arrow
                selected = (selected - 1) % len(options)
            elif key == '\033[B':  # Down Arrow
                selected = (selected + 1) % len(options)
            elif key == '\r':  # Enter
                if selected == len(keys):  # Selected Exit
                    break
                else:
                    render_target_view(TRACK_TARGETS[keys[selected]])
    finally:
        # Restore cursor
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
