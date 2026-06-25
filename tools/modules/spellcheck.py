#!/usr/bin/env python3
# Offline Spellchecker Module for Local-Ai Agent

import os, re, sys

def load_system_dictionary():
    paths = ["/usr/share/dict/words", "/etc/dictionaries-common/words", "/usr/dict/words"]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return {word.strip().lower() for word in f if word.strip().isalpha()}
            except Exception: pass
    return None

DICT_WORDS = load_system_dictionary()
DEV_TERMS = {"auth", "git", "bash", "zsh", "cli", "tui", "yaml", "json", "ast", "llm", "api", "url", "cmd", "args", "uuid", "md", "txt", "db", "sqlite", "epoxy", "wttr"}
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
    if not DICT_WORDS or not word.isalpha() or len(word) < 4:
        return word
    w_lower = word.lower()
    if w_lower in DICT_WORDS:
        return word
    candidates = edits1(w_lower) & DICT_WORDS
    if candidates:
        # High-performance keyboard-typo heuristic:
        # Priority 1: Transpositions/Anagrams (e.g., 'heor' -> 'hero')
        # Priority 2: Insertions (e.g., 'chek' -> 'check')
        # Priority 3: Replacements (e.g., 'chek' -> 'chef')
        # Priority 4: Deletions (e.g., 'chek' -> 'che')
        def edit_priority(cand):
            is_trans = (sorted(cand) == sorted(w_lower))
            diff = len(cand) - len(w_lower)
            if is_trans:
                prio = 1
            elif diff == 1:
                prio = 2
            elif diff == 0:
                prio = 3
            else:
                prio = 4
            # Returns a tuple: (Priority, Alphabetical)
            return (prio, cand)
        
        # min() selects the lowest priority number (1 is best, 4 is worst)
        # Ties are broken alphabetically by the second tuple element
        best = min(candidates, key=edit_priority)
        return best.upper() if word.isupper() else best.capitalize() if word[0].isupper() else best
    return word

def check_query_spelling(query, get_key_fn):
    if not DICT_WORDS:
        return "RUN", query
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
    if changed:
        corrected_query = "".join(corrected_words)
        # Clean, discoverable menu prompt
        sys.stderr.write(f"\n\033[1;30m[sys] Typos detected. Correct query to:\033[0m\n\033[3m   \"{corrected_query}\"\033[0m\n\033[1;30m   [↵ accept  Tab: edit  d: disable  Esc: skip]: \033[0m")
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
            # Clear line and print the explicit re-enable command helper
            sys.stderr.write("\r\x1b[K\033[2;31m[sys] Spellchecker disabled. (Type /e to re-enable)\033[0m\n")
            sys.stderr.flush()
            return "DISABLE", query
        else:
            sys.stderr.write("\r\x1b[K\033[2;31m[sys] Kept original.\033[0m\n")
            sys.stderr.flush()
    return "RUN", query
