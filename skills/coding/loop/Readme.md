> TESTING ALPHA DRAFT (WIP) (Early Concepts & Prototypes)

### Core Use Case: Automated Intent Production
The primary purpose of the `triangle-loop` is **Automated Intent Production**—translating raw, highly vague, or unpolished human engineering ideas and rough draft scripts into production-ready, highly optimized, and logically verified code. 

By utilizing a progressive disclosure of complexity, the loop ensures that heavy token and compute resources are only spent *after* you have verified and locked in the architectural design, keeping execution fast, cheap, and strictly aligned with your goals.

---

--- Loop 1

### 1. The Unified `triangle-loop` Visual Workflow

```text
  [ HUMAN INTENT / DRAFT ]
             │
             ▼
  ┌──────────────────────────────┐
  │  Ultra-Lite-Router (ULR)     │ ──> [0-Cost Search] ──> Selects Specialty Skill Card
  └──────────────────────────────┘
             │ (Injects Skill + Context)
             ▼
  ┌──────────────────────────────┐
  │  PASS 1: The General Sketch  │ ──> Generates Low-Token Structural Blueprint
  └──────────────────────────────┘
             │
             ▼
   [ USER CONSENT GATE #1 ] ───────> [ABORT / TWEAK] ──> (Rerun Pass 1 / Exits with 0 cost)
             │
             ├─▶ [APPROVE]
             ▼
  ┌──────────────────────────────┐
  │  PASS 2: Code Refactoring    │ ◄─────────────────────────┐
  └──────────────────────────────┘                           │
             │                                               │
             ▼                                               │ (FAIL Loop - Max 3 Runs)
  ┌──────────────────────────────┐                           │
  │  PASS 2: Review & Audit      │ ──> [Self-Correction] ────┘
  │       (The Judge Gate)       │
  └──────────────────────────────┘
             │
             ├─▶ [PASS]
             ▼
   [ USER CONSENT GATE #2 ] ───────> [ABORT] ──> (Exits with audited draft preserved)
             │
             ├─▶ [APPROVE]
             ▼
  ┌──────────────────────────────┐
  │  PASS 3: Simplify & Ship     │ ──> Strips Logic Bloat ──> [Clipboard Copy (wl-copy)]
  └──────────────────────────────┘
```

---

### 2. Architectural Step Breakdown

#### Pass 1: The General Sketch (Low-Token Blueprint)
* **What it does:** Ingests your raw intent or draft script. Instead of immediately writing massive codeblocks, it utilizes a lightweight framing skill to generate a high-level **structural blueprint** of the proposed solution.
* **Why it works:** Because generating a layout takes very few tokens (~150–200 tokens), it minimizes CPU execution time and protects your free-tier request limits. You get an immediate architectural "best guess" from the model before committing to a heavy generation pass.
* **Human-in-the-Loop Interactivity:** You review the layout. If the AI misunderstood your architecture, you either abort with zero wasted heavy tokens, or type a simple feedback tweak to instantly regenerate a corrected blueprint.

#### Pass 2: Code Refactoring & Loop Auditing (The Sovereign Gate)
* **What it does:** Once you approve the Pass 1 blueprint, the loop escalates to heavy computation. It builds the full script, then automatically passes that script to an isolated **Review & Audit Judge**.
* **Why it works:** The Judge uses strict constraints (checking for memory leaks, error-handling vectors, and logical syntax flaws). 
* **The Self-Correction Loop:** If the Judge returns a `FAIL` verdict, the orchestrator intercepts the failure checklist, automatically appends it as corrective instructions to the history stack, and triggers a rebuild. The human is never shown the broken code; the loop automatically self-heals in the background (up to 3 times) until the Judge outputs a `PASS`.

#### Pass 3: Simplify & Ship (The Aesthetic Polish)
* **What it does:** Takes the passed, functionally correct script from Pass 2 and applies an aggressive minification and polishing pass.
* **Why it works:** It strips out dead variables, redundant conditional blocks, and bloated imports. It optimizes variables for readability and execution speed.
* **Final Output:** It outputs only the clean, execution-ready code block directly to your terminal and automatically copies it to your Wayland clipboard using `wl-copy`.

---

--- Loop 2

### The 3-Pass "Senior Engineer" Pipeline Architecture

Instead of a heavy multi-agent graph, we construct a lightweight pipeline using three targeted skills:

