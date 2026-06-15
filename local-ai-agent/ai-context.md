# Local-AI Agent Blueprint

> **Syntax**: `[command / execution] ---> [intent1], [intent2], [intent3]`  
> **Delimiter**: `" ---> "` (Three-dash arrow with a trailing space)

---

### Directional Syntax Guide
1. `~/path`: Indexes workspace and launches a standard AI Workspace.
2. `ai init --<skill>`: Indexes codebase workspace pre-primed with a chosen `--<skill>` (e.g., `--coder` or `--sysadmin`).
3. `[TOOL] <command>`: Runs a local utility (like `cat`, `curl`, or `date`) to inject dynamic Markdown context.
4. `<command>`: Launches a native terminal alias, interactive TUI, or document viewer (using `mdcat`, `leaf`, or `glow`).

---

## 1. Workspace Initializers & Bridges

```properties
# --- OpenCode Direct Terminal Launcher ---
~/.config/local-ai/opencode-bridge/opencode-bridge ---> opencode bridge, bridge, ocb

# --- Odysseus Direct Terminal Launcher ---
~/.config/local-ai/odysseus-bridge/odysseus-bridge ---> odysseus bridge, bridge, ody, odb

# --- Hermes Direct Browser Workspace Launcher ---
~/.config/local-ai/hermes-bridge/hermes-bridge ---> hermes bridge, bridge, hmb, herm

# --- Standard Codebase Workspaces (Dynamic Auto-Init) ---
~/Projects/qwen-hypr ---> projects qwen, projects

# --- Specialized Codebase Workspaces (Skill-Primed) ---
ai init ~/Projects/quickshell --coder ---> projects quickshell, projects
```

## 2. On-Demand System Prompts & Role Injections (Skills)

```properties
# --- Skills (Prompt & Role Injection) ---
[TOOL] cat ~/.config/local-ai/local-ai-agent/skills/system/mysys.md --leaf ---> mysys, show mysys, view sys, mysys doc
# [TOOL] cat ~/.config/local-ai/local-ai-agent/skills/identity/business/mybiz.md --leaf ---> mybiz, show business profile, view mybiz
# [TOOL] cat ~/.config/local-ai/local-ai-agent/skills/identity/marketing/strategy.md --leaf ---> marketing strategy, growth strategy, view marketing
# [TOOL] cat ~/.config/local-ai/local-ai-agent/skills/identity/workout/routine.md --leaf ---> routine, fitness profile, workout routine
```

## 3. Dynamic Context-Injected Tools (RAG)

```properties
# --- Pre-Install Zero-Trust AUR Package & PKGBUILD Auditor ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/aur-audit ---> audit package, audit pkg, check pkgbuild, aur audit, scan aur, verify pkgbuild, pre-install check

# --- Host Security Surface & Vulnerability Intelligence (SECAUD) ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/security-audit --leaf ---> security audit, secaud, system audit

# --- System Optimization (Improve System Performance) ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/system-optimize --leaf ---> system optimize, sysop, system optimization

# --- System Logs & Diagnostics (Compressed Stream Triage) ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/log-checker --leaf ---> log checker, ailog, log check, check errors, system crashed, events

# --- System Resources & Diagnosis (System Health) ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/system-health --leaf ---> system health, sysh, health, system diagnosis, why is my system slow

# --- Pending Updates ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/update-inspector --leaf ---> update inspector, ui, check upgrades, what updates do i have, pending updates

# --- Disk Usage ---
[TOOL] df -h / ---> disk usage, nvme drive usage, check storage space

# --- AI Status & Provider Diagnostics ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/ai-status --leaf ---> status, aistatus, aistat, ai-status

# --- Weather & Live Networking ---
# (Uses standard on-demand flags like --leaf, --glow, --mdcat, or --cat)
[TOOL] curl -s "wttr.in/?format=3" --cat ---> weather simple, wttr, weather, rain forecast simple
[TOOL] curl -s wttr.in --cat ---> weather full, wttr, weather, rain forecast full

# --- System Time & Date (Real-time Clock Context) ---
[TOOL] date ---> time, date, current time, what time is it, system date, system time

# [TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/identity/business/mybiz ---> run business tool, execution biz
# [TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/identity/marketing/marketing ---> run marketing tool, execute growth
# [TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/identity/workout/routine ---> run workout tool, routine metrics
```

## 4. Static Aliases & Shell Shortcuts

```properties
# --- Local-Ai Agent Blueprint Map (CheatSheet) ---
~/.config/local-ai/local-ai-agent/tools/blueprint --leaf ---> cheatsheet, blueprint, bp, cs, map

# --- AI-Generated Git Commits ---
~/.config/local-ai/local-ai-agent/tools/agentic/ai-commit ---> ai-commit, gc, git-commit, git commit

# --- Server Lifecycle Management ---
~/.config/local-ai/local-ai-agent/tools/kill-ai-servers ---> killserver, ks
```

## 5. TUI (Terminal User Interface) Programs

```properties
# --- AI Deep Research TUI ---
~/.config/local-ai/research-tui/deep-research ---> deep research, research, dr

# --- Custom TUI Applications ---
~/.config/local-ai/basepage-tui/basepage.py ---> basepage, base, basepage tui, rss
~/.config/local-ai/basepage-tui/basetracker.py ---> basetracker, base, basetracker tui

# --- Media & Volume Controllers (Pure Reactive) ---
~/.config/local-ai/local-ai-agent/tools/subsec/media/media.py ---> tuiamp, winamp, media

# --- Article Summarizers ---
~/.config/local-ai/ai-summary/llmsum.py ---> llmsum, ytsum, summary
```

## 6. Graphical Applications & Webapps

```properties
# --- Local-Ai Tablet Voice Bridge ---
~/.config/local-ai/voice/voice-query ---> voice, voice query, voice bridge

# --- System App Launcher (Ultra-Light Rofi-TUI) ---
~/.config/local-ai/local-ai-agent/tools/subsec/app-launcher/app-launcher.py ---> app launcher, app

# --- Native Webapp Wrappers & Browsers ---
omarchy-launch-webapp https://music.youtube.com/ ---> youtube music, yt, music, youtube
nohup uwsm app -- brave-origin --user-data-dir="~/.config/BraveSoftware/brave-spotify-bunker" --app=https://open.spotify.com/ >/dev/null 2>&1 & ---> spotify music, spotify, music
```

## 7. Subsection Applications

```properties
# --- Stopwatch ---
~/.config/local-ai/local-ai-agent/tools/subsec/stopwatch/stopwatch.py ---> stopwatch py, sw, stopwatch
~/.config/local-ai/local-ai-agent/tools/subsec/stopwatch/stopwatch.sh ---> stopwatch sh, sw, stopwatch

# --- Notes ---
~/.config/local-ai/local-ai-agent/tools/subsec/notes/notes.sh ---> notes, open notes, add to notes

# --- State & Workflow Management ---
~/.config/local-ai/local-ai-agent/tools/subsec/hyprstate/work ---> hyprstate work, work, hyprstate
~/.config/local-ai/local-ai-agent/tools/subsec/hyprstate/clean ---> hyprstate clean, clean, hyprstate
~/.config/local-ai/local-ai-agent/tools/subsec/hyprstate/gitcom ---> hyprstate gitcom, gitcom, hyprstate
~/.config/local-ai/local-ai-agent/tools/subsec/hyprstate/media ---> hyprstate media, media, hyprstate
```

## 8. Continual Learning

```properties
# --- Learned System Shortcuts ---
ss -tuln ---> how do i view active network ports, active ports, network ports
hostnamectl ---> how do i see my system information, system info, hostname
```
