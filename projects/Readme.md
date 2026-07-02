# Workspace & Session Manager Manual
Local agent workspaces, dynamic memories, save checkpoints, and codebase mapping.

```console
~ ❯ session
[02/02] ❯ [session test 2] ai init ~/session-test-2 --init
:: ↵ run  Esc: 
ℹ Compiling index map...
✔ Compressed index-map: ~/session-test-2/index-map-session-test-2.txt
╭──────────────────────────────────────────────╮
│  >_ Local-AI Agent                           │
│                                              │
│  model:     local-model                      │
│  directory: ...i/projects/session-test-2     │
│  skill:     init                             │
│  database:  active (3 facts, 26 turns)       │
╰──────────────────────────────────────────────╯
[sys] Startup context: 104 tokens | Ctrl+C to exit.

Agent: Workspace loaded. Awaiting instructions.
 [7 tokens | 0.52s | 23.38 t/s]
[via .../Qwen3.6-35B-A3B.gguf]
❯ hello
[sys] Memory recall skipped.
Agent: Hello! How can I assist you with your Python project today?
 [13 tokens | 1.03s | 22.68 t/s]
[via .../Qwen3.6-35B-A3B.gguf]
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
*   `~/<workspace>/.agent/session.json`: Secure server-side tracking key for cloud APIs.
*   `~/<workspace>/.agent/tpm.md`: Human-readable personal facts, editable by hand.
*   `~/<workspace>/index-map-<project>.txt`: Codebase structural blueprint compiled on-the-fly.
*   `~/<workspace>/history.md`: Chronological Markdown conversation ledger.

## 2. In-Session Commands
*   **`/clear` / `/reset`**: Wipes local history, deletes cloud session, deletes `history.md`, and SQL-deletes your facts/turns.
*   **`/m`**: Unifies and toggles long-term memory and TPM reconciliation ON/OFF.
*   **`/stats`**: Toggles real-time generation speed metrics (`speed_test.py`) ON/OFF.
*   **`/tok`**: Displays live context window usage progress bar.
*   **`/skill <search>`** (or `/s`): Search and load custom skills dynamically.
*   **`Esc` or `Right Arrow`**: Instantly bypasses memory/tool authorization prompts.

## 3. Checkpoints & Handoff (Save States)
*   **Save Current State:** `❯ -save <tag>` (Saves snapshot directly to SQLite).
*   **Rollback State:** `❯ -load` (or `-timeline`). Lists snapshots; type index and press `Enter`.
*   **Global Handoff**: If a checkpoint is not found locally, `/load` scans all other databases to clone it. Allows risk-free sandboxing in fresh folders.

## 4. On-Demand File Context (Local RAG)
*   **Command:** `❯ view file <filename>` (or `read`/`show`).
*   **Execution:** Runs a local `cat` behind the scenes and injects raw file contents into context.

## 5. Security Isolation
*   **Docker**: Run the agent inside a Docker container to isolate the execution context entirely from your host.
*   **Vetting**: Scan all custom skills with [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) before importing.

## 6. Codebase Graph Mapper (v1.5.0)
*   **Command:** `index-map <dir>` (or automatic on startup).
*   **Features:**
    *   *Auto-Create*: Automatically runs `mkdir -p` if the directory does not exist.
    *   *Top-Level AST*: Parses only top-level nodes for Python/Rust/Go. 100x faster than full walking.
    *   *Shorthand*: Strips imports and trims function arguments to save 50% in token context.
    *   *Graphing*: Compiles Obsidian-style `[[wiki-links]]` into a relational link graph.
    *   *Images*: Byte-level header parsing for PNG/JPG/GIF/SVG dimensions and sizes in microseconds.

## 7. Context Limits
*   **Inline Override:** `AI_MAX_TOKENS=16000 session-test`
*   **Global Override:** `export AI_MAX_TOKENS=16000`

## 8. Dynamic Memory (TPM)
*   **Background Extraction**: Spawns a background thread on completion to extract facts without delay.
*   **Dynamic Sync**: Manual edits made to `.agent/tpm.md` are synced back into SQLite at bootup.
*   **Reconciliation**: SQL `INSERT OR REPLACE` overwrites old contradictory facts cleanly.
```
