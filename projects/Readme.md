# Local-AI Agent Workspace & Session Manual

High-speed local developer agent, episodic memory, SQLite checkpoints, IPython kernel harness, and codebase index graph.

```console
~ ❯ sess
[02/03] ❯ [session test 2] ai init ~/session-test-2
:: ↵ run  Esc: 
[ok] Mapping complete! [session-test-2 index-map & SQLite graph database updated]

[ai init] Select default Agent Profile for workspace session-test-2:

Enable Autonomous YOLO mode? [y/N]: y
✓ Profile set to: Pi Py-Pro (Autonomous YOLO)

╭─  >_ Local-AI Agent  ────────────────────────────────────╮
│     model:  gemini-3.5-flash-lite                        │
│ directory:  ~/.config/local-ai/projects/session-test-2   │
│     skill:  pi/py-pro                                    │
│  database:  active (1 facts, 1 turns)                    │
╰───────────────────────────────────────── Ctrl+C to exit ─╯
 Startup context: 743 tokens

Agent: Workspace loaded. Awaiting instructions.
 [ think: 10 | ans: 10 | 20 tokens | 0.07s @ 136.9 t/s ]
 [ 794 in | 10 out | ctx: 9.8% ]
❯ 
```

---

## UI Box Themes

Switch CLI box styles using `/box [1-5]` (or type `/box` to cycle). Selection persists in `~/.config/local-ai/.state.json`.

#### Style #1: Codex Rounded (Default)
```console
╭─  >_ Local-AI Agent  ─────────╮
│     model:  gemini-3.5-flash  │
│ directory:  ~                 │
│     skill:  chat              │
│  database:  stateless         │
╰────────────── Ctrl+C to exit ─╯
```

#### Style #2: Double Border
```console
╔═  ❖ Local-AI Agent  ══════════╗
║     model:  gemini-3.5-flash  ║
║ directory:  ~                 ║
║     skill:  default           ║
║  database:  stateless         ║
╚══════════════ Ctrl+C to exit ═╝
```

#### Style #3: Heavy Square
```console
┏━  ❖ Local-AI Agent  ━━━━━━━━━━┓
┃     model:  gemini-3.5-flash  ┃
┃ directory:  ~                 ┃
┃     skill:  default           ┃
┃  database:  stateless         ┃
┗━━━━━━━━━━━━━━ Ctrl+C to exit ━┛
```

#### Style #4: Minimalist Line
```console
 ─  Local-AI Agent  ──────────── 
      model:  gemini-3.5-flash   
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
│     model:  gemini-3.5-flash  │
│ directory:  ~                 │
│     skill:  default           │
│  database:  stateless         │
╰────────────── Ctrl+C to exit ─╯
```

---

## 1. Directory Structure

All auto-created agent metadata files are strictly isolated inside `project/.agent/` to keep project workspaces completely clean.

| Path | Purpose |
| :--- | :--- |
| `~/.config/local-ai/projects/database/*.db` | Global SQLite turn history and fact memory database. |
| `~/.config/local-ai/.active_sessions/` | Sub-agent PID lockfiles for process tracking. |
| `~/.config/local-ai/.spend_ledger.json` | Global cloud API token usage and daily spend ledger. |
| `~/<workspace>/.agent/config.json` | Default workspace agent profile and YOLO settings. |
| `~/<workspace>/.agent/tpm.md` | Human-editable Markdown fact memory store. |
| `~/<workspace>/.agent/history.md` | Chronological session history log. |
| `~/<workspace>/.agent/task_log.md` | Audit log for autonomous `/task` loop executions. |
| `~/<workspace>/.agent/index-map-<project>.txt` | Shorthand codebase index map (Agent mode). |
| `~/<workspace>/.agent/index-map-memory-<project>.db` | Relational knowledge graph & `sqlite-vec` embeddings. |

---

## 2. Profile Selector (`ai init`)

Running `ai init <path>` sets the default workspace agent profile:

