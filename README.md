<p align="center">
  <img alt="Local-AI Agent" src="https://github.com/user-attachments/assets/56fe2b60-0cbe-4f51-bc27-a35516f1088f" width="800" />
</p>

<h1 align="center">Local-AI Agent <kbd>v0.8.9.22-beta</kbd></h1>

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

All configurations and custom shortcuts are managed in [`ai-context.md`](ai-context.md).

*   **Direct (No Session)**: Sub-millisecond Jaccard matching (`jaccard_search`) instantly routes custom keywords to your local terminal.
*   **Single-Turn Agent (`ai <query>`):** Returns a single response directly to your shell prompt without loading an active conversation.
*   **Multi-Turn Chat (`ai` alone):** Starts a persistent terminal session with multi-turn context tracking.
*   **Workspace Agents (`ai init <path>`):** Indexes your directory into a lightweight codebase graph and boots up a codebase-aware chat.

---

<h2 align="center">CLI Launch Interface</h2>

```console
╭──────────────────────────────────────────────╮
│  >_ Local-AI Agent                           │
│                                              │
│  model:     local-model                      │
│  directory: ...-ai/projects/session-test     │
│  skill:     init                             │
│  database:  active (3 facts, 109 turns)      │
╰──────────────────────────────────────────────╯
[sys] Startup context: 104 tokens | Ctrl+C to exit.

Agent: Workspace loaded. Awaiting instructions.
❯ 
```

---

<h2 align="center">Temporal Personality Memory (TPM)</h2>

<p align="center">
  <em>Evolving with your workspace, learning your habits, and standardizing your identity.</em>
</p>

