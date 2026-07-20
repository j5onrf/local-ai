# File: ~/.config/local-ai/modules/agent_spell.py
import os
import sys
import re
import json
import shutil
import urllib.parse as urlparse
import urllib.request as urlreq
import difflib
from typing import Set, Dict, Tuple, List, Callable, Any

TYPO_OVERRIDES: Dict[str, str] = {
    "hellow": "hello", "helow": "hello", "helo": "hello",
    "howre": "how are", "wru": "where are you", "hru": "how are you",
    "youa": "you", "trainted": "trained"
}
PROTECTED_WORDS: Set[str] = {"hello", "hi", "hey", "how", "here", "you", "who", "there"}


def load_system_dictionary() -> Set[str]:
    """Loads system word dictionary with development and TUI command word exceptions."""
    embedded: Set[str] = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with", "he", "as", "you", 
        "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", 
        "all", "would", "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", "when", 
        "make", "can", "like", "time", "no", "just", "him", "know", "take", "people", "into", "year", "your", "good", "some", 
        "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", 
        "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these", 
        "give", "day", "most", "us", "lazy", "quick", "brown", "fox", "jumps", "dog", "cat", "mat", "sit", "sits", "book", 
        "read", "reads", "spelling", "grammar", "here", "there", "where", "why", "when", "how", "who", "what", "which", "whose",
        "am", "is", "are", "was", "were", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing",
        "write", "writes", "written", "writing", "code", "coder", "coding", "program", "programming", "python", "script",
        "sentence", "errors", "error", "correct", "correction", "spelled", "spelling", "hello", "hi", "hey"
    }
    paths: List[str] = ["/usr/share/dict/words", "/etc/dictionaries-common/words", "/usr/dict/words"]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    words = {word.strip().lower() for word in f if word.strip().isalpha()}
                    words.update(embedded)
                    return words
            except Exception:
                pass
    return embedded


DICT_WORDS: Set[str] = load_system_dictionary()
DEV_TERMS: Set[str] = {
    "auth", "git", "bash", "zsh", "cli", "tui", "yaml", "json", "ast", "llm", 
    "api", "url", "cmd", "args", "uuid", "md", "txt", "db", "sqlite", "epoxy", "wttr"
}
if DICT_WORDS:
    DICT_WORDS.update(DEV_TERMS)


def edits1(word: str) -> Set[str]:
    """Generates all edit-distance-1 permutations for a given word."""
    letters: str = 'abcdefghijklmnopqrstuvwxyz'
    splits: List[Tuple[str, str]] = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes: List[str] = [L + R[1:] for L, R in splits if R]
    transposes: List[str] = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces: List[str] = [L + c + R[1:] for L, R in splits if R for c in letters]
    inserts: List[str] = [L + c + R for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)


def correct_word(word: str) -> str:
    """Phonetically verifies and corrects individual word selections."""
    if not DICT_WORDS or not word.isalpha() or len(word) < 3:
        return word
    w_lower: str = word.lower()
    if w_lower in DICT_WORDS:
        return word
    candidates: Set[str] = edits1(w_lower) & DICT_WORDS
    if candidates:
        def edit_priority(cand: str) -> Tuple[int, str]:
            is_trans: bool = (sorted(cand) == sorted(w_lower))
            diff: int = len(cand) - len(w_lower)
            prio: int = 1 if is_trans else 2 if diff == 1 else 3 if diff == 0 else 4
            return (prio, cand)
        
        best: str = min(candidates, key=edit_priority)
        return best.upper() if word.isupper() else best.capitalize() if word[0].isupper() else best
    return word


def apply_static_overrides(query: str) -> Tuple[str, bool]:
    """Applies hardcoded static typo corrections on query patterns."""
    words: List[str] = re.split(r'(\b[a-zA-Z]+\b)', query)
    corrected_words: List[str] = []
    changed: bool = False
    for chunk in words:
        if chunk.isalpha():
            w_lower: str = chunk.lower()
            if w_lower in TYPO_OVERRIDES:
                corrected: str = TYPO_OVERRIDES[w_lower]
                if chunk.isupper():
                    corrected = corrected.upper()
                elif chunk[0].isupper():
                    corrected = corrected.capitalize()
                corrected_words.append(corrected)
                changed = True
            else:
                corrected_words.append(chunk)
        else:
            corrected_words.append(chunk)
    return "".join(corrected_words), changed


def highlight_diff(original: str, corrected: str) -> str:
    """Highlights differences between the original input and the auto-corrected query."""
    orig_words: List[str] = re.split(r'(\s+)', original)
    corr_words: List[str] = re.split(r'(\s+)', corrected)
    
    matcher = difflib.SequenceMatcher(None, orig_words, corr_words)
    result: List[str] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        chunk: str = "".join(corr_words[j1:j2])
        if op == 'equal':
            result.append(chunk)
        elif op in ('replace', 'insert'):
            if chunk.strip():
                # Bold Green formatting, disabling italics
                result.append(f"\033[23;1;32m{chunk}\033[0m\033[3m")
            else:
                result.append(chunk)
    return "".join(result)


