### TESTING ALPHA DRAFT (WIP) (Early Concepts & Prototypes)

### Core Use Case: Automated Intent Production
The primary purpose of the `triangle-loop` is **Automated Intent Production**—translating raw, highly vague, or unpolished human engineering ideas and rough draft scripts into production-ready, highly optimized, and logically verified code. 

By utilizing a progressive disclosure of complexity, the loop ensures that heavy token and compute resources are only spent *after* you have verified and locked in the architectural design, keeping execution fast, cheap, and strictly aligned with your goals.

---

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
