# Local-AI Agent Workspace & Session Manual

High-speed local developer agent, episodic memory, SQLite checkpoints, and codebase index graph.

```console
~ ❯ sess
[01/03] ❯ [session test] ai init ~/session-test --init
:: ↵ run  Esc: 
╭─  >_ Local-AI Agent [sub-agent #1]  ───────────────────╮
│     model:  LFM2.5-8B-A1B.gguf                         │
│ directory:  ~/.config/local-ai/projects/session-test   │
│     skill:  hermes/pro                                 │
│  database:  active (0 facts, 25 turns)                 │
╰─────────────────────────────────────── Ctrl+C to exit ─╯
 Startup context: 845 tokens
╭─ ⚙ ────────────────────────────────────────────────────
The user has sent a notification that workspace is initialized and they're standing by for instructions.
According to the system prompt, we should reply only with: "Workspace 
loaded. Awaiting instructions." No additional commentary. So I will respond accordingly.
╰────────────────────────────────────────────────────────
Agent:
Workspace loaded. Awaiting instructions.                                     
 [ think: 75 | ans: 14 | 89 tokens | 1.4s @ 61.8 t/s ]
 [ 1027 in | 89 out | ctx: 13.6% ]
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
[ai init] Agent Profile: session-test

  Standard
     1. Default Assistant    ~120t

  Full Tier (Direct Action)
     2. Pi Full              ~400t
     3. Claude Full          ~440t
     4. Hermes Full          ~380t

  Pro Tier (Index-First)
     5. Pi Pro               ~280t
     6. Claude Pro           ~290t
  ❯  7. Hermes Pro           ~280t

  Lite Tier (1B+)
     8. Pi Lite              ~220t
     9. Claude Lite          ~230t
    10. Hermes Lite          ~220t

  ↵ select  ↑/↓ navigate  Tab: YOLO [OFF]  Esc: default
```

#### Profile Tiers

| Tier | Profiles | Model Scale | Overhead | Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Standard** | `default` | Universal | `~120t` | General assistant without workspace tool loops. |
| **Full** | `pi/full`, `claude/full`, `hermes/full` | Large Models | `~380t–440t` | Direct multi-file action and editing loops. |
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

## 11. Context Limits

Override max context token limits:
```bash
AI_MAX_TOKENS=16000 ai init ~/my-project
```
