# Local-AI Agent Blueprint

> **Syntax**: `[command / execution] ──> [intent1], [intent2], [intent3]`  
> **Delimiter**: `" ──> "` (Three-dash arrow with a trailing space)

---

### Directional Syntax Guide
1. `~/path`: Indexes workspace and launches a standard AI Workspace.
2. `ai init --<skill>`: Indexes codebase workspace pre-primed with a chosen `--<skill>` (e.g., `--coder` or `--prompt`).
3. `[TOOL] <command> [--s]`: Runs a background utility to inject dynamic Markdown context (append ` --s` to bypass confirmation).
4. `<command>`: Launches a native terminal alias, interactive TUI, or document viewer (using `mdcat`, `leaf`, or `glow`).

---

## 1. Workspace Initializers & Bridges

```properties
# --- OpenCode Direct Terminal Launcher ---
~/.config/local-ai/tools/subsec/opencode-bridge/opencode-bridge ---> opencode bridge, bridge, ocb

# --- Odysseus Direct Terminal Launcher ---
~/.config/local-ai/tools/subsec/odysseus-bridge/odysseus-bridge ---> odysseus bridge, bridge, ody, odb

# --- Hermes Direct Browser Workspace Launcher ---
~/.config/local-ai/tools/subsec/hermes-bridge/hermes-bridge ---> hermes bridge, bridge, hmb, herm

# --- Standard Codebase Workspaces (Dynamic Auto-Init) ---
~/Projects/qwen-hypr ---> projects qwen, projects

# --- Specialized Codebase Workspaces (Skill-Primed) ---
ai init ~/Projects/quickshell --coder ---> projects quickshell, projects
```

## 2. On-Demand System Prompts & Role Injections (Skills)

```properties
# --- Dynamic Host Profiler & System Analytics ---
[TOOL] cat ~/.config/local-ai/skills/system/mysys.md --leaf ---> mysys, show mysys, view sys, mysys doc

# --- Prompt Engineering & Optimization Engine ---
[TOOL] cat ~/.config/local-ai/skills/meta/prompt.md ---> prompt builder, prompt, optimize prompt

# [TOOL] cat ~/.config/local-ai/skills/identity/business/mybiz.md --leaf ---> mybiz, show business profile, view mybiz
# [TOOL] cat ~/.config/local-ai/skills/identity/marketing/strategy.md --leaf ---> marketing strategy, growth strategy, view marketing
# [TOOL] cat ~/.config/local-ai/skills/identity/workout/routine.md --leaf ---> routine, fitness profile, workout routine
```

## 3. Dynamic Context-Injected Tools (RAG)

```properties
# --- Pre-Install Zero-Trust AUR Package & PKGBUILD Auditor ---
[TOOL] ~/.config/local-ai/tools/agentic/system/aur-audit ---> audit package, aur audit

# --- Host Security Surface & Vulnerability Intelligence (SECAUD) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/security-audit --leaf ---> security audit, secaud, system audit

# --- System Optimization (Improve System Performance) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/system-optimizer --leaf ---> system optimizer, sysop, optimize

# --- System Logs & Diagnostics (Compressed Stream Triage) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/log-checker --leaf ---> log checker, ailog, log check, check errors, system crashed, events

# --- System Resources & Diagnosis (System Health) ---
[TOOL] ~/.config/local-ai/tools/agentic/system/system-health --leaf ---> system health, sysh, health, system diagnosis, why is my system slow

# --- Pending Updates ---
[TOOL] ~/.config/local-ai/tools/agentic/system/update-inspector --leaf ---> update inspector, inspector, ui

# --- Disk Usage ---
[TOOL] df -h / ---> disk usage, drive usage

# --- AI Status & Provider Diagnostics ---
[TOOL] ~/.config/local-ai/tools/agentic/system/ai-status --s --leaf ---> ai status, aistat, status, aistatus 

# --- Weather & Live Networking ---
[TOOL] curl -s wttr.in --s --cat ---> weather full, wttr, weather, rain forecast full
[TOOL] curl -s "wttr.in/?format=3" --s --cat ---> weather simple, wttr, weather, rain forecast simple

# --- System Time & Date (Real-time Clock Context) ---
[TOOL] date --s ---> time, date, current time, what time is it
```