def check_query_spelling_offline(query: str) -> Tuple[str, bool]:
    """Runs high-speed local dictionary edit-distance corrections."""
    words: List[str] = re.split(r'(\b[a-zA-Z]+\b)', query)
    corrected_words: List[str] = []
    changed: bool = False
    for chunk in words:
        if chunk.isalpha():
            corrected: str = correct_word(chunk)
            if corrected != chunk:
                changed = True
            corrected_words.append(corrected)
        else:
            corrected_words.append(chunk)
    return "".join(corrected_words), changed


def check_query_spelling(query: str, get_key_fn: Callable[[], str]) -> Tuple[str, str]:
    """Runs spellcheck verification pipelines with fallback priorities."""
    original_input: str = query
    query, changed_static = apply_static_overrides(query)
    corrected_query: str = query
    changed: bool = changed_static
    used_grammar_server: bool = False

    endpoints: List[str] = [
        "http://localhost:8010/v2/check",
        "http://localhost:8081/v2/check",
        "https://api.languagetool.org/v2/check"
    ]
    response_data: Optional[Dict[str, Any]] = None
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

    if response_data and "matches" in response_data:
        matches: List[Dict[str, Any]] = response_data["matches"]
        if matches:
            matches.sort(key=lambda m: m.get("offset", 0), reverse=True)
            chars: List[str] = list(query)
            for match in matches:
                offset: Optional[int] = match.get("offset")
                length: Optional[int] = match.get("length")
                replacements: List[Dict[str, Any]] = match.get("replacements", [])
                
                if replacements and offset is not None and length is not None:
                    best_correction: Optional[str] = replacements[0].get("value")
                    if best_correction is not None:
                        original_word: str = query[offset : offset + length]
                        
                        if original_word.lower() in PROTECTED_WORDS:
                            continue
                        
                        if original_word and best_correction and original_word.isalpha():
                            local_cand: str = correct_word(original_word)
                            if local_cand != original_word and local_cand.lower() != best_correction.lower():
                                def get_prio(w: str) -> int:
                                    w_low = w.lower()
                                    orig_low = original_word.lower()
                                    return 1 if (sorted(w_low) == sorted(orig_low)) else 2 if len(w_low) - len(orig_low) == 1 else 3 if len(w_low) - len(orig_low) == 0 else 4
                                
                                local_prio = get_prio(local_cand)
                                api_prio = get_prio(best_correction)
                                orig_first = original_word[0].lower()
                                api_first = best_correction[0].lower()
                                local_first = local_cand[0].lower()
                                
                                if local_prio < api_prio or (api_first != orig_first and local_first == orig_first):
                                    best_correction = local_cand
                        
                        chars[offset : offset + length] = list(best_correction)
                        changed = True
            corrected_query = "".join(chars)

    if not used_grammar_server and not changed_static:
        corrected_query, changed = check_query_spelling_offline(query)

    if changed and corrected_query.strip().lower() != original_input.strip().lower():
        highlighted: str = highlight_diff(original_input, corrected_query)
        
        sys.stderr.write(
            f"\n\033[2m[sys] Typos detected. Correct query to:\033[0m\n"
            f"\033[3m   \"{highlighted}\"\033[0m\n"
            f"\033[2m   [↵ accept  Tab: edit  d: disable  Esc: skip]: \033[0m"
        )
        sys.stderr.flush()
        
        key: str = get_key_fn()
        cols: int = shutil.get_terminal_size().columns or 80
        
        # Strictly measure dynamic wrapped lines to perform clean console cursor recovery
        line1_len: int = len("[sys] Typos detected. Correct query to:")
        line2_len: int = 3 + len(corrected_query) + 1
        line3_len: int = len("   [↵ accept  Tab: edit  d: disable  Esc: skip]: ")
        
        lines1: int = (line1_len + cols - 1) // cols
        lines2: int = (line2_len + cols - 1) // cols
        lines3: int = (line3_len + cols - 1) // cols
        
        total_lines: int = 1 + lines1 + lines2 + lines3  # +1 represents leading newline
        clear_prompt: str = "\r\x1b[K" + "\x1b[1A\r\x1b[K" * (total_lines - 1)

        if key in ('\r', '\n', ''):
            # Calculate dynamic rollback rows
            prompt_len: int = 2 + len(original_input)  # '❯ ' + query
            prompt_lines: int = (prompt_len + cols - 1) // cols
            
            rollback_distance: int = (total_lines - 1) + prompt_lines
            sys.stderr.write(f"\r\x1b[{rollback_distance}A\r\x1b[J")
            sys.stderr.write(f"\033[1;30m❯\033[0m {corrected_query}\n")
            sys.stderr.flush()
            return "RUN", corrected_query
            
        elif key in ('\t', 'e', 'E'):
            sys.stderr.write(clear_prompt)
            sys.stderr.write("\033[2;33m[sys] Returning to editor...\033[0m\n")
            sys.stderr.flush()
            return "EDIT", original_input
        elif key in ('d', 'D'):
            sys.stderr.write(clear_prompt)
            sys.stderr.write("\033[2;31m[sys] Spellchecker disabled. (Type /spell to re-enable)\033[0m\n")
            sys.stderr.flush()
            return "DISABLE", original_input
        else:
            sys.stderr.write(clear_prompt)
            sys.stderr.flush()
            
    return "RUN", original_input
