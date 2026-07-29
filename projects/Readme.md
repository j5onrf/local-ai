# Local-AI Agent Workspace & Session Manual

High-speed local developer agent, episodic memory system, checkpoint state manager, and codebase index graph.

```console
~ ❯ session
[01/03] ❯ [session test] ai init ~/session-test --init
:: ↵ run  Esc: 
╭─  >_ Local-AI Agent  ──────────────────────────────────╮
│     model:  Qwen3.5-2B.gguf                            │
│ directory:  ~/.config/local-ai/projects/session-test   │
│     skill:  pi/lite                                    │
│  database:  active (0 facts, 24 turns)                 │
╰─────────────────────────────────────── Ctrl+C to exit ─╯
 Startup context: 327 tokens

╭─ ⚙ Thinking Process ───────────────────────────────────────────────────────────────────────────╮
│ The user has provided me with a system prompt that defines my role as Pi Lite, an efficient    │
│ local software developer assistant. I need to follow specific instructions:                    │
│                                                                                                │
│ 1. DO NOT call tools at startup (read_file, list_dir, run_command)                             │
│ 2. Learn from CODESPACE MAP first                                                              │
│ 3. Reply with ONE brief sentence acknowledging the project and wait for user's instructions    │
│                                                                                                │
│ I should acknowledge the project structure without making any tool calls yet. The codebase     │
│ appears to be in /home/user/.config/local-ai/projects/session-test based on the path           │
│ mentioned in the map.                                                                          │
╰────────────────────────────────────────────────────────────────────────────────────────────────╯
Agent:  Acknowledging the session-test workspace under `/home/user/.config/local-ai/projects/`
ready for your task assignment.
 [ think: 120 | ans: 26 | 146 tokens | 3.8s @ 41.6 t/s ]
 [ 1199 in | 146 out | ctx: 16.4% ]
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

  ─── Standard ───────────────────────────────────────────
  ❯  1. Default Assistant    (~120t | Standard assistant)
  ─── Full 1:1 Tier (Direct Action) ───────────────────────────────────────────
     2. Pi Agent [1:1]       (~400t | Direct tool prompt)
     3. Claude Code          (~440t | Direct tool prompt)
     4. Hermes Agent         (~380t | Direct tool prompt)
  ─── Pro Tier (Index-First / 35B+ & Cloud) ───────────────────────────────────────────
     5. Pi Pro               (~280t | Index-first + reasoning prompt)
     6. Claude Pro           (~290t | Index-first + reasoning prompt)
     7. Hermes Pro           (~280t | Index-first + reasoning prompt)
  ─── Lite Tier (Index-First / 1B–7B Models) ───────────────────────────────────────────
     8. Pi Lite              (~220t | Index-first standby prompt)
     9. Claude Lite          (~230t | Index-first standby prompt)
    10. Hermes Lite          (~220t | Index-first standby prompt)

  :: ↵ select  ↑/↓ navigate  Tab: YOLO [OFF]  Esc: default
```

> **YOLO Mode Guard:** If you hit <kbd>Enter</kbd> without toggling <kbd>Tab</kbd> first, a clean 1-line prompt asks: `Enable Autonomous YOLO mode? [y/N]:` to prevent accidentally launching with manual tool confirmation gates on.
>
> **Reset Profile Menu:** To change or reset a workspace's saved profile, delete `.agent/config.json` inside that project:
> ```bash
> rm .agent/config.json
> ```

### Master Agent Profiles & Personalities

Although all profiles leverage the same local system tools (`read_file`, `write_file`, `list_dir`, `run_command`), they instruct models using two primary architectural tiers:

#### 1. Full 1:1 Profiles (Designed for Large Models 14B–70B+)
* **Claude Code (`claude/full`):** *The Methodical Planner.* Writes structured plans within `<thought>` blocks before executing tools. Highly analytical, cautious, and designed to trace entire codebase dependency trees before applying edits. Best for complex refactoring.
* **Pi Agent (`pi/full`):** *The Surgical Developer.* An ultra-direct, action-first assistant that strips out conversational padding and disclaimers. Requires immediate verification of updates via shell commands. Best for rapid file editing and fast bug fixes.
* **Hermes Agent (`hermes/full`):** *The Automation Engine.* Treats software development as a pure, sequence-driven tool-calling pipeline. Focuses on executing shell scripts, database updates, and diagnostics. Best for structural scripts and background workflows.

#### 2. Lite Profiles (Optimized for Small/2B Models)
* **Pi Lite (`pi/lite`), Claude Lite (`claude/lite`), Hermes Lite (`hermes/lite`):** *Index-First & Standby Architecture.* Smaller local models (1B–3B) often exhibit tool eagerness, blindly calling `list_dir` or `read_file` across every workspace file at startup. Lite profiles enforce a **Strict Startup Rule**:
  1. **No Startup Tool Calls:** Disables tool calls during initialization.
  2. **Index-Map Ingestion:** Ingests the project structure directly from the `CODESPACE MAP` context.
  3. **Standby Hand-off:** Replies with 1 brief sentence acknowledging the project, then waits for the user's explicit request before making targeted tool calls.

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

