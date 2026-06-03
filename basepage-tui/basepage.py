#!/usr/bin/env python3
# Basepage TUI v0.7.5 [j5onrf] [06-01-26]

import sys
import os
import tty
import termios
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import subprocess
import shutil
import webbrowser
import html
import time
import random

CACHE_DIR = os.path.expanduser("~/.cache/ai_basepage")
os.makedirs(CACHE_DIR, exist_ok=True)

REDLIB_INSTANCE = "auto"

FEEDS = {
    "r/hyprland": {"type": "reddit", "subreddit": "hyprland"},
    "r/unixporn": {"type": "reddit", "subreddit": "unixporn"},
    "Hacker News": {"type": "custom", "url": "https://news.ycombinator.com/rss"},
    "llama.cpp Releases": {"type": "github", "owner": "ggml-org", "repo": "llama.cpp"}
}

SORTS = ["hot", "top_day", "top_week"]

ACTIVE_REDLIB_INSTANCE = None
current_sort_idx = 0

def get_working_redlib_instance():
    instance_cache = os.path.join(CACHE_DIR, "redlib_instances.json")
    instances = []
    
    try:
        if not os.path.exists(instance_cache) or (time.time() - os.path.getmtime(instance_cache)) > 86400:
            url = "https://raw.githubusercontent.com/redlib-org/redlib-instances/main/instances.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Basepage TUI Redirector)'})
            with urllib.request.urlopen(req, timeout=4.0) as res:
                data = json.loads(res.read().decode('utf-8'))
                with open(instance_cache, "w") as f:
                    json.dump(data, f)
    except Exception:
        pass

    try:
        with open(instance_cache, "r") as f:
            data = json.load(f)
            instances = [
                inst["url"] for inst in data.get("instances", []) 
                if "onion" not in inst.get("url", "") and "url" in inst
            ]
    except Exception:
        pass

    if not instances:
        instances = [
            "https://redlib.catsarch.com",
            "https://redlib.privacyredirect.com",
            "https://redlib.perennialte.ch"
        ]

    priority_instances = [
        "https://redlib.catsarch.com",
        "https://redlib.privacyredirect.com",
        "https://reddit.adminforge.de"
    ]

    shuffled_instances = [i for i in instances if i not in priority_instances]
    random.shuffle(shuffled_instances)
    test_pool = priority_instances + shuffled_instances
    
    for inst in test_pool[:10]:
        inst_clean = inst.rstrip('/')
        try:
            req = urllib.request.Request(f"{inst_clean}/settings", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=2.0) as res:
                html_snippet = res.read(1000).decode('utf-8', errors='ignore')
                if "redlib" in html_snippet.lower() or "theme" in html_snippet.lower() or "<form" in html_snippet.lower():
                    return inst_clean
        except Exception:
            continue
            
    return priority_instances[0].rstrip('/')

def map_to_redlib(url):
    global ACTIVE_REDLIB_INSTANCE
    if not url:
        return ""
    if REDLIB_INSTANCE and REDLIB_INSTANCE != "auto":
        base_instance = REDLIB_INSTANCE.rstrip('/')
    else:
        if not ACTIVE_REDLIB_INSTANCE:
            ACTIVE_REDLIB_INSTANCE = get_working_redlib_instance()
        base_instance = ACTIVE_REDLIB_INSTANCE
    return re.sub(r'https?://(?:[a-z0-9]+\.)?reddit\.com', base_instance, url, flags=re.IGNORECASE)

def open_in_browser(url):
    if not url:
        return
    try:
        if sys.platform.startswith('linux'):
            subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == 'win32':
            os.startfile(url)
        else:
            webbrowser.open(url)
    except Exception:
        try:
            webbrowser.open(url)
        except Exception:
            pass

def fully_unescape(text):
    if not text:
        return ""
    for _ in range(5):
        next_text = html.unescape(text)
        if next_text == text:
            break
        text = next_text
    return text