```text
Draft Script ──> [Pass 1: Plan & Build] ──> [Pass 2: Review & Audit (Judge)] ──> [Pass 3: Simplify & Ship] ──> Final Publication Script
                         ▲                                │
                         └─────────── (FAIL Loop) ────────┘
```

### How Your Proposed 3-Pass Architecture Operates

This layout maps your progressive refinement design cleanly to your manual, human-controlled philosophy:

```text
Draft Idea ──> [Pass 1: General Sketch] ──> [USER GATE: Approved?] ──> [Pass 2: Specialty Router + User Inputs] ──> [Pass 3: Deep Compile] ──> Final Draft
                                                    │
                                                    └── (Abort - 0 Wasted Tokens)
```

### The Architecture of the "Ultra-Lite-Router" (ULR)

A branching tree map of highly specific sectors is incredibly elegant and perfectly fits your manual, human-in-the-loop philosophy:

```text
               ┌──> [TUI Design] ────> [ANSI Color Palettes] (Skill Card)
               │
  [Coding] ────┼──> [Database] ──────> [SQLite Memory Tuning] (Skill Card)
               │
               └──> [Bash Script] ───> [Zsh Signal Trapping] (Skill Card)
```

#### How to Route Across 100+ Skills for 0 Tokens

If you used an LLM to read your prompt and decide which of the 100 skills to load, you would waste a precious free-tier request on every single run. Instead, your ULR can route across 100 folders using two **zero-cost local methods**:

#### Method A: Interactive TUI Progressive Disclosure (The Manual King)
Since your agent is designed for strict human control, your script can display an instantaneous, nested interactive terminal menu. You run your tool, and the script displays a clean, low-overhead menu:

```text
Select Engineering Specialty:
 ❯ [1] Coding
   [2] System Operations
   [3] Business/Strategy

   (You press 1)

 Select Target Sub-Skill:
   [1] Python TUI Layouts (~/skills/coding/tui-layouts.md)
 ❯ [2] Bash Async Subprocesses (~/skills/coding/bash-async.md)
   [3] SQLite Performance (~/skills/coding/sqlite-perf.md)
```

#### Step 1: Ingest Intent
You launch the tool: `ai route`. It prompts you with a clean, centered text bar:
`[ULR] Describe your active intent: ` 
You type: `"optimize database query speed"`

#### Step 2: Zero-Cost Local Search
Your script immediately walks your `skills/` directory and reads the first 2 lines (headers/metadata) of your 100+ files [2.1]. 
* It runs your local `jaccard_search` algorithm comparing your typed intent against the headers/keywords of all your files [1].
* It builds a score map of the most relevant skill cards.

#### Step 3: Render the Highlighted Grid (The Selector)
The TUI renders a categorized grid of your skills. The files that scored high on the Jaccard search are highlighted in green/blue, while the rest remain in dim grey. 

```text
 ── INTENT FOCUS: "optimize database query speed" ──────────────────────────────
 
  📁 Coding             📁 Systems             📁 Identity
  [ ] tui.md            [ ] sysop.md           [ ] mybiz.md
  [ ] refactor.md       [ ] secaud.md          [ ] routine.md
 🌟 [ ] sqlite-perf.md  [ ] aur-audit.md       [ ] strategy.md
  [ ] bash-async.md     [ ] harden.md          [ ] notes.md
  
 ───────────────────────────────────────────────────────────────────────────────
  ❯ Use Arrows [▲▼◀▶] to navigate | [Enter] to Compile & Copy to Clipboard
```

#### Step 4: The Human Decision & Compilation
* You can let the cursor auto-jump to the top highlighted recommendation, or you can manually arrow over to override it.
* When you press `Enter` on `sqlite-perf.md`, the Python script:
  1. Loads the content of `skills/coding/sqlite-perf.md` [2.1].
  2. Stitches it with your original intent and your local repository context/skeleton map [1, 2.1].
  3. Copies the entire compiled system prompt to your clipboard using `wl-copy`.
  4. Flashes a quick notification: `[sys] Structured prompt compiled & copied to clipboard. Ready to paste.`

### The Verdict
This Directional TUI acts as an incredibly smart, local, zero-latency interface. It keeps your terminal clean, uses **zero** API requests, forces you to hone your intentions into precise niches, and gives you total, sovereign control over how you feed your context to both local models and heavy cloud models. It is a highly optimized, elegant workflow.

---

--- loop 3

