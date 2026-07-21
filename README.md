<p align="center">
  <img alt="Local-AI Agent" src="https://github.com/j5onrf/local-ai/blob/main/logo.png" width="800" />
</p>

<h1 align="center">Local-AI Agent <kbd>v0.9.3.21-beta</kbd></h1>

<p align="center">
  <img src="https://img.shields.io/github/last-commit/j5onrf/local-ai?style=for-the-badge&labelColor=1f1f1f&color=8dbdff" alt="Last Commit">
  <img src="https://img.shields.io/badge/language-python-a3be8c?style=for-the-badge&labelColor=1f1f1f" alt="Language">
  <img src="https://img.shields.io/github/repo-size/j5onrf/local-ai?style=for-the-badge&labelColor=1f1f1f&color=d6b4e0" alt="Repo Size">
</p>

<p align="center">
  <code>gpt</code> &nbsp; <code>claude</code> &nbsp; <code>grok</code> &nbsp; <code>gemini</code> &nbsp; <code>openrouter</code> &nbsp; <code>gguf</code>
</p>

---

<h2 align="center">How the Agent Works</h2>

All configurations and custom shortcuts are managed in [`ai-context.md`](ai-context.md). The system is built with minimal context-stuffing, making it highly effective even when using highly quantized, resource-constrained models like `Qwen-3.5-2B` `Gemma4`.

*   **Direct (No Session)**: Sub-millisecond Jaccard matching (`jaccard_search`) instantly routes custom keywords to your local terminal.
*   **Single-Turn Agent (`ai <query>`):** Returns a single response directly to your shell prompt without loading an active conversation.
*   **Multi-Turn Chat (`ai` alone):** Starts a persistent terminal session with multi-turn context tracking.
*   **Workspace Agents (`ai init <path>`):** Indexes your directory into a lightweight codebase graph and boots up a codebase-aware chat.

---

<h2 align="center">CLI Launch Interfaces</h2>

