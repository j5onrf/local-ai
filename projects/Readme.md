# Workspace & Session Manager Manual
Local agent workspaces, dynamic memories, save checkpoints, and codebase mapping.

```console
~ ❯ session
[02/02] ❯ [session test] ai init ~/session-test --init
:: ↵ run  Esc: 
ℹ Compiling relational index graph...
✔ Compiled index-map: ~/session-test/index-map-session-test.txt
✔ Created graph database: ~/session-test/index-map-memory-session-test.db
╭──────────────────────────────────────────────╮
│  >_ Local-AI Agent                           │
│                                              │
│  model:     Qwen3.6-35B-A3B.gguf             │
│  directory: ...i/projects/session-test       │
│  skill:     init                             │
│  database:  active (3 facts, 26 turns)       │
╰──────────────────────────────────────────────╯
[sys] Startup context: 160 tokens | Ctrl+C to exit.

Agent: Workspace loaded. Awaiting instructions.
 [7 tokens | 0.52s | 23.38 t/s]
 [ 918 in | 10 out | cost: $0.00000 | today: $0.0000 | ctx: 11.3% ]
❯ hello
[sys] Memory recall skipped.
Agent: Hello! How can I assist you with your Python project today?
 [13 tokens | 1.03s | 22.68 t/s]
 [ 950 in | 13 out | cost: $0.00000 | today: $0.0000 | ctx: 11.8% ]
❯ /clear
[sys] Conversation history, cloud session, and local TPM memory cleared.

❯ I am working as a Lead Python Developer. I prefer using Helix for editing files, and my favorite shell is Bash.
Agent: Understood. I have noted your preferences:

*   **Role:** Lead Python Developer
*   **Editor:** Helix
*   **Shell:** Bash

❯ /tok

[sys] Context Window: 487/8192 tokens
[sys] Usage: [█░░░░░░░░░░░░░░░░░░░] 5.9%
[sys] Remaining: 7705 tokens

❯
```

## 1. Directory Structure
*   `~/.config/local-ai/projects/database/*.db`: Isolated SQLite database managing history per workspace.
*   `~/.config/local-ai/.spend_ledger.json`: Local-only daily token and API cost ledger (git-ignored).
*   `~/<workspace>/.agent/session.json`: Secure server-side tracking key for cloud APIs.
*   `~/<workspace>/.agent/tpm.md`: Human-readable personal facts, editable by hand.
*   `~/<workspace>/index-map-<project>.txt`: Codebase structural blueprint compiled on-the-fly.
*   `~/<workspace>/index-map-memory-<project>.db`: Active SQLite-backed relational knowledge graph.
*   `~/<workspace>/history.md`: Chronological Markdown conversation ledger.

## 2. In-Session Commands
*   **`/clear` / `/reset`**: Wipes local history, deletes cloud session, deletes `history.md`, and SQL-deletes your facts/turns.
*   **`/g`**: **Toggle Confirmation Gates** ON/OFF. Toggling gates off enables autonomous workspace editing.
*   **`/m`**: Unifies and toggles long-term memory and TPM reconciliation ON/OFF.
*   **`/r` / `/r [limit]`**: **Toggle Deep Reasoning** ON/OFF on-the-fly (defaults to 500 tokens, or set custom token limit).
*   **`/stats`**: Toggles real-time generation speed metrics (`speed_test.py`), token spend ledger, and active model indicators ON/OFF.
*   **`/tok`**: Displays live context window usage progress bar.
*   **`/skill <search>`** (or `/s`): Search and load custom skills dynamically.
*   **`Esc` or `Right Arrow`**: Instantly bypasses memory/tool authorization prompts.

## 3. Checkpoints & Handoff (Save States)
*   **Save Current State:** `❯ -save <tag>` (Saves snapshot directly to SQLite).
*   **Rollback State:** `❯ -load` (or `-timeline`). Lists snapshots; type index and press `Enter`.
*   **Global Handoff**: If a checkpoint is not found locally, `/load` scans all other databases to clone it. Allows risk-free sandboxing in fresh folders.

## 4. On-Demand File Context (Local RAG)
*   **Whole-File Context**: `❯ view file <filename>` (or `read`/`show`). Runs a local `cat` behind the scenes to append file contents into the context.
*   **Snippet-Specific Context**: `❯ read function <symbol>`. Queries the relational index database and extracts *only* the specific function or class code block based on line offsets, saving up to 95% in token overhead.

## 5. Security & Execution Isolation
*   **Mode Segregation**: Standard conversational sessions (`ai`) and single-shot queries (`ai <query>`) operate in strict **read-only** mode. Active file-editing and command execution capabilities are strictly restricted to workspace agent sessions (`ai init`).
*   **Workspace Boundary Lock**: Even when confirmation gates are disabled (`/g`), any attempt by the agent to read, write, or list files outside the active workspace directory (e.g., in `~` or system root `/`) **always** forces a manual `[Y/n]` authorization prompt.
*   **Visual Line-Diffs**: Before applying any file modification, the agent renders a colorized unified line-diff directly in your terminal so changes can be inspected before approval.
*   **Docker & Symlinking**: Run the agent inside a Docker container to isolate the execution context entirely from your host. You can symlink your local clone (`~/.config/local-ai`) into the container's volume mount directories, allowing you to modify files locally on your host while safely executing and testing them inside a secure sandbox.
*   **Vetting**: Scan all custom skills with [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) before importing.

## 6. Codebase Graph Mapper & Relational Index
*   **Command:** `index-map <dir>` (or automatically executed on startup if the flat map `.txt` or relational `.db` is missing/outdated).
*   **Core Capabilities:**
    *   *SQLite-Backed Graph Model*: Generates a local `index-map-memory-<project>.db` database containing files, classes, and function scopes (`nodes`) and call-chain/inheritance connections (`edges`).
    *   *Multi-Language AST & Regex Parsing*: Parses code targets using standard Python AST visitors and high-speed structural regex profiles for compiled or scripting languages (Rust, Go, JS/TS, C/C++, Lua).
    *   *LSP-Lite Reference Resolver*: Resolves dependency calls heuristically by checking local file bounds, module import statements, and globally unique workspace symbols.
    *   *Human-in-the-Loop RAG*: Maps intent triggers to graph queries, prompting for authorization before injecting call trees and function snippets into the context.
    *   *Images & Binaries*: Decodes sizes and dimensions of image assets (PNG/JPG/GIF/SVG) directly from binary headers in microseconds.

## 7. Context Limits
*   **Inline Override:** `AI_MAX_TOKENS=16000 session-test`
*   **Global Override:** `AI_MAX_TOKENS=16000`

## 8. Temporal Personality Memory (TPM)
*   **Origins**: Combines Weaviate Engram's SQLite active reconciliation loop with Noema's hand-editable, local Markdown file system.
*   **Background Extraction**: Spawns a background thread on completion to extract facts without delay.
*   **Dynamic Sync**: Manual edits made to `.agent/tpm.md` are synced back into SQLite at bootup.
*   **Reconciliation**: SQL `INSERT OR REPLACE` overwrites old contradictory facts cleanly.

