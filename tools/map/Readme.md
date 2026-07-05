# Codebase Mapping & Relational Knowledge Graph: `index-map`

---

This subsystem maps your project's directory structure into a lightweight, high-density shorthand index and parallel relational SQLite graph database, saving **95% to 99% in token overhead** compared to raw codebase ingestion.

*   **`index-map`** Dual-pass workspace analyzer. 
    *   **Pass 1**: Parses Python source code via AST (and other languages via high-performance structural regex profiles) to extract files, classes, function signatures with arguments, and line-offset boundaries. 
    *   **Pass 2**: Resolves dependencies and imports to build a relational database (`index-map-memory-{proj_name}.db`) mapping containment (`contains`) and call-chains (`calls`).
    *   **Output**: Compiles a flat tag-based shorthand (`index-map-{proj_name}.txt`) for immediate prompt context and a relational knowledge database. Runs 100% offline with zero dependencies and **0 token cost**.

---

### Expected Behavior

```text
~ ❯ index map
[01/01] ❯ [index map] ~/.config/local-ai/tools/map/index-map
:: ↵ run  Esc: 
```

#### Relational Graph & Shorthand AST Scan (Standard)
```text
[sys] Compile index map memory for session-test? [↵ run  Esc]: 
ℹ Compiling relational index graph...
✔ Compiled index-map: ~/projects/session-test/index-map-session-test.txt
✔ Created graph database: ~/projects/session-test/index-map-memory-session-test.db
```

*Pressing **Enter** at the target prompt defaults to scanning your current active working directory.*
*Pressing **Esc** (or `n`/`N`) at the confirmation gate bypasses compilation safely without crashing parent automation.*

---

### 🛡️ Dual-Guardrail Safety Gates

To protect your system performance and API request budgets from accidental runaway folder crawls:

*   **Pre-Scan Path Disclosure:** The prompt explicitly displays your active working directory path before walking a folder, preventing blind executions.
*   **Home-Dir Warning Gate:** The filesystem crawler immediately halts and requires explicit, manual keyboard confirmation (`y/N`) if you attempt to scan your entire home directory (`~` or `/home/user`).

---

### ⚙️ Human-in-the-Loop Silent Graph Queries

The system integrates directly with your active agent's prompt context. When you or your AI agent need to inspect workspace details, the agent suggests the correct trigger phrase to execute in the CLI:

*   `trace symbol <symbol>`: Resolves and traces the incoming callers and outgoing callees of a function or class.
*   `blast radius <symbol>`: Runs a recursive upstream BFS traversal to find all breaking risks if the symbol is modified.
*   `read function <symbol>`: Uses database line offsets to dynamically print the exact source code block of the target symbol.
*   `find symbol <pattern>`: Performs a rapid, low-level SQL lookup on the codebase index nodes.
*   `architecture overview`: Shows aggregate statistics of files, classes, functions, and relational edges in the workspace.

---

### Token Savings Math

*   **Targeted Snippets vs. Full File Ingestion (~95%+ Saved):** Reading a 10-line function inside an 11KB source file used to consume 2,750 tokens of file read context. Your agent can now run `read function`, fetching *only* the specific code block (roughly 120 tokens) and leaving your context window clean.
*   **JSON Map vs. Flat AST Map (~65% Saved):** Compiling codebase metadata into the flat, tag-based SmartCrusher shorthand completely removes JSON structural syntax overhead (braces, quotes, nested indentations). A codebase with over 100 files is crushed from a bulky 4,000-token JSON down to a tiny, high-density **1,500-token** flat-shorthand map with no loss in semantic fidelity.
*   **Call-Graph Tracing vs. Broad Greps (~90%+ Saved):** Tracing a call chain previously required reading several source files back-to-back. Relational tracing delivers a precise 5-line structural tree directly to the context, pinpointing targets instantly.
*   **Images & Binaries (~100% Saved):** Massive assets (like `.png` or `.pdf` files) are cataloged into a ~5-token reference without corrupting terminal output or wasting context window.