def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
        ch = sys.stdin.read(1)
        if ch == '\033':
            ch += sys.stdin.read(2)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def get_text_input(prompt_text):
    sys.stdout.write(f"\033[?25h\n {prompt_text}")
    sys.stdout.flush()
    
    user_input = []
    
    while True:
        ch = get_key()
        if ch in ('\r', '\n'):
            break
        elif ch in ('\x7f', '\x08'):
            if user_input:
                user_input.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
        elif ch == '\033':
            user_input = []
            break
        elif len(ch) == 1 and ch.isprintable():
            user_input.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
            
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    return "".join(user_input).strip()

def highlight_matches(text, keyword, reset_code="\033[0m\033[1m"):
    if not keyword:
        return text
    highlight_code = "\033[30;43m"
    pattern = re.compile(f"({re.escape(keyword)})", re.IGNORECASE)
    return pattern.sub(f"{highlight_code}\\1{reset_code}", text)

def count_keyword_matches(items, keyword):
    if not keyword:
        return 0
    count = 0
    lowered_kw = keyword.lower()
    for item in items:
        count += item.get('title', '').lower().count(lowered_kw)
        count += item.get('body', '').lower().count(lowered_kw)
    return count

def print_header(subtitle=""):
    sys.stdout.write("\033[2J\033[H")
    c = [f"\033[3{i}m" for i in range(1, 6)]
    reset = "\033[0m"
    print(f"         {c[0]}╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮{reset}")
    print(f"         {c[1]}│    󰚌  BASEPAGE DASHBOARD    │{reset}")
    print(f"         {c[2]}╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯{reset}")
    if subtitle:
        print(f"               \033[1;35m// {subtitle}\033[0m\n")

def fetch_feed_instant(target_key):
    if target_key not in FEEDS:
        return False
        
    feed_config = FEEDS[target_key]
    sort_mode = SORTS[current_sort_idx]
    
    if feed_config["type"] == "github":
        owner = feed_config["owner"]
        repo = feed_config["repo"]
        url = f"https://github.com/{owner}/{repo}/releases.atom"
    elif feed_config["type"] == "reddit":
        subreddit = feed_config["subreddit"]
        if sort_mode == "hot":
            url = f"https://www.reddit.com/r/{subreddit}/hot/.rss?limit=30"
        elif sort_mode == "top_day":
            url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day&limit=30"
        elif sort_mode == "top_week":
            url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=week&limit=30"
        else:
            url = f"https://www.reddit.com/r/{subreddit}/hot/.rss?limit=30"
    else:
        url = feed_config["url"]

    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0'}
    )
    try:
        with urllib.request.urlopen(req, timeout=6.0) as response:
            content = response.read().decode('utf-8', errors='ignore')
            entries = re.findall(r'<(entry|item)>(.*?)</\1>', content, re.DOTALL)
            items = []
            
            for _, entry_content in entries:
                title_match = re.search(r'<title[^>]*>(.*?)</title>', entry_content, re.DOTALL)
                
                link_match = re.search(r'<link\s+[^>]*rel=["\']alternate["\']\s+[^>]*href=["\']([^"\'\s]+)["\']', entry_content)
                if not link_match:
                    link_match = re.search(r'<link\s+[^>]*href=["\']([^"\'\s]+)["\']\s+[^>]*rel=["\']alternate["\']', entry_content)
                if not link_match:
                    link_match = re.search(r'<link\s+[^>]*type=["\']text/html["\']\s+[^>]*href=["\']([^"\'\s]+)["\']', entry_content)
                if not link_match:
                    link_match = re.search(r'<link\s+[^>]*href=["\']([^"\'\s]+)["\']', entry_content)
                if not link_match:
                    link_match = re.search(r'<link[^>]*>(.*?)</link>', entry_content, re.DOTALL)
                    
                content_match = re.search(r'<content[^>]*>(.*?)</content>', entry_content, re.DOTALL)
                if not content_match:
                    content_match = re.search(r'<description[^>]*>(.*?)</description>', entry_content, re.DOTALL)
                
                comments_match = re.search(r'<comments[^>]*>(.*?)</comments>', entry_content, re.DOTALL)
                
                if title_match and (link_match or content_match):
                    title_raw = title_match.group(1)
                    title_raw = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_raw, flags=re.DOTALL)
                    title_text = fully_unescape(title_raw).strip()
                    
                    if link_match:
                        link_raw = link_match.group(1) if len(link_match.groups()) >= 1 else link_match.group(0)
                        if '>' in link_raw:
                            link_raw = re.sub(r'<[^>]+>', '', link_raw)
                        post_url = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', link_raw, flags=re.DOTALL).strip()
                    else:
                        post_url = ""
                        
                    if content_match:
                        body_raw = content_match.group(1)
                        body_raw = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', body_raw, flags=re.DOTALL)
                        html_body = fully_unescape(body_raw)
                    else:
                        html_body = ""
                        
                    comments_url = ""
                    if comments_match:
                        comments_raw = comments_match.group(1).strip()
                        comments_url = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', comments_raw, flags=re.DOTALL).strip()
                    
                    img_url = ""
                    href_imgs = re.findall(r'href=["\'](https://i\.redd\.it/[^"\']+\.(?:jpg|jpeg|png|gif))["\']', html_body, re.IGNORECASE)
                    if href_imgs: img_url = href_imgs[0]
                        
                    clean_text = re.sub(r'<[^>]+>', '', html_body)
                    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
                    clean_text = re.sub(r'submitted by.*$', '', clean_text, flags=re.IGNORECASE | re.DOTALL).strip()
                    
                    if not clean_text:
                        clean_text = "[No entry text parsed.]"

                    items.append({
                        "title": title_text,
                        "img": img_url,
                        "link": post_url,
                        "comments": comments_url,
                        "body": clean_text
                    })

            if not items:
                return False

            safe_key = re.sub(r'[^a-zA-Z0-9_-]', '_', target_key).strip('_')
            if feed_config["type"] == "reddit":
                cache_path = os.path.join(CACHE_DIR, f"{safe_key}_{sort_mode}_raw.json")
            else:
                cache_path = os.path.join(CACHE_DIR, f"{safe_key}_raw.json")
                
            with open(cache_path, "w") as f:
                json.dump(items, f)
            return True
                
    except Exception:
        return False

