# Local-AI Agent Workspace & Session Manual

High-speed local developer agent, episodic memory system, checkpoint state manager, and codebase index graph.

```console
~ ❯ session
[01/03] ❯ [session test] ai init ~/session-test --init
:: ↵ run  Esc: 
✔ Mapping complete! [session-test index-map & SQLite graph database updated]
[1] 702000
╔═  ❖ Local-AI Agent [sub-agent #1] ════════════╗
║     model:  Qwen3.6-35B-A3B.gguf              ║
║ directory:  ~/.config/local-ai/session-test   ║
║     skill:  init code2                        ║
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

## 2. In-Session Commands

```text
╭─  ⚙ Help & Commands  ───────────────────────────────────────────────╮
│   Shortcuts: Esc: bypass  Ctrl+C: cancel                            │
│                                                                     │
│   Available commands:                                               │
│  /help, /h            - Show help menu                              │
│  /t [N|show|hide]     - Set reasoning budget or show/hide           │
│  /g                   - Toggle confirmation gates                   │
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
- **Vector Search (`sqlite-vec`):** Automatically embeds codeblocks into a parallel `nodes_vec` virtual table, auto-calibrating to local embedding model dimensions (e.g., 384, 512, 1024).
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
```