## 4. Static Aliases & Shell Shortcuts

```properties
# --- Local-Ai Agent Blueprint (CheatSheet) ---
~/.config/local-ai/tools/blueprint --s --leaf ---> cheatsheet, bp, cs, blueprint

# --- AI-Generated Git Commits ---
~/.config/local-ai/tools/agentic/system/ai-commit ---> ai-commit, gc, git-commit, git commit

# --- Skeleton Map (Structural Repo Profile Compiler) ---
~/.config/local-ai/tools/map/skeleton-map ---> skeleton map, sm,

# --- Server Lifecycle Management ---
~/.config/local-ai/tools/kill-ai-servers ---> killserver, ks
```

## 5. TUI (Terminal User Interface) Programs

```properties
# --- Fusion-Research Engine (Compound MoA / Self-Fusion) ---
~/.config/local-ai/tools/agentic/fusion/f_research -r ---> fusion research, fusion, fr, deep research
# --- AI Deep Research TUI ---
~/.config/local-ai/tools/subsec/research-tui/deep-research ---> deep research, research, dr

# --- Custom TUI Applications ---
~/.config/local-ai/tools/subsec/basepage-tui/basepage.py ---> basepage, base, basepage tui, rss
~/.config/local-ai/tools/subsec/basepage-tui/basetracker.py ---> basetracker, base, basetracker tui

# --- Media & Volume Controllers (Pure Reactive) ---
~/.config/local-ai/tools/subsec/media/media.py ---> tuiamp, winamp, media

# --- Article Summarizers ---
~/.config/local-ai/tools/subsec/ai-summary/llmsum.py ---> llmsum, ytsum, summary, sum

# --- Local-Ai Tablet Voice Bridge ---
~/.config/local-ai/tools/subsec/voice/voice-query ---> voice, voice query, voice bridge
```

## 6. Graphical Applications & Webapps

```properties
# --- System App Launcher (Ultra-Light Rofi-TUI) ---
~/.config/local-ai/tools/subsec/app-launcher/app-launcher.py ---> app launcher, app

# --- Native Webapp Wrappers & Browsers ---
omarchy-launch-webapp https://music.youtube.com/ ---> youtube music, yt, music, youtube
nohup uwsm app -- brave-origin --user-data-dir="~/.config/BraveSoftware/brave-spotify-bunker" --app=https://open.spotify.com/ >/dev/null 2>&1 & ---> spotify music, spotify, music
```

## 7. Subsection Applications

```properties
# --- Stopwatch ---
~/.config/local-ai/tools/subsec/stopwatch/stopwatch.py ---> stopwatch py, sw, stopwatch
~/.config/local-ai/tools/subsec/stopwatch/stopwatch.sh ---> stopwatch sh, sw, stopwatch

# --- Notes ---
~/.config/local-ai/tools/subsec/notes/notes.sh ---> notes, open notes, add to notes

# --- State & Workflow Management ---
~/.config/local-ai/tools/subsec/hyprstate/work ---> hyprstate work, work, hs, hyprstate
~/.config/local-ai/tools/subsec/hyprstate/clean ---> hyprstate clean, clean, hs, hyprstate
~/.config/local-ai/tools/subsec/hyprstate/gitcom ---> hyprstate gitcom, gitcom, hs, hyprstate
~/.config/local-ai/tools/subsec/hyprstate/media ---> hyprstate media, media, hs, hyprstate
```

## 8. Continual Learning

```properties
# --- Learned System Shortcuts ---
ss -tuln ---> how do i view active network ports, active ports, network ports
hostnamectl ---> how do i see my system information, system info, hostname
```
