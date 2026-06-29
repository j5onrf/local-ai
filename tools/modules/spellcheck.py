#!/usr/bin/env python3 [v0.8.9.8]
# Offline & Online Context-Aware Spellchecker Module for Local-Ai Agent

import os
import re
import sys
import json
import urllib.request as urlreq
import urllib.parse as urlparse

def load_system_dictionary():
    paths = ["/usr/share/dict/words", "/etc/dictionaries-common/words", "/usr/dict/words"]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return {word.strip().lower() for word in f if word.strip().isalpha()}
            except Exception:
                pass
    return None

DICT_WORDS = load_system_dictionary()
DEV_TERMS = {
    "auth", "git", "bash", "zsh", "cli", "tui", "yaml", "json", "ast", "llm", 
    "api", "url", "cmd", "args", "uuid", "md", "txt", "db", "sqlite", "epoxy", "wttr"
}
if DICT_WORDS:
    DICT_WORDS.update(DEV_TERMS)


def edits1(word):
    letters    = 'abcdefghijklmnopqrstuvwxyz'
    splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
    deletes    = [L + R[1:]               for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
    inserts    = [L + c + R               for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)


def correct_word(word):
    """Fallback single-word spelling correction if grammar servers are offline."""
    if not DICT_WORDS or not word.isalpha() or len(word) < 4:
        return word
    w_lower = word.lower()
    if w_lower in DICT_WORDS:
        return word
    candidates = edits1(w_lower) & DICT_WORDS
    if candidates:
        def edit_priority(cand):
            is_trans = (sorted(cand) == sorted(w_lower))
            diff = len(cand) - len(w_lower)
            prio = 1 if is_trans else 2 if diff == 1 else 3 if diff == 0 else 4
            return (prio, cand)
        
        best = min(candidates, key=edit_priority)
        return best.upper() if word.isupper() else best.capitalize() if word[0].isupper() else best
    return word


def check_query_spelling_offline(query: str) -> tuple:
    """Processes classic context-blind fallback dictionary checks."""
    words = re.split(r'(\b[a-zA-Z]+\b)', query)
    corrected_words = []
    changed = False
    for chunk in words:
        if chunk.isalpha():
            corrected = correct_word(chunk)
            if corrected != chunk:
                changed = True
            corrected_words.append(corrected)
        else:
            corrected_words.append(chunk)
    return "".join(corrected_words), changed


def check_query_spelling(query, get_key_fn):
    """Main verification interface. Resolves grammar context and coordinates correction menus."""
    corrected_query = query
    changed = False
    used_grammar_server = False

    # Cascading service list (Local Docker, Local OS package, Public Free Cloud)
    endpoints = [
        "http://localhost:8010/v2/check",
        "http://localhost:8081/v2/check",
        "https://api.languagetool.org/v2/check"
    ]
    
    response_data = None
    for url in endpoints:
        form_data = urlparse.urlencode({'text': query, 'language': 'en-US'}).encode('utf-8')
        req = urlreq.Request(url, data=form_data, method='POST')
        try:
            with urlreq.urlopen(req, timeout=1.2) as r:
                response_data = json.loads(r.read().decode('utf-8'))
                used_grammar_server = True
                break
        except Exception:
            continue

    # Apply grammar server suggestions if retrieved
    if response_data and "matches" in response_data:
        matches = response_data["matches"]
        if matches:
            # Sort replacements in reverse offset order to prevent indexing shift errors
            matches.sort(key=lambda m: m.get("offset", 0), reverse=True)
            chars = list(query)
            for match in matches:
                offset = match.get("offset")
                length = match.get("length")
                replacements = match.get("replacements", [])
                
                if replacements and offset is not None and length is not None:
                    best_correction = replacements[0].get("value")
                    if best_correction is not None:
                        # Splice corrected words/phrases contextually
                        chars[offset : offset + length] = list(best_correction)
                        changed = True
            corrected_query = "".join(chars)

    # Air-gapped fallback to classic edit-distance check
    if not used_grammar_server:
        corrected_query, changed = check_query_spelling_offline(query)

    # Prompt user on change detection
    if changed and corrected_query.strip() != query.strip():
        sys.stderr.write(
            f"\n\033[2m[sys] Typos detected. Correct query to:\033[0m\n"
            f"\033[3m   \"{corrected_query}\"\033[0m\n"
            f"\033[2m   [↵ accept  Tab: edit  d: disable  Esc: skip]: \033[0m"
        )
        sys.stderr.flush()
        
        key = get_key_fn()
        if key in ('\r', '\n', ''):
            sys.stderr.write("\r\x1b[K\033[2;32m[sys] Corrected.\033[0m\n")
            sys.stderr.flush()
            return "RUN", corrected_query
        elif key in ('\t', 'e', 'E'):
            sys.stderr.write("\r\x1b[K\033[2;33m[sys] Returning to editor...\033[0m\n")
            sys.stderr.flush()
            return "EDIT", query
        elif key in ('d', 'D'):
            sys.stderr.write("\r\x1b[K\033[2;31m[sys] Spellchecker disabled. (Type /e to re-enable)\033[0m\n")
            sys.stderr.flush()
            return "DISABLE", query
        else:
            sys.stderr.write("\r\x1b[K\033[2;31m[sys] Kept original.\033[0m\n")
            sys.stderr.flush()
            
    return "RUN", query