```console
[ai init] Select default Agent Profile for workspace session-test:

  ─── Agents ────────────────────────
  ❯  1. Pi Pro               (~280t)
     2. Claude Pro           (~290t)
     3. Hermes Pro           (~280t)

     1. Pi Lite              (~220t)
     2. Claude Lite          (~230t)
     3. Hermes Lite          (~220t)

  ─── Py ────────────────────────────
     1. Pi Py-Pro            (~300t)
     2. Claude Py-Pro        (~310t)
     3. Hermes Py-Pro        (~300t)

     1. Pi Py-Lite           (~220t)
     2. Claude Py-Lite       (~250t)
     3. Hermes Py-Lite       (~240t)

  :: ↵ select  ↑/↓ navigate  Tab: YOLO [OFF]  Esc: default
```

#### Profile Tiers

| Tier | Profiles | Model Scale | Overhead | Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Pro** | `pi/pro`, `claude/pro`, `hermes/pro` | Medium Models | `~280t–290t` | Index-first codebase mapping. |
| **Lite** | `pi/lite`, `claude/lite`, `hermes/lite` | Small Models | `~220t–230t` | Index-first standby preventing tool-eagerness loops. |
| **Py-Pro** | `pi/py-pro`, `claude/py-pro`, `hermes/py-pro` | Medium/Large Code Models | `~300t–310t` | Full IPython kernel harness (`exec_python`). |
| **Py-Lite** | `pi/py-lite`, `claude/py-lite`, `hermes/py-lite` | Small Code Models | `~220t–250t` | Concise IPython kernel harness preventing tool-eagerness loops. |

* **Reset Workspace Profile:** Delete `.agent/config.json` inside the project folder (`rm .agent/config.json`).
* **Customize Skills:** Modify or create profile `.md` files in `~/.config/local-ai/skills/profiles/`.

---

## 3. Command Reference

