# Local-AI Agent (v0.8.3.2)

<img alt="Image_5e1xpv5e1xpv5e1x-3" src="https://github.com/user-attachments/assets/56fe2b60-0cbe-4f51-bc27-a35516f1088f" />

`Laguna-M.1` `Qwen3-Coder` `Gemini-3.1-Flash-Lite`

---

## How the Agent Works

All configurations, automations, and custom project workspaces are managed through a single markdown master blueprint: **`ai-context.md`**. The agent resolves your inputs into one of four execution paradigms:

* **No Session (Direct selections)**: Typing custom commands or shortcuts prompts a local, rarity-weighted sparse search matrix to select options instantly without querying an LLM.
* **Single-Turn Agent (`ai <query>`)**: Typing `ai <query>` instantly answers a single question and returns you directly to your Bash prompt, silently running local diagnostic tools to gather context when your keywords are matched.
* **Multi-Turn Chat (`ai` alone)**: Typing `ai` alone initiates an interactive, persistent conversation session with local state preservation and multi-turn context memory.
* **Workspace Agents (`ai init <path>`)**: Compiles a path-specific structural tree of your repository, launching a dedicated, codebase-aware co-pilot session.

---

## Core Features

| Pillar | Capability | Description |
| :--- | :--- | :--- |
| **Performance** | **Zero-Daemon Footprint** | Consumes 0% idle CPU and 0% idle RAM with absolutely no background processes or active polling threads. |
| | **Rarity-Weighted Search** | Upgraded log-scale TF-IDF/BM25 sparse indexing weights rare terms (like `hyprctl`) over noise to eliminate conflicts. |
| **Resiliency** | **Cascading Fallback Chain** | Seamlessly cascades from Gemini $\rightarrow$ OpenRouter $\rightarrow$ Custom Cloud down to local servers if an endpoint drops offline. |
| | **OpenRouter Failover** | Sends a prioritized model array payload to automatically route around free-tier model congestion on the server side. |
| **Integration** | **Zero-Bloat Auto-Routing** | Automatically injects your system specs (`mysys.md`) *only* when queries contain system keywords (e.g. `gpu`, `kernel`). |
| | **Voice Query Bridge** | Connects any Wi-Fi tablet or phone over local HTTPS/HTTP to record audio, transcribing natively on the cloud with 0% PC CPU load. |
| | **Dynamic Viewer Pipeline** | Intercepts manual `[TOOL]` calls, automatically piping them to `mdcat` for terminal rendering while translating them to `cat` for AI context tasks. |
| **Portability** | **Zero-Config Bootstrap** | Silent local diagnostics query your CPU, GPU, and window manager on first-run, auto-generating your system profile. |
| | **Auditable Codebase** | Designed with full transparency in under 400 lines of highly clean, standard-library Python code. |

---

## TUI Carousel Controls

* **`Up` / `Down` Arrow Keys:** Cycle through available ranked selections
* **`Enter`:** Execute the highlighted command (or initialize a workspace if the selection is a directory path)
* **`Esc` / `Ctrl+C` / `Any Key`:** Cancel menu (features an anti-spam buffer flush to prevent command line leakage)

---

## Command Reference

* `ai`: Launch an interactive, multi-turn conversation session. Press `Ctrl+C` or type `exit`/`quit` to quit.
* `ai init <path>`: Index a directory and launch an interactive workspace agent primed with your codebase structure.
* `ai <query>`: Instantly answer a single question and return directly to your Bash prompt.
* `voice`: Launch your high-speed, local-network tablet voice bridge on port 9999.

---

## The Brain: Configuration (`ai-context.md`)

Add your shortcuts, dynamic tool integrations, and project workspaces to `~/.config/local-ai/local-ai-agent/ai-context.md`. The search index automatically compiles in under 2ms on your next execution.

```markdown
## 1. Workspace Initializers & Bridges

# --- OpenCode Direct Terminal Launcher ---
~/.config/local-ai/opencode-bridge/opencode-bridge ---> opencode bridge, ocb

# --- Standard Codebase Workspaces (Dynamic Auto-Init) ---
# (Triggers standard ai init on the directory tree when matched)
~/Projects/qwen-hypr ---> projects qwen, projects

# --- Specialized Codebase Workspaces (Skill-Primed) ---
# (Specialized project initializations primed with the "coder" Skill!)
ai init ~/Projects/quickshell coder ---> projects quickshell, projects


## 4. Static Aliases & Shell Shortcuts

# --- Local-Ai Agent Blueprint Map (CheatSheet) (Optional: leaf, glow) ---
~/.config/local-ai/local-ai-agent/tools/blueprint | mdcat ---> cheatsheet, blueprint, bp, cs, map
~/.config/local-ai/local-ai-agent/tools/blueprint | leaf ---> cheatsheet leaf, blueprint, bp, cs, map
```

---

## Setup & Prerequisites

### 1. Install optional rendering utilities

To render Markdown files (`.md` skills, system profiles, and diagnostic logs) cleanly inside your terminal using your **native terminal theme colors**, it is recommended to install **`mdcat`** (Rust-based Markdown CLI viewer):

```bash
yay mdcat
```

*Note: If `mdcat` is missing from the system, the Python agent automatically falls back to standard `cat` using standard-library path checks, keeping the entire pipeline fully portable.*

### 2. Install the Project Files
```bash
git clone https://github.com/j5onrf/local-ai.git ~/.config/local-ai
```

### 3. Append the Hook to Your `~/.bashrc`
```bash
echo '[ -f "$HOME/.config/local-ai/local-ai-agent/ai-hook.sh" ] && source "$HOME/.config/local-ai/local-ai-agent/ai-hook.sh"' >> ~/.bashrc
source ~/.bashrc
```

*(Optional)* Export your cloud API keys to activate cloud routing and fallback logic:
```bash
export GEMINI_API_KEY="AIzaSyYourGeminiKey"
export OPENROUTER_API_KEY="sk-or-v1-YourOpenRouterKey"
```

---

```text
    ║
  ═ █ ═                                                          ██╗
    ║                                                            ██║
                                                                ███║
               ╔══╗                                           ██╔██║
             ══╝  ╚══                                       ██╔╝ ██║
                                                          ██╔╝   ██║
                                                        █████████████████████████╗
                                                        ╚███████████████████████╔╝   ~ > A H O Y _
                                                    ═══╝╚════╝╚════╝╚════╝╚════╝═══

```

---

</div>

*For detailed system architecture diagrams, custom tool development guidelines, and advanced prompt engineering, refer to the full **[documentation.md](documentation.md)**.*
