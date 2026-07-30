# Local-AI Agent Workspace & Session Manual

High-speed local developer agent, episodic memory, SQLite checkpoints, and codebase index graph.

```console
~ ❯ sess
[01/03] ❯ [session test] ai init ~/session-test --init
:: ↵ run  Esc: 
✔ Mapping complete! [session-test index-map & SQLite graph database updated]
╔═  ❖ Local-AI Agent  ═══════════════════════════════════╗
║     model:  Qwen3.6-35B-A3B.gguf                       ║
║ directory:  ~/.config/local-ai/projects/session-test   ║
║     skill:  hermes/pro                                 ║
║  database:  active (0 facts, 1 turns)                  ║
╚═══════════════════════════════════════ Ctrl+C to exit ═╝
 Startup context: 418 tokens

╭─ ⚙ Thinking Process ──────────────────────────────────────────
The user has provided a system prompt override and a CODESPACE MAP for the workspace `session-test`. 
No explicit user task or goal is provided in the conversation yet.

According to Execution Protocol #1: "Unprompted Initialization: If no explicit user task or goal is 
provided in the conversation, acknowledge the workspace in 1 brief sentence and standby for 
instructions."

I should simply acknowledge the workspace and wait for instructions. I will not execute any 
exploratory tool calls.
╰───────────────────────────────────────────────────────────────

Agent:
Hermes Agent initialized and ready at /home/j5/.config/local-ai/projects/session-test. Standing by 
for your task or instructions.                                                
 [ think: 138 | ans: 39 | 177 tokens | 4.8s @ 28.0 t/s ]
 [ 1471 in | 177 out | ctx: 20.1% ]
❯ 
```
---

## UI Box Themes

Switch box styles using `/box [1-5]` (or type `/box` to cycle). Selection persists in `~/.config/local-ai/.state.json`.

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
│     skill:  chat              │
│  database:  stateless         │
╰────────────── Ctrl+C to exit ─╯
```

#### Style #3: Heavy Square
```console
┏━  ❖ Local-AI Agent  ━━━━━━━━━━┓
┃     model:  Qwen3.5-2B.gguf   ┃
┃ directory:  ~                 ┃
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

Running `ai init <path>` set default workspace agent profile:

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