Highlights the current paradigm shift in AI systems engineering: **you stop writing prompts, and you start writing loops.** 

The model writing the code cannot be the one grading it, and that a separate, independent "Judge" must enforce quality gates—is exactly what is designed into the **`coding-triangle-loop`**.

By applying **ultra-lite, 3-pass, human-in-the-loop** philosophy to the concepts, we can extract three specific, high-value architectural optimizations that will significantly improve the execution of the current loop.

---

### Optimization 1: The Cross-Boundary Hybrid Loop (Local Doer, Cloud Judge)

*“The loop holds the line... You could have a frontier model checking the work and cheaper or free models actually doing the work itself.”*

* **The Problem:** Running massive, multi-turn code refactoring entirely on Gemini Flash Lite consumes your free-tier request quota quickly, but running it entirely on Qwen/local can sometimes result in loose code formatting or missing logic.
* **The Ultra-Lite Solution:** You can split your API targets inside the script:
  * **Pass 1 (The Sketch):** Executed locally on **Qwen/local** (instant, free, low token cost).
  * **Pass 2: Code Refactor (The Doer):** Executed locally on **Qwen/local** at 12-120 t/s (completely free, zero memory pressure, writes the bulk lines).
  * **Pass 2: The QA Audit (The Judge):** Executed on **Gemini 3.5 Flash** (/fallbacks)(free cloud, zero-bias, highly pedantic).
* **Why it wins:** This is the ultimate hybrid optimization. The local model does 90% of the long-text, heavy-lifting code generation, while your highly intelligent cloud model only steps in to read, evaluate, and provide precise, targeted corrections. You get GPT-4/Gemini-grade verification while keeping your cloud request footprint virtually non-existent.

---

### Optimization 2: The Evolving `.ai_memory` (Lite-Memory Logging)

Highlights how agents operate in a positive feedback loop by logging outputs to an "Obsidian Galaxy" database, letting subsequent runs pull from past context automatically.

* **The Problem:** You do not want heavy databases, network syncs, or Obsidian integrations bloating your local agent.
* **The Ultra-Lite Solution:** Implement a localized, hidden **`.ai_memory`** file.
  * When `coding-triangle-loop` finishes a successful run and copies the final code to your clipboard, it appends a single, ultra-dense, 1-line log entry to a hidden `.ai_memory` file in the project's root folder:
    `[2026-06-22] Refactored backup-monitor daemon using syslogs and signal traps.`
  * The next time you run `coding-triangle-loop` in that directory, the script's Pass 1 automatically reads this tiny `.ai_memory` file (which is only 3–5 lines of text) and appends it to your prompt.
* **Why it wins:** No databases. No bloat. Your local agent gains instant **episodic memory** of what it did in past sessions, ensuring it respects and builds on top of its previous code designs without breaking them on subsequent refactors.

---

### Optimization 3: AST-Driven "Stealth Routing" (The 0-Cost Specialty Injector)

Using a "Planner" or a "Kanban Board" of agents to triage and route tasks before they begin.

* **The Problem:** We want to load highly specific local skill cards (like your `skills.md`, or `sqlite-perf.md`) to guide the code generation, but having an LLM read the draft and choose the skill costs a request.
* **The Ultra-Lite Solution:** Use basic, local Python regex scanning inside `coding-triangle-loop` to auto-route specialties based on imports and syntax:
  * Before starting Pass 1, the Python script scans your raw draft code for specific keywords:
    * If it detects `import sqlite3`, it automatically loads and appends `sqlite-perf.md` [2.1].
    * If it detects `import termios` or `\033[`, it automatically loads `tui.md` [1, 2.1].
    * If it detects `import signal` or `subprocess`, it automatically loads `bash-async.md` or a systems engineering skill card [1, 2.1].
* **Why it wins:** It costs exactly **0 tokens, 0 cents, and 0 requests** to route. Your Python script programmatically auto-detects the tech stack and injects the exact, highly specific system guidelines into Pass 2's build prompt, guaranteeing senior-grade output with zero manual setup.

---

### Summary
By applying these three patterns, you don't need a heavy "Agent Operating System" or complex Kanban boards. Your lightweight Python script remains a single file, but it gains:
1. **The security of a hybrid model boundary** (cheap local generation, smart cloud validation).
2. **Local, project-level episodic memory** (via `.ai_memory` logs).
3. **Automatic, zero-cost task specialization** (via local regex routing).