def render_page(target_key):
    if target_key not in FEEDS:
        return
        
    feed_config = FEEDS[target_key]
    sort_mode = SORTS[current_sort_idx]
    
    sort_labels = {"hot": "HOT", "top_day": "TOP (Day)", "top_week": "TOP (Week)"}
    safe_key = re.sub(r'[^a-zA-Z0-9_-]', '_', target_key).strip('_')
    
    if feed_config["type"] == "reddit":
        cache_path = os.path.join(CACHE_DIR, f"{safe_key}_{sort_mode}_raw.json")
        sort_suffix = f" {sort_labels[sort_mode]}"
    else:
        cache_path = os.path.join(CACHE_DIR, f"{safe_key}_raw.json")
        sort_suffix = ""
        
    if not os.path.exists(cache_path):
        fetch_feed_instant(target_key)
            
    try:
        with open(cache_path, "r") as f:
            items = json.load(f)
    except Exception:
        print("\033[1;31m⚠️ Local cache empty. Trigger manual refetch.\033[0m")
        subprocess.run(["sleep", "1.2"])
        return
        
    if not items:
        print_header(f"{target_key} Index")
        print("No items available in cache.")
        input("\n[Enter] Return")
        return
        
    PAGE_SIZE = 15
    current_page = 0
    selected_global = 0
    search_query = ""
    
    while True:
        total_items = len(items)
        max_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE
        
        start_idx = current_page * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, total_items)
        page_items = items[start_idx:end_idx]
        
        local_select = selected_global - start_idx
        if local_select < 0:
            selected_global = start_idx
        elif local_select >= len(page_items) and page_items:
            selected_global = end_idx - 1
            
        match_count = count_keyword_matches(items, search_query)
        search_status = f" | \033[1;33m🔍 Scanner: '{search_query}' ({match_count} found)\033[0m" if search_query else ""
        
        print_header(f"{target_key}{sort_suffix} Feed (Page {current_page + 1}/{max_pages}){search_status}")
        print("\033[34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n")
        
        for local_idx, item in enumerate(page_items):
            global_idx = start_idx + local_idx
            body_snippet = item.get('body', '').replace('\n', ' ').strip()
            short_snippet = (body_snippet[:65] + '...') if len(body_snippet) > 65 else body_snippet
            
            disp_title = highlight_matches(item['title'], search_query, reset_code="\033[0m\033[1;36m" if global_idx == selected_global else "\033[0m\033[1m")
            disp_snippet = highlight_matches(short_snippet, search_query, reset_code="\033[0m\033[1;36m" if global_idx == selected_global else "\033[0m\033[3;90m")
            
            if global_idx == selected_global:
                print(f" \033[1;36m❯ {global_idx+1:02d}. {disp_title}\033[0m")
                print(f"       \033[1;36m↳ {disp_snippet}\033[0m")
            else:
                print(f"   \033[90m{global_idx+1:02d}.\033[0m \033[1m{disp_title}\033[0m")
                print(f"       \033[3;90m↳ {disp_snippet}\033[0m")
                
        print("\n\033[34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
        print(" [↑/↓] Navigate | [←/→] Page | [/] Scan Filter | [c] Clear Scan | [Enter] Read | [q] Back")
        
        sys.stdout.flush()
        
        key = get_key()
        if key == '\033[A': 
            selected_global = (selected_global - 1) % total_items
            current_page = selected_global // PAGE_SIZE
        elif key == '\033[B': 
            selected_global = (selected_global + 1) % total_items
            current_page = selected_global // PAGE_SIZE
        elif key == '\033[C': 
            if (current_page + 1) < max_pages:
                current_page += 1
                selected_global = current_page * PAGE_SIZE
        elif key == '\033[D': 
            if current_page > 0:
                current_page -= 1
                selected_global = current_page * PAGE_SIZE
        elif key == '/':
            search_query = get_text_input("Enter scanner keyword to highlight: ")
        elif key.lower() == 'c':
            search_query = ""
        elif key.lower() == 'o' and page_items:
            active_item = items[selected_global]
            if target_key == "Hacker News" and active_item.get("comments"):
                open_in_browser(active_item["comments"])
            else:
                open_in_browser(map_to_redlib(active_item['link']))
        elif key.lower() == 'q':
            break
        elif key == '\r' and page_items: 
            active_item = items[selected_global]
            
            if target_key == "Hacker News" and active_item.get("comments"):
                open_in_browser(active_item["comments"])
                continue
                
            term_cols = shutil.get_terminal_size().columns
            term_width = max(term_cols - 8, 40)
            raw_body_text = active_item.get('body', '[No text body parsed.]')
            
            body_lines = []
            for paragraph in raw_body_text.split('\n\n'):
                words = paragraph.split(' ')
                current_line = []
                for word in words:
                    if '\n' in word:
                        parts = word.split('\n')
                        for p_idx, part in enumerate(parts):
                            current_line.append(part)
                            if p_idx < len(parts) - 1:
                                body_lines.append(" " + " ".join(current_line))
                                current_line = []
                        continue
                    if sum(len(w) for w in current_line) + len(current_line) + len(word) > term_width:
                        body_lines.append(" " + " ".join(current_line))
                        current_line = [word]
                    else:
                        current_line.append(word)
                if current_line:
                    body_lines.append(" " + " ".join(current_line))
                body_lines.append("")
            
            scroll_offset = 0
            
            while True:
                sys.stdout.write("\033[2J\033[H")
                term_lines = shutil.get_terminal_size().lines
                term_cols = shutil.get_terminal_size().columns
                
                local_body_matches = raw_body_text.lower().count(search_query.lower()) if search_query else 0
                item_scan_status = f" | \033[1;33m🔍 Found here: {local_body_matches} times\033[0m" if search_query else ""
                
                print_header(f"Reading: {target_key}{item_scan_status}")
                
                disp_reader_title = highlight_matches(active_item['title'], search_query, reset_code="\033[0m\033[1;32m")
                print(f" \033[1;32m❯ {disp_reader_title}\033[0m")
                print("\033[90m─" * term_cols + "\033[0m")
                
                TEXT_START_ROW = 8
                FOOTER_RESERVE = 3
                VISIBLE_ROWS = max(term_lines - TEXT_START_ROW - FOOTER_RESERVE, 3)
                
                visible_slice = body_lines[scroll_offset:scroll_offset + VISIBLE_ROWS]
                for idx, text_line in enumerate(visible_slice):
                    disp_line = highlight_matches(text_line, search_query)
                    sys.stdout.write(f"\033[{TEXT_START_ROW + idx};1H{disp_line}")
                
                DIVIDER_ROW = term_lines - 2
                MENU_ROW = term_lines - 1
                
                sys.stdout.write(f"\033[{DIVIDER_ROW};1H\033[90m─" * term_cols + "\033[0m")
                sys.stdout.write(f"\033[{MENU_ROW};1H \033[1;36m[↑/↓]\033[0m Scroll  |  \033[1;36m[/]\033[0m Change Scan Word  |  \033[1;33m[q/Enter]\033[0m Close")
                
                sys.stdout.flush()
                
                sub_key = get_key()
                if sub_key == '\033[A': 
                    if scroll_offset > 0: scroll_offset -= 1
                elif sub_key == '\033[B': 
                    if scroll_offset + VISIBLE_ROWS < len(body_lines): scroll_offset += 1
                elif sub_key == '/':
                    search_query = get_text_input("Change scanner keyword: ")
                elif sub_key.lower() == 'o':
                    open_in_browser(map_to_redlib(active_item['link']))
                elif sub_key == '\r' or sub_key.lower() == 'q':
                    sys.stdout.write("\033[2J\033[H")
                    break

def main():
    global current_sort_idx
    selected = 0
    
    sys.stdout.write("\033[?1049h\033[?1007l\033[H\033[?25l")
    sys.stdout.flush()
    
    try:
        subprocess.Popen(
            [sys.executable, __file__, "--bg-sync"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass
    
    try:
        while True:
            print_header("Main Controller Grid")
            
            options = []
            feed_keys = list(FEEDS.keys())
            
            for fk in feed_keys:
                options.append(f"❯ Read {fk}")
                
            sort_labels = {"hot": "[HOT]", "top_day": "[TOP (Day)]", "top_week": "[TOP (Week)]"}
            options.append(f"❯ Toggle Feed Sorting: {sort_labels[SORTS[current_sort_idx]]}")
            options.append("❯ Force Background Refetch")
            options.append("❯ Exit Dashboard Utility")
            
            for i, opt in enumerate(options):
                if i == selected:
                    sys.stdout.write(f"  \033[1;36m{opt}\033[0m\n")
                else:
                    sys.stdout.write(f"    {opt}\n")
            sys.stdout.flush()
            
            key = get_key()
            if key == '\033[A': 
                selected = (selected - 1) % len(options)
            elif key == '\033[B': 
                selected = (selected + 1) % len(options)
            elif key == '\r': 
                num_feeds = len(feed_keys)
                
                if selected < num_feeds:
                    render_page(feed_keys[selected])
                elif selected == num_feeds:
                    current_sort_idx = (current_sort_idx + 1) % len(SORTS)
                elif selected == num_feeds + 1:
                    print_header("Manual Ecosystem Sync")
                    print(" Siphoning data streams completely...")
                    global ACTIVE_REDLIB_INSTANCE
                    ACTIVE_REDLIB_INSTANCE = None
                    
                    for fk in feed_keys:
                        fetch_feed_instant(fk)
                        
                    print("\n \033[1;32m✓ Local feeds and redirects updated successfully.\033[0m")
                    subprocess.run(["sleep", "0.8"])
                elif selected == num_feeds + 2:
                    break
    finally:
        sys.stdout.write("\033[?1049l\033[?1007h\033[?25h")
        sys.stdout.flush()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--bg-sync":
        for mode_idx in range(len(SORTS)):
            current_sort_idx = mode_idx
            for fk in FEEDS.keys():
                fetch_feed_instant(fk)
        sys.exit(0)
        
    main()
