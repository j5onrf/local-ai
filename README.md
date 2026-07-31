<p align="center">
  <img alt="Local-AI Agent Logo" src="logo.png" width="800" />
</p>

<h1 align="center">Local-AI Agent <kbd>v0.9.7.3-beta</kbd></h1>

<p align="center">
  <a href="https://github.com/j5onrf/local-ai"><img src="https://shieldcn.dev/github/stars/j5onrf/local-ai.svg?color=emerald&variant=outline" alt="GitHub Stars"></a>
  <a href="https://github.com/j5onrf/local-ai"><img src="https://shieldcn.dev/badge/language-python.svg?color=emerald&variant=outline" alt="Language"></a>
  <a href="https://github.com/j5onrf/local-ai"><img src="https://shieldcn.dev/github/last-commit/j5onrf/local-ai.svg?color=emerald&variant=outline" alt="Last Commit"></a>
  <a href="https://github.com/j5onrf/local-ai/blob/main/LICENSE"><img src="https://shieldcn.dev/badge/license-MIT.svg?color=emerald&variant=outline" alt="License"></a>
  <a href="https://github.com/j5onrf/local-ai"><img src="https://shieldcn.dev/views/repo/j5onrf/local-ai.svg?color=emerald&variant=outline" alt="Views"></a>
</p>

<p align="center">
  <code>gpt</code> &nbsp; <code>claude</code> &nbsp; <code>grok</code> &nbsp; <code>gemini</code> &nbsp; <code>openrouter</code> &nbsp; <code>gguf</code>
</p>

---

## Overview & Execution Modes

Built with zero context-stuffing for extreme efficiency on quantized local engines (`Qwen-3.5-2B+`, `Gemma-4-E2B+`) and frontier cloud provider cascades.

- **Direct Shell Jaccard (`<shortcut>`):** Sub-millisecond keyword routing to local shell scripts via [`ai-context.md`](ai-context.md).
- **Single-Turn Query (`ai <query>`):** Instant response piped straight back to your active shell prompt.
- **Multi-Turn Chat (`ai`):** Persistent interactive terminal session with memory context.
- **Workspace Agent (`ai init <path>`):** Full codebase graph indexing, path-healing file editing, and sub-agent concurrency.

---

## Key Systems & Integrations

