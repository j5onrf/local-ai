# Local-AI Agent <kbd>v0.8.6.1</kbd>

<div align="center">
  <img alt="Local-AI Agent" src="https://github.com/user-attachments/assets/56fe2b60-0cbe-4f51-bc27-a35516f1088f" width="800" />

  <p>
    <code>Laguna-M.1</code>  <code>Qwen3-Coder</code>  <code>Gemini-3.1-Flash-Lite</code>
  </p>
</div>

---

## How the Agent Works

All configurations are managed through your master blueprint: `ai-context.md`.

> **Routing Logic:** The agent automatically determines the optimal execution path based on your input pattern, ensuring zero wasted tokens.

* **No Session (Direct selections):** Uses a fast Jaccard Similarity engine (`jaccard_search`) with prefix-matching to instantly route custom commands and shortcuts to your local terminal.
* **Single-Turn Agent (`ai <query>`):** Answers a single question and returns you to Bash, executing explicitly mapped diagnostic tools and skills only when requested.
* **Multi-Turn Chat (`ai` alone):** Initiates an interactive, persistent conversation with local state preservation and multi-turn context memory.
* **Workspace Agents (`ai init <path>`):** Compiles a path-specific structural tree of your repository, launching a dedicated, codebase-aware agent session primed with your chosen skill file.

---

| Pillar | Capability | Description |
| --- | --- | --- |
| **Performance** | **Zero-Daemon** | 0% idle CPU/RAM. Ultra-lite execution. |
| **Search Engine** | **Jaccard Similarity** | Sub-millisecond keyword and partial-word matching. |
| **Resiliency** | **Fallbacks** | Automatically cascades: Gemini $\rightarrow$ OpenRouter $\rightarrow$ Local. |
| **Safety** | **Zero-Trust Guardrails** | Intercepts destructive commands before shell execution. |
| **Integration** | **Dynamic Context** | On-demand compilation of system specs and tool outputs. |
| **Optimization** | **Token-Slasher** | Custom tool and skill integration built for minimal token use. |
| **Interface** | **Conversational TUI** | Rich, multi-turn chat sessions directly in the terminal. |
| **Auditability** | **Zero-Dependency** | Under 300 lines of standard-library Python. |

---

## TUI Carousel Controls

* **`Up` / `Down` Arrow Keys:** Cycle through available ranked selections.
* **`Enter`:** Execute the highlighted command (or initialize a workspace if the selection is a directory path).
* **`Esc` / `Ctrl+C` / `Any Key`:** Cancel menu (features an anti-spam buffer flush to prevent command line leakage).

```text
~ ❯ hs
[01/04] ❯ [hyprstate work] ~/.config/local-ai/local-ai-agent/tools/subsec/hyprstate/work
:: ↵ run  any skip: 
```

---

## Command Reference

| Command | Description |
| --- | --- |
| `ai` | Launch interactive, multi-turn conversation session. |
| `ai init <path>` | Index directory & launch codebase-aware agent. |
| `ai <query>` | Instant answer; returns directly to Bash prompt. |
| `voice` | Launch local-network tablet voice bridge (Port 9999). |
| `/f` `f` | Launch Follow-ups, in multi-turn chat session. |

---

## The Brain: Configuration (`ai-context.md`)

Add your shortcuts, commands, and workspaces to `ai-context.md`.

```markdown
# --- Specialized Codebase Workspaces (Skill-Primed) ---
ai init ~/Projects/quickshell --coder ---> projects quickshell, projects

# --- System Optimization (Improve System Performance) ---
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/system/system-optimize --leaf ---> system optimize, sysop
```

---

## Setup & Prerequisites

### 1. Optional: Terminal Markdown Rendering

For the best experience, install `mdcat` to render Markdown files with your native terminal colors:

```bash
yay mdcat
```

### 2. Install Project

```bash
git clone https://github.com/j5onrf/local-ai.git ~/.config/local-ai
```

### 3. Bash Hook

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
  ═ █ ═                                                  ██╗
    ║                                                    ██║
                                                        ███║
               ╔══╗                                   ██╔██║
             ══╝  ╚══                               ██╔╝ ██║
                                                  ██╔╝   ██║
                                                █████████████████████████╗
                                                ╚███████████████████████╔╝   ~ > A H O Y _
                                            ═══╝╚════╝╚════╝╚════╝╚════╝═══
```

