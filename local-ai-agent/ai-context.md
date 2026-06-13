# Local-AI Agent Blueprint

> **Syntax**: `[command / execution] ---\> [intent1], [intent2], [intent3]`  
> **Delimiter**: `" ---> "` (Three-dash arrow with a trailing space)

---

### Directional Syntax Guide
1. **Directory Path**: Indexes workspace and launches standard AI Workspace.
2. **'ai init' + Skill**: Indexes workspace and launches AI pre-primed with Skill.
3. **'[TOOL] command'**: Runs local utility to inject dynamic Markdown context.
4. **Raw Command**: Native terminal alias, interactive TUI, or document viewer.

---

## 1. Workspace Initializers & Bridges

```properties
# --- OpenCode Direct Terminal Launcher ---
~/.config/local-ai/opencode-bridge/opencode-bridge ---> opencode bridge, ocb

# --- Odysseus Direct Terminal Launcher ---
~/.config/local-ai/odysseus-bridge/odysseus-bridge ---> odysseus bridge. ody, odb

# --- Hermes Direct Browser Workspace Launcher ---
~/.config/local-ai/hermes-bridge/hermes-bridge ---> hermes bridge, hmb, herm

# --- Standard Codebase Workspaces (Dynamic Auto-Init) ---
# (Triggers standard ai init on the directory tree when matched)
~/Projects/qwen-hypr ---> projects qwen, projects

# --- Specialized Codebase Workspaces (Skill-Primed) ---
# (Specialized project initializations primed with the "coder" Skill!)
ai init ~/Projects/quickshell coder ---> projects quickshell, projects
```

## 2. On-Demand System Prompts & Role Injections (Skills)

```properties
# --- Skills (Prompt & Role Injection) ---
[TOOL] cat ~/.config/local-ai/local-ai-agent/tools/skills/sysadmin.md ---> sysadmin, show sysadmin, sysadmin manual
[TOOL] cat ~/.config/local-ai/local-ai-agent/tools/skills/mysys.md ---> mysys, show mysys, view mysys, mysys doc
```

## 3. Dynamic Context-Injected Tools (RAG)

```properties
# --- Pre-Install Zero-Trust AUR Package & PKGBUILD Auditor ---
~/.config/local-ai/local-ai-agent/tools/agentic/aur-audit ---> audit package, audit pkg, check pkgbuild, aur audit, scan aur, verify pkgbuild, pre-install check

# --- Host Security Surface & Vulnerability Intelligence (SECAUD) ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/security-audit ---> security audit, secaud, audit system security, scan for vulnerabilities

# --- System Optimization (mysys skill primed) ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/system-optimize --->  system optimize, sysop, system optimization

# --- System Logs & Diagnostics (Compressed Stream Triage) ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/log-checker ---> log checker, ailog, log check, check errors, system crashed, events

# --- System Resources & Diagnosis (System health) ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/system-diagnosis ---> system health, sysh, health, system diagnosis, why is my system slow

[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/update-inspector ---> update inspector, ui, check upgrades, what updates do i have, pending updates, what updates do i have pending

[TOOL] df -h / ---> disk usage, nvme drive usage, check storage space

# --- AI Status & Provider Diagnostics ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/ai-status ---> status, aistatus, aistat, ai-status

# --- Weather & Live Networking ---
[TOOL] curl -s "wttr.in/?format=3" ---> weather simple, wttr, weather, rain forecast simple
[TOOL] curl -s wttr.in ---> weather full, wttr, weather, rain forecast full

# --- System Time & Date (Real-time Clock Context) ---
[TOOL] date ---> time, date, current time, what time is it, system date, system time
```

## 4. Static Aliases & Shell Shortcuts

```properties
# --- Local-Ai Agent Blueprint Map (CheatSheet) (Optional: leaf, glow) ---
~/.config/local-ai/local-ai-agent/tools/blueprint | mdcat ---> cheatsheet, blueprint, bp, cs, map
~/.config/local-ai/local-ai-agent/tools/blueprint | leaf ---> cheatsheet leaf, blueprint, bp, cs, map

# --- AI-Generated Git Commits ---
~/.config/local-ai/local-ai-agent/tools/agentic/ai-commit ---> ai-commit, gc, git-commit, git commit

# --- Server Lifecycle Management ---
~/.config/local-ai/local-ai-agent/tools/kill-ai-servers ---> killserver, ks
```

## 5. TUI (Terminal User Interface) Programs

```properties
# --- AI Deep Research TUI ---
/home/j5/.config/local-ai/research-tui/deep-research ---> deep research, research, dr

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
/home/j5/.config/local-ai/voice/voice-query ---> voice, voice query, voice bridge

# --- System App Launcher (Ultra-Light Rofi-TUI) ---
~/.config/local-ai/local-ai-agent/tools/subsec/app-launcher/app-launcher.py ---> app launcher, app

# --- Native Webapp Wrappers & Browsers ---
omarchy-launch-webapp https://music.youtube.com/ ---> youtube music, yt, yt music, youtube

nohup uwsm app -- brave-origin --user-data-dir="~/.config/BraveSoftware/brave-spotify-bunker" --app=https://open.spotify.com/ >/dev/null 2>&1 & ---> spotify music, spotify, music
```

## 7. Subsection Applications

```properties
# --- Stopwatch ---
~/.config/local-ai/local-ai-agent/tools/subsec/stopwatch/stopwatch.py ---> stopwatch py, sw, stop watch
~/.config/local-ai/local-ai-agent/tools/subsec/stopwatch/stopwatch.sh ---> stopwatch sh, sw, stop watch

# --- Notes ---
~/.config/local-ai/local-ai-agent/tools/subsec/notes/notes.sh ---> notes, open notes, add to notes

# --- State & Workflow Management ---
~/.config/local-ai/local-ai-agent/tools/subsec/hyprstate/work ---> hyprstate work, work, workspace
~/.config/local-ai/local-ai-agent/tools/subsec/hyprstate/clean ---> hyprstate clean, clean, workspace
~/.config/local-ai/local-ai-agent/tools/subsec/hyprstate/gitcom ---> hyprstate gitcom, gitcom, workspace
```

## 8. Continual Learning

```properties
# --- Learned System Shortcuts ---
ss -tuln ---> how do i view active network ports
hostnamectl ---> how do i see my system information