| Feature System | Foundation & Architectural Roots | Interface Command / Link |
| :--- | :--- | :--- |
| **Temporal Personality Memory (TPM)** | Reconciles personal identity & workspace habits using [Weaviate Engram](https://github.com/weaviate/engram-python-sdk) concepts + [Noema](https://github.com/Fail-Safe/Noema) Markdown files. | `.agent/tpm.md` |
| **Codebase Graph & Relational Index** | Structural codebase maps ([Graphify](https://github.com/Graphify-Labs/graphify)) + relational queries ([codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)) + [sqlite-vec](https://github.com/asg017/sqlite-vec) vector RAG. | `index-map <dir>` |
| **System Admin & Diagnostics** | Live health monitoring, AUR/security audits, system optimization, status routing, and git commit hooks. | [`/tools/agentic/system/`](/tools/agentic/system) |
| **Model Select TUI** | Real-time **[Cloud Connection](https://github.com/j5onrf/local-ai/blob/main/modules/Readme.md)** TUI, key toggles, and endpoint selector. | `model select` |
| **Interactive Textual TUI** | Full-screen, **[Textual](https://github.com/j5onrf/local-ai/blob/main/modules/Readme.md)** TUI workspace powered by a C-speed `uvloop` event loop. | `/tui` |

---

## CLI Launch Interface

> Customize box themes with `/box [1-5]`. For detailed multi-agent workflows, read the [**Workspace Manual**](https://github.com/j5onrf/local-ai/blob/main/projects/Readme.md).

#### 1. Interactive Multi-Turn Chat (`ai`)
```console
~ ❯ ai
╭─  >_ Local-AI Agent  ──────────────╮
│     model:  Qwen3.6-35B-A3B.gguf   │
│ directory:  ~                      │
│     skill:  chat                   │
│  database:  stateless              │
╰─────────────────── Ctrl+C to exit ─╯
 Startup context: 103 tokens
❯ 
```
#### 2. Workspace & Sub-Agent (`ai init <path>`)
```console
~ ❯ sess
[01/03] ❯ [session test] ai init ~/session-test --init
:: ↵ run  Esc: 
✔ Mapping complete! [session-test index-map & SQLite graph database updated]
╭────────────────────────────────────────────────────────╮
│   >_ Local-AI Agent [sub-agent #1]                     │
│                                                        │
│     model:  Qwen3.6-35B-A3B.gguf                       │
│ directory:  ~/.config/local-ai/projects/session-test   │
│     skill:  hermes/pro                                 │
│  database:  active (0 facts, 2 turns)                  │
╰─────────────────────────────────────── Ctrl+C to exit ─╯
 Startup context: 195 tokens

Agent: Workspace loaded. Awaiting instructions.

 [ 7 tokens | 0.28s | 28.23 t/s ]
 [ 703 in | 7 out | ctx: 8.7% ]
❯ 
```

---

## Core Capabilities

| Core Module | Capability | Description |
| :--- | :--- | :--- |
| **Engine** | **Zero-Daemon** | 0% idle CPU/RAM usage. Native Python standard-library execution. |
| **Resilience** | **Provider Cascade** | Top-down `.env` fallback: Gemini $\rightarrow$ OpenRouter $\rightarrow$ OpenAI $\rightarrow$ Claude $\rightarrow$ Grok $\rightarrow$ Local GGUF. |
| **Multi-Agent** | **Subagents** | [Vercel Eve](https://github.com/vercel/eve)-style sub-agents with [herdr](https://github.com/ogulcancelik/herdr) multiplexing via (`-save`/`-load`). |
| **Safety** | **Zero-Trust Gates** | Mandatory approval prompts for commands and out-of-bounds file access. |
| **Validation** | **Type-Safe & AST Guard** | [Pydantic AI](https://github.com/pydantic/pydantic-ai) schemas + [OpenAI Agents](https://github.com/openai/openai-agents-python)-style self-correcting `.py`/`.json` writes. |
| **Optimization** | **Token-Slasher** | Custom [`tool`](https://github.com/j5onrf/fetch/tree/main/tools) and [`skill`](https://github.com/j5onrf/fetch/tree/main/skills) integration built for minimal token consumption. |

---

## Command Reference

```console
╭─  ⚙ Help & Commands  ───────────────────────────────────────────────╮
│   Shortcuts: Esc: bypass  Ctrl+C: cancel                            │
│                                                                     │
│   Available commands:                                               │
│  /h                          - Help menu                            │
│  /box [1-5]                  - Box style preset                     │
│  /t [N|show|hide]            - Set reasoning budget or show/hide    │
│  /g, /yolo                   - Toggle confirmation gates (YOLO)     │
│  /m                          - Toggle database memory               │
│  /stats                      - Generation speed stats               │
│  /tok                        - Context token usage                  │
│  /sync                       - Sync index                           │
│  /clear                      - Chat & memory                        │
│  /sp                         - Toggle spellchecker                  │
│  /s <q>                      - Skills                               │
│  /tui                        - Textual UI                           │
│  -save <tag>                 - Save session checkpoint              │
│  -load                       - Load or clone checkpoint             │
│  /f, /tk, /b, /a             - Follow-up, Think, Brainstorm, All    │
│  view file <path>            - Load file into context               │
│  exit, quit, q               - Exit                                 │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## Setup & Installation

```bash
# 1. Install system dependencies
sudo pacman -S python-rich python-requests

# 2. (Optional Extensions) Ultra-fast /tui and vector search
yay -S python-sqlite-vec && sudo pacman -S python-textual python-uvloop

# 3. Clone repository
git clone https://github.com/j5onrf/local-ai.git ~/.config/local-ai

# 4. Register shell environment hook
echo '[ -f "$HOME/.config/local-ai/ai-hook.sh" ] && source "$HOME/.config/local-ai/ai-hook.sh"' >> ~/.bashrc
source ~/.bashrc

# 5. Create your configuration file
nano ~/.config/local-ai/.env
```

#### Configuration Example (`~/.config/local-ai/.env`):

```env
# Top-Down Cascade Fallback Priority
GEMINI_API_KEY="AIzaSyYourGeminiKey"
GEMINI_MODEL="gemini-3.5-flash-lite"

OPENROUTER_API_KEY="sk-or-v1-YourOpenRouterKey"
OPENROUTER_MODEL="openrouter/free"

AI_MAX_TOKENS="8192"
```

---

## Developer Activity

<p align="center">
  <img src="https://shieldcn.dev/chart/github/commits/j5onrf.svg?title=Commit+Activity&theme=zinc&mode=dark&bg=transparent&color=10b981&fill=true" alt="Commit Activity" />
</p>

---

## Contributors & Credits

<p align="center">
  <img src="https://shieldcn.dev/contributors/j5onrf/local-ai.svg?theme=zinc&limit=10&radius=12" alt="Contributors Grid" />
</p>

* **Contributions:** [suyadnya](https://github.com/wibawasuyadnya) for `.env` architecture, macOS compatibility testing, and alias optimization.
* **Community:** Contributions are always welcome!