```console
╭─  ⚙ Help & Commands  ───────────────────────────────────────────────╮
│   Shortcuts: Esc: bypass  Ctrl+C: cancel                            │
│                                                                     │
│   Available commands:                                               │
│  /h                          - Help menu                            │
│  /py [code_or_cmd]           - Toggle or execute via IPython        │
│  /box [1-5]                  - Box style preset                     │
│  /task [goal]                - Autonomous task loop                 │
│  /t [N|show|hide]            - Set reasoning budget or show/hide    │
│  /g, /yolo                   - Toggle confirmation gates (YOLO)     │
│  /m                          - Toggle database memory               │
│  /md                         - Toggle Markdown                      │
│  /stats                      - Generation speed stats               │
│  /tok                        - Context token usage                  │
│  /sync                       - Sync index                           │
│  /clear                      - Chat & memory                        │
│  /sp                         - Spellchecker                         │
│  /s <q>                      - Skills                               │
│  /tui                        - Launch Textual UI                    │
│  -save <tag>                 - Save session checkpoint              │
│  -load                       - Load or clone checkpoint             │
│  /f, /tk, /b, /a             - Follow-up, Think, Brainstorm, All    │
│  file <path>                 - Load file into context               │
│  exit, quit, q               - Exit                                 │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## 4. Textual TUI Interface (`/tui`)

Full-screen async Textual interface powered by `uvloop` background workers. Launch via `/tui` or run `agent_tui.py`.

* **Plan / Build Modes (`Tab`):** Toggle between **Plan** (confirmation gate per tool action) and **Build** (Autonomous YOLO).
* **Background Services:** `uvloop` libuv file watching (`.agent/tpm.md`) and Unix domain socket IPC hub (`/tmp/local-ai-<workspace>.sock`) for multi-terminal sub-agent tracking.

---

## 5. IPython Kernel Harness (`/py`)

Replaces discrete JSON tool declarations with a live, persistent IPython kernel. Loaded variables, functions, and imports remain alive in kernel memory across cells, saving up to 90% context tokens.

- **Toggle Mode:** Type `/py` (or `/ipython`).
- **Global Smart Handler:** Typing `/py <cmd_or_code>` automatically ensures IPython mode is **ON** and executes the command immediately in both raw CLI and TUI.
- **In-Kernel SDK Functions:**
  - `read_file("path")` & `write_file("path", "content")`
  - `list_dir("path")`
  - `run_command("cmd")`
  - `read_symbol("symbol")`
- **Data Isolation:** Inspect large files or datasets using Python scripts (`import re`, `import ast`, `import json`) in memory without bloating the LLM context window.

---

## 6. Autonomous Task Loops (Ralph Engine)

Self-directed iterative loop that runs tools, verifies results, and self-corrects until a task is complete.

- **Inline Execution:** `/task "Create a module string_utils.py with tests and run unittest"`
- **Spec File Mode:** Create `TASK.md` in project root and run `/task`
- **Dual Completion Detection:** Checks both assistant text responses **and** tool execution logs (`exec_python`, `run_command`, etc.) for completion markers (`TASK COMPLETE`).
- **Stagnation Recovery:** Automatically detects duplicate turns and injects course-correction prompts.
- **Audit Logging:** Logs turn-by-turn goal progress into `.agent/task_log.md`.
- **Engine Script:** `~/.config/local-ai/tools/loop/ralph.py` (Supports flags `-n` / `--turns`, `-f` / `--file`, `--no-log`).

---

## 7. Checkpoints & Save States

- **Save:** `-save <tag>` — Snapshot session state to SQLite.
- **Load:** `-load` — Restore or clone session checkpoint across workspaces.

---

## 8. Local RAG & Context Injection

- **Whole File:** `file <path>` — Append entire file into context.
- **Targeted Symbol:** `read_symbol("<symbol>")` — Inject specific AST function/class snippet from index graph (saves 95% tokens).

---

## 9. Codebase Graph Mapper

The codebase intelligence engine features **dual-mode output routing**:

- **Agent Mode (`ai init` / `/sync`):** Outputs map files directly to `project/.agent/` to keep source directories clean.
- **Standalone CLI Mode (`index-map`):** Outputs map files to the project root directory when run independently in shell.
- **AST Graph:** Maps classes, methods, and call-chains across Python, Rust, Go, JS/TS, C/C++, Lua.
- **Vector Search:** Embeds codeblocks into `sqlite-vec` virtual tables for semantic retrieval.

---

## 10. Temporal Personality Memory (TPM)

- **Async Fact Extraction:** Auto-extracts user preferences in background thread after each turn.
- **Strict Fact Filtering:** Key blacklisting prevents project files/code from contaminating user memory.
- **Context Injection:** Compiles and injects facts into model `<context>` blocks every turn.
- **Human-Editable Sync:** Reconciles manual edits in `.agent/tpm.md` into SQLite on startup.

---

## 11. Sub-Agents & Concurrency

- **Process Badges:** Assigns sequence IDs (`[sub-agent #1]`, `[sub-agent #2]`) for parallel terminals.
- **Self-Healing Registry:** Auto-purges stale PID lockfiles (`.active_sessions/`) on exit or crash.
- **SQLite Lock Protection:** `PRAGMA busy_timeout = 5000` + `WAL` mode eliminates multi-agent database locks.
- **Unix Socket IPC:** Async socket hub (`/tmp/local-ai-<workspace>.sock`) for cross-terminal status messaging in TUI.

---

## 12. Security & Execution Isolation

- **Read-Only Default:** Workspace edits require explicit `ai init` enablement.
- **Directory Lock:** Enforces confirmation gates for paths outside project root.
- **Visual Diffs:** Shows colorized diffs prior to file writes.
- **Kernel Zero-Trust Overrides:** In IPython mode, built-ins (`open`, `os.listdir`) are guarded against out-of-bounds file access.

---

## 13. Environment Variables & Context Limits

Override max context token limits or model defaults:
```bash
AI_MAX_TOKENS=16000 ai init ~/my-project
```