* [Weaviate Engram](https://github.com/weaviate/engram-python-sdk)'s active reconciliation concepts with [Noema](https://github.com/Fail-Safe/Noema)'s local Markdown file system.

---

<h2 align="center">Codebase Graph Mapper & Relational Index</h2>

<p align="center">
  <em>Building flat shorthand maps and queryable call graphs.</em>
</p>

* [Graphify](https://github.com/Graphify-Labs/graphify)'s codebase mapping with [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)'s relationship queries.

---

<h2 align="center">System Administration & Diagnostics</h2>

<p align="center">
  <em>Inspecting package updates, monitoring system health, and optimizing performance...</em>
</p>

* [log-checker](/tools/agentic/system/log-checker) and [system-health](/tools/agentic/system/system-health) live diagnostics with [aur-audit](/tools/agentic/system/aur-audit), [security-audit](/tools/agentic/system/security-audit), [update-inspector](/tools/agentic/system/update-inspector) zero-trust auditing, [system-optimizer](/tools/agentic/system/system-optimizer) resource adjustments, [ai-status](/tools/agentic/system/ai-status) routing, and [ai-commit](/tools/agentic/system/ai-commit) hooks.

---

<h2 align="center">Core Capabilities</h2>

| Core | Capability | Description |
| :---: | :---: | :--- |
| **Performance** | **Zero-Daemon** | 0% idle CPU/RAM. `Ultra-light` execution. |
| **Intelligence** | **Scalability** | Optimized from `Qwen3.5 2B` up to frontier models. |
| **Resiliency** | **Fallbacks** | Automatically cascades: `Gemini` → `OpenRouter` → `Local`. |
| **Safety** | **Zero-Trust Guardrails** | Intercepts destructive commands before shell execution. |
| **Integration** | **Dynamic Context** | On-demand compilation of system specs and file contents. |
| **Optimization** | **Token-Slasher** | Custom [`tool`](https://github.com/j5onrf/local-ai/tree/main/tools) and [`skill`](https://github.com/j5onrf/local-ai/tree/main/skills) integration built for minimal token use. |
| **Interface** | **Conversational TUI** | Rich, multi-turn chat sessions directly in the terminal. |
| **Auditability** | **Zero-Dependency** | Under 500 lines of modular, standard-library Python. |

---

<h2 align="center">TUI Carousel & Input Controls</h2>

* **`Up` / `Down` Arrow Keys:** Cycle through available ranked selections.
* **`Enter`:** Execute the highlighted command (or initialize a [workspace](https://github.com/j5onrf/local-ai/tree/main/projects) if the selection is a directory path).
* **`Esc` / `Right Arrow` / `Ctrl+C`:** Cancel/Skip the active menu, memory-recall, or tool authorization prompt cleanly.

```console
~ ❯ weather
[01/02] ❯ [weather full] curl -s wttr.in | cat
:: ↵ run  Esc:
```

---

<h2 align="center">Model Select TUI</h2>

<p align="center">
  <em>Manage your active cloud endpoints, inspect live API rankings, and toggle keys.</em>
</p>

* Run **`model select`** directly from your terminal to launch the interactive **[Cloud Connection](https://github.com/j5onrf/local-ai/tree/main/modules)**

---

<h2 align="center">Command Reference</h2>

### 1. Global Shell Commands
*Executed directly from your terminal prompt.*

| Command | Description |
| :--- | :--- |
| **`ai`** | Launch an interactive, multi-turn chat session. |
| **`ai <query>`** | Get an instant, one-shot answer, straight back to your shell prompt. |
| **`ai init <path>`** | Launch (or create) a codebase-aware workspace agent. |
| **`hs` / `hist`** | Interactively search or view active workspace `history.md`. |

### 2. Active Session Commands
*Typed directly inside an active chat session.*

| Command | Description |
| :--- | :--- |
| **`/skill <query>`** *(or `/s`)* | Search and load dynamic specialist skills. |
| **`view file <path>`** *(or `read`)* | Dynamically read local files directly into your model context. |
| **`-save <tag>` / `-load`** | Save active states or rollback/clone snapshots (with Global Handoff). |
| **`/f`** / **`/t`** / **`/b`** / **`/a`** | Trigger prompt-generating subroutines: Follow-up, Thinking, Brainstorm, or All. |

### 3. Modular Toggle & Diagnostic Switches
*Typed inside an active chat session to adjust settings.*

| Command | Description |
| :--- | :--- |
| **`/clear`** / **`/reset`** | **Reset** Session context, local chat history, and the SQLite TPM table. |
| **`/d`** / **`/e`** | **Disable** / **Enable** the context-aware grammar & spellchecker. |
| **`/m`** | **Toggle** long-term memory and TPM reconciliation ON/OFF. |
| **`/r`** / **`/r <tokens>`** | **Toggle** reasoning ON/OFF. Supports custom limits (default: 500). |
| **`/stats` / `/tok`** | **Diagnostics**: Toggle real-time speed metrics or view live token usage. |

---

<h2 align="center">Agent Blueprint</h2>

Add your shortcuts, commands, and workspaces to [`ai-context.md`](https://github.com/j5onrf/local-ai/blob/main/ai-context.md).

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
# 1. Optional: Install terminal rendering utilities
# (mdcat enables beautiful terminal markdown formatting)
yay -S mdcat

# 2. Install the required requests dependency
# Arch: sudo pacman -S python-requests
# Debian/Ubuntu: sudo apt install python3-requests
# macOS / Other: pip install requests
sudo pacman -S python-requests

# 3. Clone the repository locally
git clone https://github.com/j5onrf/local-ai.git ~/.config/local-ai

# 4. Add the environment hook into Bash & reload your profile
echo '[ -f "$HOME/.config/local-ai/ai-hook.sh" ] && source "$HOME/.config/local-ai/ai-hook.sh"' >> ~/.bashrc
source ~/.bashrc

# 5. Create your private configuration file (No global exports needed!)
# Fill in only what you use; the rest defaults safely.
# The agent reads this dynamically on every run with zero terminal restarts.
nano ~/.config/local-ai/.env
```

#### Configuration Example (`.env`):
```env
# ~/.config/local-ai/.env
# use "ai status" and "model select"

# Claude Subscription API Configurations
CLAUDE_API_KEY="your-claude-api-key-here"
CLAUDE_MODEL="claude-fable-5"

# OpenAI Subscription API Configurations
OPENAI_API_KEY="your-openai-api-key-here"
OPENAI_MODEL="gpt-5.5"

# Google Gemini API Configurations
GEMINI_API_KEY="AIzaSyYourFullGeminiApiKeyHere"
GEMINI_MODEL="gemini-3.1-flash-lite"

# OpenRouter API Configurations
OPENROUTER_API_KEY="sk-or-v1-YourFullOpenRouterKeyHere"
OPENROUTER_MODEL="openrouter/free"

# Context Limits
AI_MAX_TOKENS=8192
```

---

## Credits & License

*   **License**: Licensed under the permissive [MIT License](LICENSE).
*   **Contributions**: Special thanks to [suyadnya](https://github.com/wibawasuyadnya) for the `.env` configuration architecture, macOS compatibility investigations, and high-velocity alias designs. Contributions are always welcome.

