# Local-AI Blueprint

> **Syntax**: `[command / execution] ──> [intent1], [intent2], [intent3]`  
> **Delimiter**: `" ---> "` (Three-dash arrow with a trailing space)

---

### Syntax Guide
1. `~/path`: Index workspace and launch session.
2. `ai init --<skill>`: Index workspace with primed skill.
3. `[TOOL] <command> [--s]`: Run background context tool.
4. `<command>`: Launch terminal alias or viewer (`view`).

---

## 0. Core Level

```properties
# --- IPython RLM Kernel Harness Toggle ---
~/.config/local-ai/modules/agent_ipython.py ---> ipython, python harness, ipy, py harness
```

## 1. Voice & TTS

```properties
# --- Voice to Text ---
~/.config/local-ai/modules/agent_voice.py ---> voice, voice query, voice bridge, voice to text, v2t
# --- Text to Speech (TTS) ---
pkill -9 -f "pw-play|koko" ---> stop speech, kill tts, quiet, stop talking, tts
```

## 2. Workspaces

```properties
# --- Workspaces ---
ai init ~/.config/local-ai/projects/session-test ---> session test, projects session, projects
ai init ~/.config/local-ai/projects/session-test-2 ---> session test 2, projects session, projects
ai init ~/.config/local-ai/projects/session-test-3 ---> session test 3, projects session, projects
```

## 3. Codebase Map

```properties
# --- Index Map ---
[TOOL] ~/.config/local-ai/tools/map/index-map --cat ---> index map, imap
```

## 4. Web & Files

```properties
# --- Web Reader ---
[TOOL] ~/.config/local-ai/tools/agentic/web/web-reader web $1 ---> web reader, webr
[TOOL] ~/.config/local-ai/tools/agentic/web/web-reader youtube $1 ---> web reader yt, webr
# --- File Reader ---
[TOOL] cat $1 ---> view file, read file, show file, vf
# --- Memories ---
[TOOL] view .agent/tpm.md | less -R ---> show memories, mem
[TOOL] read -p "Search Memories: " query && view .agent/tpm.md | grep --color=always -A 5 -B 2 -i "$query" ---> search memories, ms
# --- History ---
[TOOL] view history.md | less -R ---> show history, hist, history
[TOOL] read -p "Search Page: " query && view history.md | grep --color=always -A 15 -B 2 -i "$query" ---> search page, hs
```

## 5. System & Health

```properties
# --- AI Status ---
[TOOL] ~/.config/local-ai/tools/agentic/system/ai-status ---> ai status, aistat, status, route
# --- System Health ---
[TOOL] ~/.config/local-ai/tools/agentic/system/system-health ---> system health, sysh
# --- Log Checker ---
[TOOL] ~/.config/local-ai/tools/agentic/system/log-checker ---> log checker, ailog
# --- AUR Audit ---
[TOOL] ~/.config/local-ai/tools/agentic/system/aur-audit ---> aur audit, audit package
# --- Security Audit ---
[TOOL] ~/.config/local-ai/tools/agentic/system/security-audit ---> security audit, secaud, system audit
# --- System Optimizer ---
[TOOL] ~/.config/local-ai/tools/agentic/system/system-optimizer ---> system optimizer, sysop
# --- System Profile ---
[TOOL] cat ~/.config/local-ai/skills/system/mysys.md ---> mysys
[TOOL] ~/.config/local-ai/tools/generate-profile ---> generate profile, sync mysys
# --- Update Inspector ---
[TOOL] ~/.config/local-ai/tools/agentic/system/update-inspector ---> update inspector
# --- Weather ---
[TOOL] curl -s "wttr.in/?format=3" --cat ---> weather simple, wttr, weather
[TOOL] curl -s wttr.in --cat ---> weather full, wttr, weather
# --- Time & Date ---
[TOOL] date "+TIME: %I:%M:%S %p %Z, %A, %B %d, %Y" ---> time, date, current time, what time is it
```

## 6. TUI Apps

```properties
# --- Model Select TUI ---
~/.config/local-ai/modules/model-select.py ---> model select, models select, mst
# --- Email TUI ---
[TOOL] ~/.config/local-ai/tools/email/email-agent ---> email agent
# --- Hyprland State ---
~/.config/local-ai/tools/subsec/hyprstate/work ---> hyprstate work, hyprwork
~/.config/local-ai/tools/subsec/hyprstate/gitcom ---> hyprstate gitcom, gitcom
```

## 7. Tools & Utilities

```properties
# --- Blueprint ---
[TOOL] ~/.config/local-ai/tools/blueprint ---> cheatsheet, bp, cs, blueprint
# --- AI Commit ---
~/.config/local-ai/tools/agentic/system/ai-commit ---> ai-commit, gc, git commit
```
