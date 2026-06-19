<p align="center">
  <img alt="Local-AI Agent" src="https://github.com/user-attachments/assets/56fe2b60-0cbe-4f51-bc27-a35516f1088f" width="800" />
</p>

<h1 align="center">Local-AI Agent <kbd>v0.8.6.5</kbd></h1>

<p align="center">
  <code>Laguna-M.1</code> &nbsp; <code>Qwen3-Coder</code> &nbsp; <code>Gemini-3.1-Flash-Lite</code>
</p>

---

<h2 align="center">How the Agent Works</h2>

All configurations are managed through your master blueprint: `ai-context.md`.

> **Routing Logic:** The agent automatically determines the optimal execution path based on your input pattern, ensuring zero wasted tokens.

* **No Session (Direct selections):** Uses a fast Jaccard Similarity engine (`jaccard_search`) with prefix-matching to instantly route custom commands and shortcuts to your local terminal.
* **Single-Turn Agent (`ai <query>`):** Answers a single question and returns you to Bash, executing explicitly mapped diagnostic tools and skills only when requested.
* **Multi-Turn Chat (`ai` alone):** Initiates an interactive, persistent conversation with local state preservation and multi-turn context memory.
* **Workspace Agents (`ai init <path>`):** Compiles a path-specific structural tree of your repository, launching a dedicated, codebase-aware agent session primed with your chosen skill file.

---

<h2 align="center">Core Pillars & Capabilities</h2>

| Pillar | Capability | Description |
| :---: | :---: | :--- |
| **Performance** | **Zero-Daemon** | 0% idle CPU/RAM. Ultra-lite execution. |
| **Search Engine** | **Jaccard Similarity** | Sub-millisecond keyword and partial-word matching. |
| **Resiliency** | **Fallbacks** | Automatically cascades: Gemini → OpenRouter → Local. |
| **Safety** | **Zero-Trust Guardrails** | Intercepts destructive commands before shell execution. |
| **Integration** | **Dynamic Context** | On-demand compilation of system specs and tool outputs. |
| **Optimization** | **Token-Slasher** | Custom tool and skill integration built for minimal token use. |
| **Interface** | **Conversational TUI** | Rich, multi-turn chat sessions directly in the terminal. |
| **Auditability** | **Zero-Dependency** | Under 300 lines of standard-library Python. |

---

<h2 align="center">TUI Carousel Controls</h2>

* **`Up` / `Down` Arrow Keys:** Cycle through available ranked selections.
* **`Enter`:** Execute the highlighted command (or initialize a workspace if the selection is a directory path).
* **`Esc` / `Ctrl+C` / `Any Key`:** Cancel menu (features an anti-spam buffer flush to prevent command line leakage).

```text
~ ❯ weather
[01/02] ❯ [weather full] curl -s wttr.in | cat
:: ↵ run  any skip: 

```

---

<h2 align="center">Command Reference</h2>

| Command | Description |
| --- | --- |
| `ai` | Launch interactive, multi-turn conversation session. |
| `ai init <path>` | Index directory & launch codebase-aware agent. |
| `ai <query>` | Instant answer; returns directly to Bash prompt. |
| `voice` | Launch local-network tablet voice bridge (Port 9999). |
| `f` `t` `b` `a` | Trigger Follow-up, Thinking, Brainstorm, or all. |

---

Add your shortcuts, commands, and workspaces to `ai-context.md`.

```markdown
# --- Weather & Live Networking ---
[TOOL] curl -s wttr.in --cat ---> weather full, wttr, weather
[TOOL] curl -s "wttr.in/?format=3" --cat ---> weather simple, wttr, weather

# --- Local-Ai Agent Blueprint (CheatSheet) ---
~/.config/local-ai/local-ai-agent/tools/blueprint --leaf ---> cheatsheet, blueprint, bp, cs
```

---

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
# Primary: Google Gemini Cloud API Configuration
export GEMINI_API_KEY="AIzaSyYourFullGeminiApiKeyHere"
export CLOUD_MODEL="gemini-3.1-flash-lite"

# Fallback: OpenRouter Configuration
export OPENROUTER_API_KEY="sk-or-v1-YourFullOpenRouterKeyHere"
export OPENROUTER_MODEL="openrouter/free"


```



