# Local-AI Agent Workspace & Session Manual

High-speed local developer agent, episodic memory system, checkpoint state manager, and codebase index graph.

```console
~ ❯ session
[01/03] ❯ [session test] ai init ~/session-test --init
:: ↵ run  Esc: 
✔ Mapping complete! [session-test index-map & SQLite graph database updated]
╔═  ❖ Local-AI Agent [sub-agent #1] ════════════╗
║     model:  Qwen3.6-35B-A3B.gguf              ║
║ directory:  ~/.config/local-ai/session-test   ║
║     skill:  pi/full                           ║
║  database:  active (3 facts, 26 turns)        ║
╚═══════════════════════════ Ctrl+C to exit ════╝
 Startup context: 191 tokens

Agent: Workspace loaded. Awaiting instructions.
 [7 tokens | 0.52s | 28.38 t/s]
 [ 918 in | 10 out | cost: $0.00000 | today: $0.0000 | ctx: 11.3% ]
❯ hello
[sys] Memory recall skipped.
Agent: Hello! How can I assist you with your Python project today?
 [13 tokens | 1.03s | 26.68 t/s]
 [ 950 in | 13 out | cost: $0.00000 | today: $0.0000 | ctx: 11.8% ]
❯ /clear
[sys] Conversation history, cloud session, and local TPM memory cleared.

❯ I am a Lead Python Developer. I use Helix editor, and my favorite shell is Bash.
Agent: Understood. I have noted your preferences:

*   **Role:** Lead Python Developer
*   **Editor:** Helix
*   **Shell:** Bash

❯ /sync
✔ Mapping complete! [session-test index-map & SQLite graph database updated]
[sys] Codespace map and relational SQLite graph successfully synchronized.

❯ /tok

[sys] Context Window: 838/8192 tokens
[sys] Usage: [██░░░░░░░░░░░░░░░░░░] 10.2%
[sys] Remaining: 7354 tokens

❯ 
```

---

## Customizable UI Box Themes

Switch box styles using `/box [1-5]` (or type `/box` to cycle). Your choice persists across sessions in `~/.config/local-ai/.state.json`.

#### Style #1: Double Border (Default)
```console
╔═  ❖ Local-AI Agent  ══════════╗
║     model:  Qwen3.5-2B.gguf   ║
║ directory:  ~                 ║
║     skill:  default           ║
║  database:  stateless         ║
╚══════════════ Ctrl+C to exit ═╝
```

#### Style #2: Codex Rounded
```console
╭─  >_ Local-AI Agent  ─────────╮
│     model:  Qwen3.5-2B.gguf   │
│ directory:  ~                 │
│     skill:  default           │
│  database:  stateless         │
╰────────────── Ctrl+C to exit ─╯
```

#### Style #3: Heavy Square
```console
┏━  ❖ Local-AI Agent  ━━━━━━━━━━┓
┃     model:  Qwen3.5-2B.gguf   ┃
┃ directory:  ~                 ┃
┃     skill:  default           ┃
┃  database:  stateless         ┃
┗━━━━━━━━━━━━━━ Ctrl+C to exit ━%
```

#### Style #4: Minimalist Line
```console
 ─  Local-AI Agent  ──────────── 
      model:  Qwen3.5-2B.gguf    
  directory:  ~                  
      skill:  default            
   database:  stateless          
 ────────────── Ctrl+C to exit ─ 
```

#### Style #5: Classic In-Panel Codex
```console
╭───────────────────────────────╮
│  >_ Local-AI Agent            │
│                               │
│     model:  Qwen3.5-2B.gguf   │
│ directory:  ~                 │
│     skill:  default           │
│  database:  stateless         │
╰────────────── Ctrl+C to exit ─╯
```

---

## 1. Directory Structure

