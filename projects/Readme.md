# Local-AI Agent Workspace & Session Manual

High-speed local developer agent, episodic memory, SQLite checkpoints, and codebase index graph.

```console
~ ❯ session
[01/03] ❯ [session test] ai init ~/session-test --init
:: ↵ run  Esc: 
╭─  ❖ Local-AI Agent  ───────────────────────────────────╮
│     model:  Hermes3.6-35B-A3B.gguf                     │
│ directory:  ~/.config/local-ai/projects/session-test   │
│     skill:  hermes/pro                                 │
│  database:  active (0 facts, 0 turns)                  │
╰─────────────────────────────────────── Ctrl+C to exit ─╯
 Startup context: 418 tokens

╭─ ⚙ Thinking Process ──────────────────────────────────────────
The user provided a codespace map without a task. According to Rule 1, acknowledge workspace in 1 
brief sentence and standby.
╰───────────────────────────────────────────────────────────────

Agent: Hermes Agent initialized at `/home/user/.config/local-ai/projects/session-test` — standing by.

 [ think: 58 | ans: 22 | 80 tokens | 3.6s @ 28.1 t/s ]
 [ 1315 in | 80 out | ctx: 17.0% ]
❯ 
```
---

## UI Box Themes

Switch box styles using `/box [1-5]` (or type `/box` to cycle). Selection persists in `~/.config/local-ai/.state.json`.

#### Style #1: Double Border (Default)
```console
╔═  ❖ Local-AI Agent  ══════════╗
║     model:  Hermes3.6-35B     ║
║ directory:  ~                 ║
║     skill:  default           ║
║  database:  stateless         ║
╚══════════════ Ctrl+C to exit ═╝
```

#### Style #2: Codex Rounded
```console
╭─  >_ Local-AI Agent  ─────────╮
│     model:  Hermes3.6-35B     │
│ directory:  ~                 │
│     skill:  default           │
│  database:  stateless         │
╰────────────── Ctrl+C to exit ─╯
```

#### Style #3: Heavy Square
```console
┏━  ❖ Local-AI Agent  ━━━━━━━━━━┓
┃     model:  Hermes3.6-35B     ┃
┃ directory:  ~                 ┃
┃     skill:  default           ║
┃  database:  stateless         ║
┗━━━━━━━━━━━━━━ Ctrl+C to exit ━┛
```

#### Style #4: Minimalist Line
```console
 ─  Local-AI Agent  ──────────── 
      model:  Hermes3.6-35B      
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
│     model:  Hermes3.6-35B     │
│ directory:  ~                 │
│     skill:  default           │
│  database:  stateless         │
╰────────────── Ctrl+C to exit ─╯
```

---

## 1. Directory Structure

| Path | Purpose |
| :--- | :--- |
| `~/.config/local-ai/projects/database/*.db` | SQLite turn and memory database. |
| `~/.config/local-ai/.active_sessions/` | Sub-agent PID lockfiles. |
| `~/.config/local-ai/.spend_ledger.json` | Token usage ledger. |
| `~/<workspace>/.agent/session.json` | Cloud API interaction tracking. |
| `~/<workspace>/.agent/tpm.md` | Human-editable Markdown memory facts. |
| `~/<workspace>/index-map-<project>.txt` | Shorthand codebase index map. |
| `~/<workspace>/index-map-memory-<project>.db` | Relational knowledge graph & `sqlite-vec` embeddings. |
| `~/<workspace>/history.md` | Chronological multi-agent session log. |

---

## 2. Profile Selector (`ai init`)

Running `ai init <path>` prompts the default workspace agent profile:

```console
[ai init] Select default Agent Profile for workspace session-test:

  ─── Standard ────────────────────────────────────────────────────────
     1. Default Assistant    (~120t | Standard assistant)

  ─── Full Tier (Direct Action / Large Models) ────────────────────────
     2. Pi Agent             (~400t | Direct tool prompt)
     3. Claude Code          (~440t | Direct tool prompt)
     4. Hermes Agent         (~380t | Direct tool prompt)

  ─── Pro Tier (Index-First / 35B+ & Cloud) ───────────────────────────
     5. Pi Pro               (~280t | Index-first + reasoning prompt)
     6. Claude Pro           (~290t | Index-first + reasoning prompt)
  ❯  7. Hermes Pro           (~280t | Index-first + reasoning prompt)

  ─── Lite Tier (Index-First / 1B–7B Models) ───────────────────────────
     8. Pi Lite              (~220t | Index-first standby prompt)
     9. Claude Lite          (~230t | Index-first standby prompt)
    10. Hermes Lite          (~220t | Index-first standby prompt)

  :: ↵ select  ↑/↓ navigate  Tab: YOLO [OFF]  Esc: default
```

#### Profile Tiers

| Tier | Profiles | Scale | Overhead | Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Standard** | `default` | Any | `~120t` | General assistant without workspace tool loops. |
| **Full** | `pi/full`, `claude/full`, `hermes/full` | 35B+ / Cloud | `~380t–440t` | Direct multi-file action and editing loops. |
| **Pro** | `pi/pro`, `claude/pro`, `hermes/pro` | 35B+ / Cloud | `~280t–290t` | Index-first mapping + standby rule + reasoning (`/t`). |
| **Lite** | `pi/lite`, `claude/lite`, `hermes/lite` | 1B–7B Local | `~220t–230t` | Index-first standby preventing tool-eagerness loops. |

* **Reset Workspace Profile:** Delete `.agent/config.json` inside the project folder (`rm .agent/config.json`).

---

## 3. Command Reference

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

## 4. Checkpoints & Save States

- **Save:** `❯ -save <tag>` — Snapshot session state to SQLite.
- **Load:** `❯ -load` — Restore or clone session checkpoint across workspaces.

---

## 5. Local RAG & Context Injection

- **Whole File:** `❯ view file <path>` — Append entire file into context.
- **Targeted Symbol:** `❯ read function <symbol>` — Inject specific AST function/class block (saves 95% tokens).

---

## 6. Codebase Graph Mapper

- **AST Graph:** Maps classes, methods, and call-chains across Python, Rust, Go, JS/TS, C/C++, Lua.
- **Vector Search:** Embeds codeblocks into `sqlite-vec` virtual tables for semantic retrieval.

---

## 7. Temporal Personality Memory (TPM)

- **Async Fact Extraction:** Auto-extracts facts in background thread after turns.
- **Sync:** Auto-syncs manual edits in `.agent/tpm.md` into SQLite on startup.

---

## 8. Sub-Agents & Concurrency

- **Process Badges:** Assigns sequence IDs (`[sub-agent #1]`, `[sub-agent #2]`) for parallel terminals.
- **SQLite WAL:** Prevents write-lock contention across concurrent instances.

---

## 9. Security & Execution Isolation

- **Read-Only Default:** Workspace edits require `ai init`.
- **Directory Lock:** Enforces confirmation gates for paths outside project root.
- **Visual Diffs:** Shows colorized diffs prior to file writes.

---

## 10. Context Limits

Override max context token limits:
```bash
AI_MAX_TOKENS=16000 ai init ~/my-project
```
