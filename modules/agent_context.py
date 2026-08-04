# File: ~/.config/local-ai/modules/agent_context.py
"""Local-AI Agent Context Search & Indexing Engine"""

import os, re, sys
from typing import List, Set, Dict, Any, Optional, Tuple

_CACHED_ENTRIES: Optional[List[Dict[str, Any]]] = None
_LAST_M_TIME: float = 0.0
TOKEN_RE: re.Pattern = re.compile(r"[^\w\s]")
STOP_WORDS: Set[str] = {"is", "what", "it", "do", "any", "i", "have", "the", "a", "an", "on", "to", "for", "me", "you", "my", "your", "we", "us", "are", "about", "in", "how"}


def tokenize(text: str, stop_words: Set[str] = STOP_WORDS) -> List[str]:
    """Cleans, splits, and tokenizes strings while excluding standard stop words."""
    return [w for w in TOKEN_RE.sub(" ", text.lower()).split() if len(w) > 1 and w not in stop_words] if text else []


def load_context_entries(context_file: str, stop_words: Set[str]) -> List[Dict[str, Any]]:
    """Reads context blueprint and parses intent mappings with strict mtime caching."""
    global _CACHED_ENTRIES, _LAST_M_TIME
    if not os.path.exists(context_file): return []
    try:
        current_mtime = os.path.getmtime(context_file)
        if _CACHED_ENTRIES is not None and current_mtime <= _LAST_M_TIME: return _CACHED_ENTRIES

        with open(context_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.read().splitlines() if (c := l.strip()) and not c.startswith("#") and "--->" in c]

        parsed: List[Dict[str, Any]] = []
        for line in lines:
            cmd, intents_str = line.split("--->", 1)
            cmd_clean = cmd.strip()
            for intent in [i.strip() for i in intents_str.split(",") if i.strip()]:
                if tokens := tokenize(intent, stop_words):
                    parsed.append({"cmd": cmd_clean, "intent": intent, "primary": intents_str.split(",")[0].strip(), "tokens": tokens, "tokens_set": set(tokens)})

        _CACHED_ENTRIES, _LAST_M_TIME = parsed, current_mtime
        return _CACHED_ENTRIES
    except Exception as e:
        sys.stderr.write(f"\033[1;31m[sys] Error parsing context metadata: {e}\033[0m\n")
        return []


def jaccard_search(query: str, context_file: str, stop_words: Set[str], threshold: float = 0.45) -> Optional[str]:
    """Computes Jaccard index intersections to locate and rank mapped intents."""
    q_clean, q_tokens = query.strip().lower(), set(tokenize(query, stop_words))
    if not q_tokens or not (entries := load_context_entries(context_file, stop_words)): return None

    candidates: List[Tuple[float, str, str]] = []
    for entry in entries:
        ent_tokens, ent_clean = entry["tokens_set"], entry["intent"].strip().lower()
        if not (inter_len := len(q_tokens & ent_tokens)) and q_clean not in ent_clean: continue
        union_len = len(q_tokens | ent_tokens)
        score = inter_len / union_len if union_len else 0.0

        if q_clean in ent_clean: score = max(score, 0.8)
        if q_clean == ent_clean: score = 3.0
        if score >= threshold: candidates.append((score, entry["cmd"], entry.get("primary", entry["intent"])))

    if not candidates: return None
    candidates.sort(key=lambda x: (-x[0], len(x[2])))

    seen, top_entries = set(), []
    for _, cmd, primary in candidates:
        if cmd not in seen and len(top_entries) < 5:
            seen.add(cmd)
            top_entries.append(f"{primary}|||{clean_tool_prefix(cmd)}")

    return "\n".join(top_entries)


def clean_tool_prefix(cmd: str) -> str:
    """Strips command metadata and appends default shell pagers."""
    is_tool = cmd.startswith("[TOOL]")
    cleaned = cmd.replace("[TOOL]", "", 1).strip() if is_tool else cmd
    if cleaned.startswith("DANGER_FLAGGED:"):
        cleaned = f"DANGER_FLAGGED:{cleaned.replace('DANGER_FLAGGED:', '').replace('[TOOL]', '').strip()}"

    cleaned = cleaned.replace(" --s", "").strip()
    pager = ""
    for flag, pg in ((" --leaf", "leaf"), (" --glow", "glow"), (" --cat", "cat"), (" --view", "view")):
        if cleaned.endswith(flag):
            cleaned, pager = cleaned[:-len(flag)].strip(), pg
            break

    if not pager and is_tool: pager = "view"
    return f"{cleaned} | {pager}" if pager else cleaned