| Path | Purpose |
| :--- | :--- |
| `~/.config/local-ai/projects/database/*.db` | SQLite databases tracking turns and memories per workspace. |
| `~/.config/local-ai/.active_sessions/` | Ephemeral PID files tracking active sub-agent processes. |
| `~/.config/local-ai/.spend_ledger.json` | Daily local/cloud API token spend ledger. |
| `~/<workspace>/.agent/session.json` | Server-side interaction tracking state for cloud APIs. |
| `~/<workspace>/.agent/tpm.md` | Human-editable Markdown copy of personal memory facts. |
| `~/<workspace>/index-map-<project>.txt` | Compiled structural shorthand map of the codebase. |
| `~/<workspace>/index-map-memory-<project>.db` | SQLite relational knowledge graph & vector embeddings (`sqlite-vec`). |
| `~/<workspace>/history.md` | Chronological Markdown conversation log across all sub-agents. |

---

## Workspace Agent Profiles (`.agent/config.json`)

When you run `ai init <path>` in a workspace for the first time, an interactive profile selector menu allows you to set the default Agent Persona for that project:

```text
[ai init] Select default Agent Profile for workspace session-test:

  ❯  1. Basic / Default    (~120 tokens | Standard init.md assistant)
     2. Pi Agent [1:1]     (~400 tokens | Streamlined native Pi prompt)
     3. Claude Code        (~440 tokens | Full 1:1 Claude Code CLI prompt)
     4. Hermes Agent       (~380 tokens | Full 1:1 Nous Hermes system prompt)

  :: ↵ select  ↑/↓ navigate  Tab: YOLO [OFF]  Esc: default
```

> **Reset Profile Menu:** To change or reset a workspace's saved profile, delete `.agent/config.json` inside that project:
> ```bash
> rm .agent/config.json
> ```

### Master Agent Profiles & Personalities

Although all three master profiles leverage the same local system tools (`read_file`, `write_file`, `list_dir`, `run_command`), they instruct the model to execute tasks using entirely different logical architectures, structural constraints, and conversational styles:

* **Claude Code (`claude/full`):** *The Methodical Planner.* Instructs the model to write out structured plans within `<thought>` blocks before executing any tool. It is highly analytical, cautious, and designed to trace entire codebase dependency trees before applying edits. It uses **Targeted Reading** to inspect only relevant files mapped by the index, rather than reading the entire directory. Best for complex refactoring and multi-file changes.
* **Pi Agent (`pi/full`):** *The Surgical Developer.* An ultra-direct, action-first assistant that strips out conversational padding, disclaimers, and unsolicited explanations. It uses a strict verification loop, requiring the model to immediately test code updates via shell commands before completing a turn. It relies on **Targeted Reading** to surgically inspect only the specific files or functions necessary for the task. Best for rapid, targeted file editing and fast bug fixes.
* **Hermes Agent (`hermes/full`):** *The Automation Engine.* Treats software development as a pure, sequence-driven tool-calling pipeline. It focuses heavily on executing shell commands, managing database updates, and running tests. It uses **Targeted Reading** to execute background tool commands on isolated components. Best for structural scripts, migrations, and running background diagnostics.

---

### Graph Index Mapping & Targeted Reading

To prevent context-window bloat on large-scale repositories, all three master profiles utilize a **Targeted Reading** architecture enabled by your project's `index-map` files (`index-map-<project>.txt` and `index-map-memory-<project>.db`):

* **How it works:** On startup (`ai init`), the harness compiles a lightweight, structural outline of your codebase's classes, functions, and import trees. 
* **Context Preservation:** Instead of executing broad, unguided file reads that would instantly saturate your local context window on a large codebase, the model uses this compiled index map to surgically identify which specific functions, files, or symbols are relevant to your query.
* **On-Demand Inspection:** The model then uses `read_file` or your RAG symbol shortcuts (`Run: read function <symbol>`) to pull **only** the necessary codeblocks into active memory.

---

## 2. In-Session Commands

