<p align="center">
  <img alt="Local-AI Agent" src="https://github.com/user-attachments/assets/56fe2b60-0cbe-4f51-bc27-a35516f1088f" width="800" />
</p>

<h1 align="center">Local-AI Agent <kbd>v0.8.9.4-beta</kbd></h1>

<p align="center">
  <img src="https://img.shields.io/github/last-commit/j5onrf/local-ai?style=for-the-badge&labelColor=1f1f1f&color=8dbdff" alt="Last Commit">
  <img src="https://img.shields.io/badge/language-python-a3be8c?style=for-the-badge&labelColor=1f1f1f" alt="Language">
  <img src="https://img.shields.io/github/repo-size/j5onrf/local-ai?style=for-the-badge&labelColor=1f1f1f&color=d6b4e0" alt="Repo Size">
</p>

<p align="center">
  <code>Gemini-3.1-flash-lite</code> &nbsp; <code>Openrouter/free</code> &nbsp; <code>Local-Ai Model</code>
</p>

---

<h2 align="center">How the Agent Works</h2>

All configurations are managed through your master blueprint: `ai-context.md`.

> **Routing Logic:** The agent automatically determines the optimal execution path based on your input pattern, ensuring zero wasted tokens.

* **No Session (Direct selections):** Uses a fast Jaccard Similarity engine (`jaccard_search`) with prefix-matching to instantly route custom commands and shortcuts to your local terminal.
* **Single-Turn Agent (`ai <query>`):** Answers a single question and returns you to Bash, executing explicitly mapped diagnostic `tools` and `skills` only when requested.
* **Multi-Turn Chat (`ai` alone):** Initiates an interactive, persistent conversation with local state preservation and multi-turn context memory.
* **Workspace Agents (`ai init <path>`):** Compiles a path-specific structural tree directly inside your active workspace using `index-map`, launching a dedicated, codebase-aware agent session primed with your chosen skill file.

---

<h2 align="center">Core Pillars & Capabilities</h2>

| Pillar | Capability | Description |
| :---: | :---: | :--- |
| **Performance** | **Zero-Daemon** | 0% idle CPU/RAM. `Ultra-light` execution. |
| **Search Engine** | **Jaccard Similarity** | Sub-millisecond keyword and partial-word matching. |
| **Resiliency** | **Fallbacks** | Automatically cascades: `Gemini` → `OpenRouter` → `Local`. |
| **Safety** | **Zero-Trust Guardrails** | Intercepts destructive commands before shell execution. |
| **Integration** | **Dynamic Context** | On-demand compilation of system specs and file contents. |
| **Optimization** | **Token-Slasher** | Custom `tool` and `skill` integration built for minimal token use. |
| **Interface** | **Conversational TUI** | Rich, multi-turn chat sessions directly in the terminal. |
| **Auditability** | **Zero-Dependency** | Under 400 lines of standard-library Python. |

---

<h2 align="center">TUI Carousel Controls</h2>

* **`Up` / `Down` Arrow Keys:** Cycle through available ranked selections.
* **`Enter`:** Execute the highlighted command (or initialize a workspace if the selection is a directory path).
* **`Esc` / `Ctrl+C` / `Any Key`:** Cancel the menu.

```text
~ ❯ weather
[01/02] ❯ [weather full] curl -s wttr.in | cat
:: ↵ run  Esc:
```

---

<h2 align="center">Command Reference</h2>

### 1. Global Shell Commands
*Executed directly from your terminal prompt.*

| Command | Description |
| :--- | :--- |
| **`ai`** | Launch an interactive, multi-turn chat session. |
| **`ai <query>`** | Get an instant, stateless answer; returns directly to your Bash prompt. |
| **`ai init <path>`** | Index a directory & launch a codebase-aware, stateful agent session. |
| **`hs`** | Perform an on-demand keyword search of your active workspace history. |
| **`hist`** | View your workspace history log (`history.md`). |

### 2. Active Session Commands
*Typed directly inside an active chat session.*

| Command | Description |
| :--- | :--- |
| **`/skill <query>`** *(or `/s`)* | Search and load dynamic specialist skills on-the-fly. |
| **`view file <path>`** *(or `read`)* | Dynamically read local files directly into your model context. |
| **`-save <tag>`** | Snapshot the current conversation state to your local SQLite database. |
| **`-load`** *(or `-timeline`)* | Rollback active history to a past SQLite checkpoint. |
| **`/f`** / **`/t`** / **`/b`** / **`/a`** | Trigger prompt-generating subroutines: Follow-up, Thinking, Brainstorm, or All. |

### 3. Modular Toggle & Diagnostic Switches
*Typed inside an active chat session to adjust settings on-the-fly.*

| Command | Description |
| :--- | :--- |
| **`/clear`** / **`/reset`** | **Reset** Google session context & clear local. |
| **`/d`** / **`/e`** | **Disable** / **Enable** the offline spellcheck engine. |
| **`/m`** | **Toggle** long-term conversation memory recall on or off. |
| **`/tok`** | **View** your live token usage capacity and visual progress bar. |

---

<h2 align="center">Agent Blueprint</h2>

Add your shortcuts, commands, and workspaces to `ai-context.md`.

```markdown
# --- Weather & Live Networking ---
[TOOL] curl -s wttr.in --cat ---> weather full, wttr, weather
[TOOL] curl -s "wttr.in/?format=3" --cat ---> weather simple, wttr, weather

# --- Local-Ai Agent Blueprint (CheatSheet) ---
~/.config/local-ai/tools/blueprint --leaf ---> cheatsheet, blueprint, bp, cs
```

---

<h2 align="center">Setup & Prerequisites</h2>

```bash
# 1. Optional: Install terminal rendering and dictionary utilities
# (words enables offline spellcheck; mdcat enables terminal markdown rendering)
yay -S mdcat words

# 2. Clone the repository locally
git clone https://github.com/j5onrf/local-ai.git ~/.config/local-ai

# 3. Inject the environment hook into Bash & reload your profile
AI_SRC='$HOME/.config/local-ai/ai-hook.sh'
printf '[ -f "%s" ] && source "%s"\n' "$AI_SRC" "$AI_SRC" >> ~/.bashrc
source ~/.bashrc

# 4. Optional: Export cloud API keys to enable remote fallback routing
export GEMINI_API_KEY="AIzaSyYourFullGeminiApiKeyHere"
export CLOUD_MODEL="gemini-3.1-flash-lite"
export OPENROUTER_API_KEY="sk-or-v1-YourFullOpenRouterKeyHere"
export OPENROUTER_MODEL="openrouter/free"
```



