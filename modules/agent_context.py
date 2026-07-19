# File: ~/.config/local-ai/modules/agent_context.py
import os
import re
import fnmatch
import shutil
import sys
from typing import List, Set, Dict, Any, Optional, Tuple

_CACHED_ENTRIES: Optional[List[Dict[str, Any]]] = None
_LAST_M_TIME: float = 0.0
TOKEN_RE: re.Pattern = re.compile(r"[^\w\s]")


def tokenize(text: str, stop_words: Set[str]) -> List[str]:
    """Cleans, splits, and tokenizes strings while excluding standard stop words."""
    if not text:
        return []
    cleaned: str = TOKEN_RE.sub(" ", text.lower())
    return [w for w in cleaned.split() if len(w) > 1 and w not in stop_words]


def load_context_entries(context_file: str, stop_words: Set[str]) -> List[Dict[str, Any]]:
    """Reads context blueprint and parses intent mappings with strict mtime caching."""
    global _CACHED_ENTRIES, _LAST_M_TIME
    if not os.path.exists(context_file):
        return []
    try:
        current_mtime: float = os.path.getmtime(context_file)
        if _CACHED_ENTRIES is not None and current_mtime <= _LAST_M_TIME:
            return _CACHED_ENTRIES
            
        with open(context_file, "r", encoding="utf-8") as f:
            lines: List[str] = [
                cleaned for line in f.read().splitlines()
                if (cleaned := line.strip()) and not cleaned.startswith("#") and "--->" in cleaned
            ]
            
        parsed_entries: List[Dict[str, Any]] = []
        for line in lines:
            cmd, intents_str = line.split("--->", 1)
            intents: List[str] = [intent.strip() for intent in intents_str.split(",") if intent.strip()]
            if not intents:
                continue
            for intent in intents:
                tokens: List[str] = tokenize(intent, stop_words)
                if tokens:
                    parsed_entries.append({
                        "cmd": cmd.strip(),
                        "intent": intent,
                        "primary": intents[0],
                        "tokens": tokens
                    })
        _CACHED_ENTRIES = parsed_entries
        _LAST_M_TIME = current_mtime
        return _CACHED_ENTRIES
    except Exception as e:
        sys.stderr.write(f"\033[1;31m[sys] Error parsing context metadata: {e}\033[0m\n")
        return []


def jaccard_search(query: str, context_file: str, stop_words: Set[str], threshold: float = 0.45) -> Optional[str]:
    """Computes Jaccard index intersections to locate and rank mapped intents."""
    q_clean: str = query.strip().lower()
    q_tokens: Set[str] = set(tokenize(query, stop_words))
    if not q_tokens:
        return None
        
    entries: List[Dict[str, Any]] = load_context_entries(context_file, stop_words)
    if not entries:
        return None
        
    candidates: List[Tuple[float, str, str]] = []
    for entry in entries:
        ent_tokens: Set[str] = set(entry["tokens"])
        ent_clean: str = entry["intent"].strip().lower()
        
        intersection: Set[str] = q_tokens & ent_tokens
        union: Set[str] = q_tokens | ent_tokens
        score: float = len(intersection) / len(union) if union else 0.0
        
        if q_clean in ent_clean:
            score = max(score, 0.8)
        if q_clean == ent_clean:
            score = 3.0
            
        if score >= threshold:
            candidates.append((score, entry["cmd"], entry.get("primary", entry["intent"])))
            
    if not candidates:
        return None
        
    # Sort descending by score, ascending by length of primary string
    candidates.sort(key=lambda x: (-x[0], len(x[2])))
    
    seen: Set[str] = set()
    top_entries: List[str] = []
    for _, cmd, primary in candidates:
        if cmd not in seen and len(top_entries) < 5:
            seen.add(cmd)
            top_entries.append(f"{primary}|||{clean_tool_prefix(cmd)}")
            
    return "\n".join(top_entries)


def clean_tool_prefix(cmd: str) -> str:
    """Strips command metadata and appends default shell pagers."""
    is_tool: bool = cmd.startswith("[TOOL]")
    cleaned: str = cmd.replace("[TOOL]", "", 1).strip() if is_tool else cmd
    
    if cleaned.startswith("DANGER_FLAGGED:"):
        cleaned = f"DANGER_FLAGGED:{cleaned.replace('DANGER_FLAGGED:', '').replace('[TOOL]', '').strip()}"
        
    cleaned = cleaned.replace(" --s", "").strip()
    pager: str = ""
    
    # We replaced deprecated "mdcat" with our new unified smart shell utility "view"
    pagers: List[Tuple[str, str]] = [
        (" --leaf", "leaf"), 
        (" --glow", "glow"), 
        (" --cat", "cat"), 
        (" --view", "view")
    ]
    for flag, pg in pagers:
        if cleaned.endswith(flag):
            cleaned = cleaned[:-len(flag)].strip()
            pager = pg
            break
            
    if not pager and is_tool:
        # Defaults tools straight to view so markdown outputs are automatically formatted via rich.markdown
        pager = "view"
        
    if pager:
        return f"{cleaned} | {pager}"
    return cleaned
