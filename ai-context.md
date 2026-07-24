# Local-AI Agent Blueprint

> **Syntax**: `[command / execution] ──> [intent1], [intent2], [intent3]`  
> **Delimiter**: `" ---> "` (Three-dash arrow with a trailing space)

---

### Directional Syntax Guide
1. `~/path`: Indexes workspace and launches a standard AI Workspace.
2. `ai init --<skill>`: Indexes codebase workspace pre-primed with a chosen `--<skill>` (e.g., `--init` or `--coder`).
3. `[TOOL] <command> [--s]`: Runs a background utility to inject dynamic Markdown context (append ` --s` to bypass confirmation).
4. `<command>`: Launches a native terminal alias, interactive TUI, or document viewer (using `view`, `leaf`, or `glow`).

---

## 1. Active Workspaces & Session Control

```properties
# --- Active Project Workspace Initialization ---
ai init ~/.config/local-ai/projects/session-test --init ---> session test, projects session, projects
ai init ~/.config/local-ai/projects/session-test-2 --init ---> session test 2, projects session, projects
ai init ~/.config/local-ai/projects/session-test-3 --init ---> session test 3, projects session, projects
```

## 2. Codebase Mapping & Relational Context

```properties
# --- Index-Map (Graph-Enabled Code Intelligence Engine) ---
[TOOL] ~/.config/local-ai/tools/map/index-map --cat ---> index map, imap

# --- Codebase Structural Tracing & Snippet Retrieval ---
[TOOL] ~/.config/local-ai/tools/map/index-map trace $1 --cat ---> trace symbol
[TOOL] ~/.config/local-ai/tools/map/index-map blast-radius $1 --cat ---> blast radius
[TOOL] ~/.config/local-ai/tools/map/index-map snippet $1 --cat ---> read function
[TOOL] ~/.config/local-ai/tools/map/index-map architecture --cat ---> architecture overview

# --- Hybrid Semantic Codebase Search (sqlite-vec Enabled) ---
[TOOL] ~/.config/local-ai/tools/map/index-map search $1 --cat ---> find symbol, semantic search, find concept, search code
```

## 3. Core Retrieval, Scraping & Web Research

```properties
# --- Web-Reader (Web Scraper & YouTube Subtitle Extractor) ---
[TOOL] ~/.config/local-ai/tools/agentic/web/web-reader web $1 ---> web reader, webr
[TOOL] ~/.config/local-ai/tools/agentic/web/web-reader youtube $1 ---> web reader yt, webr

# --- Dynamic File Reader ---
[TOOL] cat $1 ---> view file, read file, show file, vf

# --- Active Workspace Memory Viewer & Searcher ---
[TOOL] view .agent/tpm.md | less -R ---> show memories, mem
[TOOL] read -p "Search Memories: " query && view .agent/tpm.md | grep --color=always -A 5 -B 2 -i "$query" ---> search memories, ms

# --- Active Workspace History Viewer & Searcher ---
[TOOL] view history.md | less -R ---> show history, hist, history
[TOOL] read -p "Search Page: " query && view history.md | grep --color=always -A 15 -B 2 -i "$query" ---> search page, hs
```

## 4. System Diagnostics & Performance Optimization

```properties
# --- AI Status & Provider Diagnostics ---
[TOOL] ~/.config/local-ai/tools/agentic/system/ai-status ---> ai status, aistat, status, route

# --- System Resources & Diagnosis (System Health) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/system-health ---> system health, sysh

# --- System Logs & Diagnostics (Compressed Stream Triage) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/log-checker ---> log checker, ailog

# --- Pre-Install Zero-Trust AUR Package & PKGBUILD Auditor ---
[TOOL] ~/.config/local-ai/tools/agentic/system/aur-audit ---> aur audit, audit package

# --- Host Security Surface & Vulnerability Intelligence (SECAUD) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/security-audit ---> security audit, secaud, system audit

# --- System Optimization (Improve System Performance) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/system-optimizer ---> system optimizer, sysop

# --- Dynamic Host Profiler & System Analytics ---
[TOOL] cat ~/.config/local-ai/skills/system/mysys.md ---> mysys
[TOOL] ~/.config/local-ai/tools/generate-profile ---> generate profile, sync mysys

# --- Pending System Updates ---
[TOOL] ~/.config/local-ai/tools/agentic/system/update-inspector ---> update inspector

# --- Weather & Live Networking ---
[TOOL] curl -s "wttr.in/?format=3" --cat ---> weather simple, wttr, weather
[TOOL] curl -s wttr.in --cat ---> weather full, wttr, weather

# --- System Time & Date (Real-time Clock Context) ---
[TOOL] date "+TIME: %I:%M:%S %p %Z, %A, %B %d, %Y (STRICT: Output ONLY time/date. No extra conversation.)" ---> time, date, current time, what time is it
```

## 5. Interactive TUI (Terminal User Interface) Programs

```properties
# --- Dynamic Local-AI Model Select TUI ---
~/.config/local-ai/modules/model-select.py ---> model select, models select, mst

# --- Email TUI Monitor & Inbox Browser ---
[TOOL] ~/.config/local-ai/tools/email/email-agent ---> email agent

# --- Custom Basepage & BaseTracker RSS TUI Applications ---
~/.config/local-ai/tools/subsec/basepage-tui/basepage.py ---> basepage
~/.config/local-ai/tools/subsec/basepage-tui/basetracker.py ---> basetracker

# --- Media & Volume Controllers (Pure Reactive Winamp-TUI) ---
~/.config/local-ai/tools/subsec/media/media.py ---> tuiamp

# --- Article & YouTube Text-Snippet Summarizers ---
~/.config/local-ai/tools/subsec/ai-summary/llmsum.py ---> llmsum

# --- Local Stopwatch TUI Utility ---
~/.config/local-ai/tools/subsec/stopwatch/stopwatch.py ---> stopwatch py, stopwatch
~/.config/local-ai/tools/subsec/stopwatch/stopwatch.sh ---> stopwatch sh, stopwatch

# --- Shell Notes Utility ---
~/.config/local-ai/tools/subsec/notes/notes.sh ---> add notes, open notes

# --- Local Window Manager (Hyprland) State Controllers ---
~/.config/local-ai/tools/subsec/hyprstate/work ---> hyprstate work, work
~/.config/local-ai/tools/subsec/hyprstate/gitcom ---> hyprstate gitcom, gitcom
~/.config/local-ai/tools/subsec/hyprstate/gitcom2 ---> hyprstate gitcom 2, gitcom
```

## 6. Graphical Integration & Workspace Launchers

```properties
# --- Local-Ai Agent Blueprint (System CheatSheet Viewer) ---
[TOOL] ~/.config/local-ai/tools/blueprint ---> cheatsheet, bp, cs, blueprint

# --- AI-Generated Git Commits ---
~/.config/local-ai/tools/agentic/system/ai-commit ---> ai-commit, gc, git commit

# --- Native Webapp Wrappers & Browsers ---
omarchy-launch-webapp https://music.youtube.com/ ---> youtube music, yt, youtube
nohup uwsm app -- brave-origin --user-data-dir="~/.config/BraveSoftware/brave-spotify-bunker" --app=https://open.spotify.com/ >/dev/null 2>&1 & ---> spotify music, spotify, music
```
