<p align="center">
  <img alt="Local-AI Agent" src="https://github.com/user-attachments/assets/56fe2b60-0cbe-4f51-bc27-a35516f1088f" width="800" />
</p>

<h1 align="center">Local-AI Agent <kbd>v0.8.8.8-beta</kbd></h1>

<p align="center">
  <img src="https://img.shields.io/github/last-commit/j5onrf/local-ai?style=for-the-badge&labelColor=1f1f1f&color=8dbdff" alt="Last Commit">
  <img src="https://img.shields.io/badge/language-python-a3be8c?style=for-the-badge&labelColor=1f1f1f" alt="Language">
  <img src="https://img.shields.io/github/repo-size/j5onrf/local-ai?style=for-the-badge&labelColor=1f1f1f&color=d6b4e0" alt="Repo Size">
</p>

<p align="center">
  <code>Laguna-M.1</code> &nbsp; <code>Qwen3-Coder</code> &nbsp; <code>Gemini-3.1-Flash-Lite</code>
</p>

---

<h2 align="center">How the Agent Works</h2>

All configurations are managed through your master blueprint: `ai-context.md`.

> **Routing Logic:** The agent automatically determines the optimal execution path based on your input pattern, ensuring zero wasted tokens.

* **No Session (Direct selections):** Uses a fast Jaccard Similarity engine (`jaccard_search`) with prefix-matching to instantly route custom commands and shortcuts to your local terminal.
* **Single-Turn Agent (`ai <query>`):** Answers a single question and returns you to Bash, executing explicitly mapped diagnostic `tools` and `skills` only when requested.
* **Workspace Agents (`ai init <path>`):** Compiles a path-specific structural tree of your repository, launching a dedicated, codebase-aware agent session primed with your chosen skill file.

---

<h2 align="center">Core Pillars & Capabilities</h2>

| Pillar | Capability | Description |
| :---: | :---: | :--- |
| **Performance** | **Zero-Daemon** | 0% idle CPU/RAM. `Ultra-lite` execution. |
| **Search Engine** | **Jaccard Similarity** | Sub-millisecond keyword and partial-word matching. |
| **Resiliency** | **Fallbacks** | Automatically cascades: `Gemini` → `OpenRouter` → `Local`. |
| **Safety** | **Zero-Trust Guardrails** | Intercepts destructive commands before shell execution. |
| **Integration** | **Dynamic Context** | On-demand compilation of system specs and tool outputs. |
| **Optimization** | **Token-Slasher** | Custom `tool` and `skill` integration built for minimal token use. |
| **Interface** | **Conversational TUI** | Rich, multi-turn chat sessions directly in the terminal. |
| **Auditability** | **Zero-Dependency** | Under 350 lines of standard-library Python. |

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

<h2 align="center">Command Reference</h2>

| Command | Description |
| --- | --- |
| `ai` | Launch interactive, multi-turn chat session. |
| `ai <query>` | Instant answer; returns directly to Bash prompt. |
| `ai init <path>` | Index directory & launch codebase-aware agent. |
| `hs` | On-demand keyword search of workspace history. |
| `hist` | View styled workspace history log (`history.md`). |

| Command | Description |
| --- | --- |
| `/s <query>` / `/skill` | Search and load dynamic department skills on-the-fly. |
| `-save <tag>` | Snapshot current conversation directly to SQLite in RAM. |
| `-timeline` / `-load` | Rollback active memory to a past SQLite checkpoint. |
| `/f` `/t` `/b` `/a` | Trigger Follow-up, Thinking, Brainstorm, or all. |

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
# 1. Optional: Install mdcat for native terminal Markdown rendering
yay mdcat

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

