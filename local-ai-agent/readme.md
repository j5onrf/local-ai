# Local-AI Agent <kbd>v0.8.4.1</kbd>

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

* **No Session (Direct selections):** Typing custom commands or shortcuts prompts a local, rarity-weighted sparse search matrix to select options instantly, routing them directly to your local terminal or pager.
* **Single-Turn Agent (`ai <query>`):** Answers a single question and returns you to Bash, executing explicitly mapped diagnostic tools and skills only when requested.
* **Multi-Turn Chat (`ai` alone):** Initiates an interactive, persistent conversation with local state preservation and multi-turn context memory.
* **Workspace Agents (`ai init <path>`):** Compiles a path-specific structural tree of your repository, launching a dedicated, codebase-aware agent session primed with your chosen skill file.

---

## Core Features

| Pillar | Capability | Description |
| --- | --- | --- |
| **Performance** | **Zero-Daemon** | 0% idle CPU/RAM usage. No background polling threads. |
| **Resiliency** | **Cascading Fallback** | Automatically cascades: Gemini $\rightarrow$ OpenRouter $\rightarrow$ Local. |
| **Integration** | **Deterministic Context** | Uses `mysys.md` & custom tools only via defined triggers. |
| **Portability** | **Multi-Depth Skills** | Scans skills directories up to 3 levels deep recursively. |
| **Auditable** | **Clean Codebase** | Under 400 lines of standard-library Python. |

---

## TUI Carousel Controls

* **`Up` / `Down` Arrow Keys:** Cycle through available ranked selections.
* **`Enter`:** Execute the highlighted command (or initialize a workspace if the selection is a directory path).
* **`Esc` / `Ctrl+C` / `Any Key`:** Cancel menu (features an anti-spam buffer flush to prevent command line leakage).

---

## Command Reference

| Command | Description |
| --- | --- |
| `ai` | Launch interactive, multi-turn conversation session. |
| `ai init <path>` | Index directory & launch codebase-aware agent. |
| `ai <query>` | Instant answer; returns directly to Bash prompt. |
| `voice` | Launch local-network tablet voice bridge (Port 9999). |

---

## The Brain: Configuration (`ai-context.md`)

Add your shortcuts and workspaces to `ai-context.md`.

```markdown
# --- Standard Codebase Workspaces ---
~/Projects/qwen-hypr ---> projects qwen, projects

# --- Blueprint Map (CheatSheet) ---
~/.config/local-ai/local-ai-agent/tools/blueprint --leaf ---> cheatsheet, blueprint, bp

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



