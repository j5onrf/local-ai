# Local-AI Agent Workspace & Session Manual

High-speed local developer agent, episodic memory, SQLite checkpoints, and codebase index graph.

```console
~ ❯ sess
[02/03] ❯ [session test 2] ai init ~/session-test-2
:: ↵ run  Esc: 
[ok] Mapping complete! [session-test-2 index-map & SQLite graph database updated]

[ai init] Select default Agent Profile for workspace session-test-2:

Enable Autonomous YOLO mode? [y/N]: y
✓ Profile set to: Pi Py-Lite (Autonomous YOLO)

╭─  >_ Local-AI Agent  ────────────────────────────────────╮
│     model:  Qwen3.5-2B.gguf                              │
│ directory:  ~/.config/local-ai/projects/session-test-2   │
│     skill:  pi/py-lite                                   │
│  database:  active (0 facts, 8 turns)                    │
╰───────────────────────────────────────── Ctrl+C to exit ─╯
 Startup context: 447 tokens

╭─ ⚙ ────────────────────────────────────────────────────
The user has confirmed that their workspace is loaded. According to my instructions, I should only reply
with "Workspace loaded. Awaiting instructions." and NOT call any tools at startup. This means I need to
acknowledge this confirmation without taking any actions yet.
╰────────────────────────────────────────────────────────
Agent: Workspace loaded. Awaiting instructions.
 [ think: 77 | ans: 13 | 90 tokens | 2.3s @ 36.9 t/s ]
 [ 577 in | 90 out | ctx: 8.1% ]
❯ 
```

---

## UI Box Themes

Switch box styles using `/box [1-5]` (or type `/box` to cycle). Selection persists in `~/.config/local-ai/.state.json`.

#### Style #1: Codex Rounded (Default)
```console
╭─  >_ Local-AI Agent  ─────────╮
│     model:  Qwen3.5-2B.gguf   │
│ directory:  ~                 │
│     skill:  chat              │
│  database:  stateless         │
╰────────────── Ctrl+C to exit ─╯
```

#### Style #2: Double Border
```console
╔═  ❖ Local-AI Agent  ══════════╗
║     model:  Qwen3.5-2B.gguf   ║
║ directory:  ~                 ║
║     skill:  default           ║
║  database:  stateless         ║
╚══════════════ Ctrl+C to exit ═╝
```

#### Style #3: Heavy Square
```console
┏━  ❖ Local-AI Agent  ━━━━━━━━━━┓
┃     model:  Qwen3.5-2B.gguf   ┃
┃ directory:  ~                 ║
┃     skill:  default           ║
┃  database:  stateless         ║
┗━━━━━━━━━━━━━━ Ctrl+C to exit ━┛
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

All auto-created agent metadata files are strictly isolated inside `project/.agent/` to keep project workspaces completely clean.

| Path | Purpose |
| :--- | :--- |
| `~/.config/local-ai/projects/database/*.db` | Global SQLite turn history and fact memory database. |
| `~/.config/local-ai/.active_sessions/` | Sub-agent PID lockfiles for process tracking. |
| `~/.config/local-ai/.spend_ledger.json` | Global cloud API token usage and daily spend ledger. |
| `~/<workspace>/.agent/config.json` | Default workspace agent profile and YOLO settings. |
| `~/<workspace>/.agent/tpm.md` | Human-editable Markdown fact memory store. |
| `~/<workspace>/.agent/history.md` | Chronological session history log. |
| `~/<workspace>/.agent/index-map-<project>.txt` | Shorthand codebase index map (Agent mode). |
| `~/<workspace>/.agent/index-map-memory-<project>.db` | Relational knowledge graph & `sqlite-vec` embeddings. |

---

## 2. Profile Selector (`ai init`)

Running `ai init <path>` sets default workspace agent profile:

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
│  /py                         - Toggle IPython (exec_python)         │
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

## 4. Checkpoints & Save States

- **Save:** `-save <tag>` — Snapshot session state to SQLite.
- **Load:** `-load` — Restore or clone session checkpoint across workspaces.

---

## 5. Local RAG & Context Injection

- **Whole File:** `view file <path>` — Append entire file into context.
- **Targeted Symbol:** `read function <symbol>` — Inject specific AST function/class block (saves 95% tokens).

---

## 6. Codebase Graph Mapper

The codebase intelligence engine features **dual-mode output routing**:

- **Agent Mode (`ai init` / `/sync`):** Outputs map files directly to `project/.agent/` to keep source directories clean.
- **Standalone CLI Mode (`index-map`):** Outputs map files to the project root directory when run independently in shell.
- **AST Graph:** Maps classes, methods, and call-chains across Python, Rust, Go, JS/TS, C/C++, Lua.
- **Vector Search:** Embeds codeblocks into `sqlite-vec` virtual tables for semantic retrieval.

---

## 7. Temporal Personality Memory (TPM)

- **Async Fact Extraction:** Auto-extracts user preferences in background thread after each turn.
- **Strict Fact Filtering:** Key blacklisting prevents project files/code from contaminating user memory.
- **Context Injection:** Compiles and injects facts into model `<context>` blocks every turn.
- **Human-Editable Sync:** Reconciles manual edits in `.agent/tpm.md` into SQLite on startup.

---

## 8. Sub-Agents & Concurrency

- **Process Badges:** Assigns sequence IDs (`[sub-agent #1]`, `[sub-agent #2]`) for parallel terminals.
- **Self-Healing Registry:** Auto-purges stale PID lockfiles (`.active_sessions/`) on exit or crash.
- **SQLite Lock Protection:** `PRAGMA busy_timeout = 5000` + `WAL` mode eliminates multi-agent database locks.
- **Unix Socket IPC:** Async socket hub (`/tmp/local-ai-<workspace>.sock`) for cross-terminal status messaging.

---

## 9. Security & Execution Isolation

- **Read-Only Default:** Workspace edits require explicit `ai init` enablement.
- **Directory Lock:** Enforces confirmation gates for paths outside project root.
- **Visual Diffs:** Shows colorized diffs prior to file writes.

---

## 10. Autonomous Task Loops (Ralph Engine)

Self-directed iterative `while` execution loop that runs tools and verifies results until the task is complete.

- **Inline Command:** `/task "Fix syntax errors in broken_syntax.py and run pytest"`
- **Spec File Mode:** Create `TASK.md` in project root and run `/task`
- **Auto-Completion:** Loops automatically until the model outputs `TASK COMPLETE` or turn limit finishes.
- **Customize:** Ralph loop script `.py` file in `~/.config/local-ai/tools/loop/ralph.py`.

---

## 11. IPython Kernel Harness (`/py`)

Replaces discrete JSON tools with a single live Python kernel. Loaded files and variables stay in kernel memory, saving up to 90% context tokens.

- **Toggle On/Off:** Type `/py` (or `/ipython`).
- **Usage:** The agent writes and executes Python code inside `exec_python(code)`.
- **Built-in SDK:** `read_file()`, `write_file()`, `list_dir()`, `run_command()`, `read_symbol()`.
- **Data Isolation:** Large files/datasets are inspected via Python scripts (`import re`, `import ast`, `import json`) in memory without bloating the LLM context window.

---

## 12. Context Limits

Override max context token limits:
```bash
AI_MAX_TOKENS=16000 ai init ~/my-project
```
