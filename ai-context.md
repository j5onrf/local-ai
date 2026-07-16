# Local-AI Agent Blueprint

> **Syntax**: `[command / execution] ──> [intent1], [intent2], [intent3]`  
> **Delimiter**: `" ---> "` (Three-dash arrow with a trailing space)

---

### Directional Syntax Guide
1. `~/path`: Indexes workspace and launches a standard AI Workspace.
2. `ai init --<skill>`: Indexes codebase workspace pre-primed with a chosen `--<skill>` (e.g., `--init` or `--coder`).
3. `[TOOL] <command> [--s]`: Runs a background utility to inject dynamic Markdown context (append ` --s` to bypass confirmation).
4. `<command>`: Launches a native terminal alias, interactive TUI, or document viewer (using `mdcat`, `leaf`, or `glow`).

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
[TOOL] mdcat .agent/tpm.md | less -R ---> show memories, mem
[TOOL] read -p "Search Memories: " query && mdcat .agent/tpm.md | grep --color=always -A 5 -B 2 -i "$query" ---> search memories, ms

# --- Active Workspace History Viewer & Searcher ---
[TOOL] mdcat history.md | less -R ---> show history, hist, history
[TOOL] read -p "Search Page: " query && mdcat history.md | grep --color=always -A 15 -B 2 -i "$query" ---> search page, hs
```

## 4. System Diagnostics & Performance Optimization

```properties
# --- AI Status & Provider Diagnostics ---
[TOOL] ~/.config/local-ai/tools/agentic/system/ai-status --s ---> ai status, aistat, status, aistatus 

# --- System Resources & Diagnosis (System Health) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/system-health ---> system health, sysh

# --- System Logs & Diagnostics (Compressed Stream Triage) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/log-checker ---> log checker, ailog

# --- Pre-Install Zero-Trust AUR Package & PKGBUILD Auditor ---
[TOOL] ~/.config/local-ai/tools/agentic/system/aur-audit ---> aur audit, audit package

# --- Host Security Surface & Vulnerability Intelligence (SECAUD) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/security-audit --leaf ---> security audit, secaud, system audit

# --- System Optimization (Improve System Performance) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/system-optimizer --leaf ---> system optimizer, sysop

# --- Dynamic Host Profiler & System Analytics ---
[TOOL] cat ~/.config/local-ai/skills/system/mysys.md --leaf ---> mysys
[TOOL] ~/.config/local-ai/tools/generate-profile ---> generate profile, sync mysys

# --- Pending System Updates ---
[TOOL] ~/.config/local-ai/tools/agentic/system/update-inspector --leaf ---> update inspector
# --- Weather & Live Networking ---
[TOOL] curl -s "wttr.in/?format=3" --cat ---> weather simple, wttr, weather
[TOOL] curl -s wttr.in --cat ---> weather full, wttr, weather

# --- System Time & Date (Real-time Clock Context) ---
[TOOL] date "+Current Time: %I:%M:%S %p %Z on %A, %B %d, %Y" ---> time, date, current time, what time is it
```

## 5. Interactive TUI (Terminal User Interface) Programs

```properties
# --- Dynamic Local-AI Model Select TUI ---
~/.config/local-ai/modules/model-select.py ---> model select, model selector, model selection, mst

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
~/.config/local-ai/tools/blueprint --s --leaf ---> cheatsheet, bp, cs, blueprint

# --- AI-Generated Git Commits ---
~/.config/local-ai/tools/agentic/system/ai-commit ---> ai-commit, gc, git commit

# --- System App Launcher (Ultra-Light Rofi-TUI) ---
~/.config/local-ai/tools/subsec/app-launcher/app-launcher.py ---> app launcher, appl

# --- Native Webapp Wrappers & Browsers ---
omarchy-launch-webapp https://music.youtube.com/ ---> youtube music, yt, youtube
nohup uwsm app -- brave-origin --user-data-dir="~/.config/BraveSoftware/brave-spotify-bunker" --app=https://open.spotify.com/ >/dev/null 2>&1 & ---> spotify music, spotify, music
```

```
# =========================================================================
# === ARCHIVED & LEGACY PROFILES (SKIPPED DURING ACTIVE CONTEXT RUNS) ===
# =========================================================================

# --- Firecrawl Web Scraper (Replaced by ultra-light web-reader) ---
# [TOOL] ~/.config/local-ai/tools/agentic/web/firecrawl $1 ---> firecrawl, scrape website, scrape url, extract text

# --- Workspace Initializers & Bridges ---
# [TOOL] ~/.config/local-ai/tools/subsec/opencode-bridge/opencode-bridge ---> opencode bridge, bridge, ocb
# [TOOL] ~/.config/local-ai/tools/subsec/odysseus-bridge/odysseus-bridge ---> odysseus bridge, bridge, ody, odb
# [TOOL] ~/.config/local-ai/tools/subsec/hermes-bridge/hermes-bridge ---> hermes bridge, bridge, hmb, herm

# --- System Prompts & Role Injections (Skills) ---
# [TOOL] cat ~/.config/local-ai/skills/identity/business/mybiz.md --leaf ---> mybiz, show business profile, view mybiz
# [TOOL] cat ~/.config/local-ai/skills/identity/marketing/strategy.md --leaf ---> marketing strategy, growth strategy, view marketing
# [TOOL] cat ~/.config/local-ai/skills/identity/workout/routine.md --leaf ---> routine, fitness profile, workout routine

# --- Disk Usage ---
# [TOOL] df -h / ---> disk usage, drive usage

# --- Server Lifecycle Management ---
# ~/.config/local-ai/tools/tools/subsec/server/kill-ai-servers ---> killserver, ks

# --- Prompt Engineering TUIs ---
# [TOOL] ~/.config/local-ai/tools/subsec/prompt/ai-prompt-writer-image --cat ---> prompt writer image, image prompt, ip
# [TOOL] ~/.config/local-ai/tools/subsec/prompt/ai-prompt-writer --cat ---> prompt writer, prompt

# --- Research Engines ---
# ~/.config/local-ai/tools/agentic/fusion/f_research -r ---> fusion research, fusion, fr, deep research
# ~/.config/local-ai/tools/subsec/research-tui/deep-research ---> deep research, research, dr

# --- Local-Ai Tablet Voice Bridge ---
# ~/.config/local-ai/tools/subsec/voice/voice-query ---> voice, voice query, voice bridge

# --- Pixel-Browse - Headless Visual Web Ingestion (wip) ---
# [TOOL] ~/.config/local-ai/tools/subsec/headless-chromium/pixel-browse --cat ---> pixel browse, headless, chromium, pixel browser

# --- Coding-Triangle-Loop - Interactive TUI Console (wip) ---
# [TOOL] ~/.config/local-ai/tools/agentic/coding/coding-triangle-loop --cat ---> coding loop, coding, triangle, loop
```