```console
~ ❯ ai
╔═  ❖ Local-AI Agent  ══════════════════════╗
║     model:  Qwen3.6-35B-A3B.gguf          ║
║ directory:  ~                             ║
║     skill:  default                       ║
║  database:  stateless                     ║
╚══════════════════════════ Ctrl+C to exit ═╝
 Startup context: 93 tokens
❯ 
```
```console
~ ❯ sess
[01/03] ❯ [session test] ai init ~/session-test --init
:: ↵ run  Esc: 
╔═  ❖ Local-AI Agent  ═══════════════════════════════════╗
║     model:  Qwen3.6-35B-A3B.gguf                       ║
║ directory:  ~/.config/local-ai/projects/session-test   ║
║     skill:  init code2                                 ║
║  database:  active (0 facts, 21 turns)                 ║
╚═══════════════════════════════════════ Ctrl+C to exit ═╝
 Startup context: 192 tokens

Agent: Workspace loaded. Awaiting instructions.

 [10 tokens | 0.55s | 28.09 t/s]
 [ 930 in | 10 out | cost: $0.00000 | today: $0.0000 | ctx: 11.5% ]
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
  <em>Building semantic codebase maps and queryable relational graphs.</em>
</p>

* [Graphify](https://github.com/Graphify-Labs/graphify)'s codebase mapping and [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)'s relational queries, supercharged with local semantic vector search via [sqlite-vec](https://github.com/asg017/sqlite-vec).

---

<h2 align="center">System Administration & Diagnostics</h2>

<p align="center">
  <em>Inspecting package updates, monitoring system health, and optimizing performance.</em>
</p>

* [log-checker](/tools/agentic/system/log-checker) and [system-health](/tools/agentic/system/system-health) live diagnostics with [aur-audit](/tools/agentic/system/aur-audit), [security-audit](/tools/agentic/system/security-audit), [update-inspector](/tools/agentic/system/update-inspector) zero-trust auditing, [system-optimizer](/tools/agentic/system/system-optimizer) resource adjustments, [ai-status](/tools/agentic/system/ai-status) routing, and [ai-commit](/tools/agentic/system/ai-commit) hooks.

---

<h2 align="center">Core Capabilities</h2>

| Core | Capability | Description |
| :---: | :---: | :--- |
| **Performance** | **Zero-Daemon** | 0% idle CPU/RAM. `Ultra-light` execution. |
| **Intelligence** | **Scalability** | Optimized from `Qwen3.5-2B` up to frontier models. |
| **Resiliency** | **Fallbacks** | Top-Down Cascade: `.env` order: `Provider` → `GGUF`. |
| **Multi-Agent** | **Subagents** | [Vercel's Eve](https://github.com/vercel/eve)-style with [herdr](https://github.com/ogulcancelik/herdr) multiplexing via (`-save`/`-load`). |
| **Safety** | **Zero-Trust Guardrails** | Intercepts out-of-bounds commands and edits for manual approval. |
| **Safety** | **Type-Safe Validation** | Enforces [Pydantic AI](https://github.com/pydantic/pydantic-ai)'s schema concepts natively. |
| **Safety** | **Syntactic Guardrails** | [OpenAI Agents](https://github.com/openai/openai-agents-python)-style self-correcting `.py`/`.json` writes. |
| **Integration** | **Dynamic Context** | On-demand compilation of system specs and file contents. |
| **Optimization** | **Token-Slasher** | Custom [`tool`](https://github.com/j5onrf/fetch/tree/main/tools) and [`skill`](https://github.com/j5onrf/fetch/tree/main/skills) integration built for minimal token use. |
| **Interface** | **Conversational TUI** | Rich, multi-turn chat sessions directly in the terminal. |
| **Auditability** | **Zero-Dependency** | Under 700 lines of modular, standard-library Python. |

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

* Run **`model select`** directly from your terminal to launch the interactive **[Cloud Connection](https://github.com/j5onrf/local-ai/blob/main/modules/Readme.md)** TUI.

---

<h2 align="center">Interactive TUI</h2>

<p align="center">
  <em>A full-screen, mouse-clickable, multi-theme terminal workspace modeled after grok-build.</em>
</p>

* Type **`/tui`** inside any active chat session to transition into the full-screen **[Textual](https://github.com/j5onrf/local-ai/blob/main/modules/Readme.md)** TUI.

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
| **`/sync`** *(or `/re`)* | Sync Codebase index real-time reloading of disk changes. |
| **`/f`** / **`/t`** / **`/b`** / **`/a`** | Trigger prompt-generating subroutines: Follow-up, Thinking, Brainstorm, or All. |

### 3. Modular Toggle & Diagnostic Switches
*Typed inside an active chat session to adjust settings.*

| Command | Description |
| :--- | :--- |
| **`/tui`** | **Toggle** full-screen Textual TUI mode ON/OFF (Suspends standard chat). |
| **`/clear`** / **`/reset`** | **Reset** Session context, local chat history, and the SQLite TPM table. |
| **`/spell`** / **`/sp`** | **Toggle** the context-aware grammar & spellchecker ON/OFF. |
| **`/g`** | **Toggle** workspace confirmation gates ON/OFF (autonomous editing mode). |
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
# 1. Install core system dependencies (requests reduces latency | rich formats)
sudo pacman -S python-rich python-requests  # Arch Linux
# Debian/Ubuntu: sudo apt install python3-rich python3-requests
# macOS/Other:   pip install rich requests

# 2. (Optional) Install extensions (sqlite-vec for code search | textual for /tui)
# Arch Linux:    yay -S python-sqlite-vec && sudo pacman -S python-textual
# Debian/Ubuntu: pip install sqlite-vec --break-system-packages && sudo apt install python3-textual
# macOS/Other:   pip install sqlite-vec textual

# 3. Clone repository & register shell environment hook
git clone https://github.com/j5onrf/local-ai.git ~/.config/local-ai && \
echo '[ -f "$HOME/.config/local-ai/ai-hook.sh" ] && source "$HOME/.config/local-ai/ai-hook.sh"' >> ~/.bashrc && \
source ~/.bashrc

# 4. Create your private configuration file
nano ~/.config/local-ai/.env
```

#### Configuration Example (`~/.config/local-ai/.env`):

```env
# Cascade Fallback (Evaluated Top-Down)
GEMINI_API_KEY="AIzaSyYourGeminiKeyHere"
GEMINI_MODEL="gemini-3.1-flash-lite"

OPENROUTER_API_KEY="sk-or-v1-YourOpenRouterKey"
OPENROUTER_MODEL="openrouter/free"

OPENAI_API_KEY="your-openai-api-key"
OPENAI_MODEL="gpt-5.6"

CLAUDE_API_KEY="your-claude-api-key"
CLAUDE_MODEL="claude-fable-5"

XAI_API_KEY="xai-your-grok-key"
XAI_MODEL="grok-4.5"

AI_MAX_TOKENS="8192" # Offline Local Context Limit
```

---

<h2 align="center">Roadmap to v1.0.0</h2>

<p align="center">
  <em>The final performance and security passes before the official stable release.</em>
</p>

- [ ] **Dynamic Stress-Testing:** Conduct continuous context-window pressure tests across standard (GGUF) and deep reasoning backends.
- [ ] **Optimization Audits:** Run latency profiling and memory alignment passes on connection pooling and stream processing modules.
- [ ] **Security Validation:** Implement automated file boundary testing to verify directory containment and authorization overrides.
- [ ] **Final Code Optimizations:** Use strongest frontier coding model with exclusive finishing coding-skill.md to run a final pass and optimize final production ready product.
- [ ] **Stable Tag Deployment:** Publish official **`v1.0.0`** production-stable release!

---

## Credits & License

*   **License**: Licensed under the permissive [MIT License](LICENSE).
*   **Contributions**: Special thanks to [suyadnya](https://github.com/wibawasuyadnya) for the `.env` configuration architecture, macOS compatibility investigations, and high-velocity alias designs. Contributions are always welcome.