```text
╭─  ⚙ Help & Commands  ───────────────────────────────────────────────╮
│   Shortcuts: Esc: bypass  Ctrl+C: cancel                            │
│                                                                     │
│   Available commands:                                               │
│  /help, /h            - Show help menu                              │
│  /box, /box-style     - Change CLI box style (1-5)                  │
│  /t [N|show|hide]     - Set reasoning budget or show/hide           │
│  /g, /yolo            - Toggle confirmation gates (YOLO mode)       │
│  /m                   - Toggle long-term memory                     │
│  /stats               - Toggle generation speed stats               │
│  /tok                 - Show context token usage                    │
│  /sync, /re           - Sync codebase AST & graph                   │
│  /clear, /reset       - Clear chat history & memory                 │
│  /spell, /sp          - Toggle spellchecker                         │
│  /skill <q>, /s       - Search and load custom skills               │
│  /tui                 - Open full-screen Textual UI                 │
│  -save <tag>          - Save session checkpoint                     │
│  -load, -timeline     - Load or clone checkpoint                    │
│  view file <path>     - Load file into context                      │
│  read function <sym>  - Load AST symbol snippet                     │
│  exit, quit, q        - Exit Local-AI Agent                         │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## 3. Checkpoints & Save States

- **Save Snapshot:** `❯ -save <tag>` — Writes an instant session snapshot to SQLite.
- **Restore State:** `❯ -load` (or `-timeline`) — Lists all available checkpoints to restore.
- **Global Handoff:** If a checkpoint is missing locally, `-load` searches other workspace databases to clone it into your active session.

---

## 4. On-Demand File Context (Local RAG)

- **Whole File Insertion:** `❯ view file <path>` (or `read`/`show`) — Reads and appends file contents into context.
- **Targeted Symbol Extraction:** `❯ read function <symbol>` — Uses line offsets in the relational database to inject *only* the specific function/class source block (saves up to 95% token overhead).

---

## 5. Codebase Graph Mapper & Relational Index

- **Execution:** Runs via `index-map <dir>` or automatically on boot if flat maps are missing/outdated.
- **Vector Search (`sqlite-vec`):** Automatically embeds codeblocks into a parallel `nodes_vec` virtual table, auto-calibrating to local embedding model dimensions.
- **Relational Graph (`nodes` & `edges`):** Maps AST nodes (classes, methods, functions) and symbol call-chains across Python, Rust, Go, JS/TS, C/C++, and Lua.
- **Binary & Asset Extraction:** Extracts dimension metadata from images (PNG/JPG/SVG) directly from binary headers.

---

## 6. Temporal Personality Memory (TPM)

- **Asynchronous Fact Extraction:** Runs in a background thread after each turn without delaying responses.
- **Bidirectional Sync:** Automatically reconciles manual hand-edits in `.agent/tpm.md` back into SQLite on startup using `INSERT OR REPLACE`.

---

## 7. Workspace Sub-Agents & Concurrency

- **Process Badging:** Assigns sequential badges (`[sub-agent #1]`, `[sub-agent #2]`) when opening parallel terminals in the same workspace directory.
- **Process Garbage Collection:** Automatically cleans up stale PID files in `.active_sessions/` upon startup.
- **WAL Concurrency:** Uses SQLite Write-Ahead Logging (WAL) and busy-timeout queues to prevent write locks during concurrent sub-agent executions.
- **Shared Chronological Log:** Sub-agents write their completed actions sequentially to `history.md`.

---

## 8. Security & Execution Isolation

- **Read-Only Default:** Standard chat (`ai`) operates in strict read-only mode. Workspace modifications require `ai init`.
- **Workspace Directory Lock:** Modifying or inspecting files outside the project root (`~` or `/`) **always** triggers a mandatory authorization gate.
- **Colorized Unified Diffs:** Renders visual syntax-highlighted diffs in terminal prior to executing file modifications.
- **Docker Sandboxing:** Fully supports running inside Docker volume mounts with host-symlinked configs (`~/.config/local-ai`).

---

## 9. Context Limits

Override the maximum context token limit inline or globally via environment variables:
```bash
# Inline override:
AI_MAX_TOKENS=16000 ai init ~/my-project

# Global export:
export AI_MAX_TOKENS=16000

