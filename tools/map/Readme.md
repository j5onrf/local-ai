# Codebase Mapping & Relational Knowledge Graph: `index-map`

---

Maps your codebase directory structure into a lightweight, flat tag-based shorthand index (`.txt`) and a parallel SQLite relational graph database (`.db`). Reduces token ingestion overhead by **95% to 99%** with zero API token cost.

*   **Hybrid Semantic Search:** Integrates `sqlite-vec` (a zero-dependency, pure-C SQLite extension) to embed, index, and query your actual class and function codeblocks conceptually.
*   **Parser & Linker:** Statically parses Python source via AST (and Go, Rust, Lua, JS/TS, C/C++ via regex profiles) to map containment, block boundaries, imports, and call dependencies.
*   **Offline Compilation:** Runs entirely locally, offline, and with zero external dependencies (gracefully falling back to a standard relational database if `sqlite-vec` is missing).

---

### Expected Behavior

```text
~ ❯ index-map
[sys] Compile index map memory for session-test? [↵ run  Esc]: 
ℹ Probing local embedding server for dimensional limits...
✔ Active embedding model resolved (384 dimensions detected).
ℹ Compiling relational index graph...
✔ Compiled index-map: ~/projects/session-test/index-map-session-test.txt
✔ Created graph database: ~/projects/session-test/index-map-memory-session-test.db
```

*Pressing **Enter** targets the current active working directory; **Esc** (or `n`/`N`) safely cancels execution.*

---

### 🛡️ Dual-Guardrail Safety Gates

To protect your system performance and API request budgets from accidental runaway folder crawls:

*   **Pre-Scan Path Disclosure:** Displays target paths clearly before walking folders to prevent blind runs.
*   **Home-Dir Warning Gate:** Pauses and requires explicit keyboard confirmation (`y/N`) if attempting to scan your entire home directory (`~`).

---

### ⚙️ Human-in-the-Loop Graph & Semantic Queries

When the AI agent suggests a structural or conceptual query, execute the intent trigger inside your prompt. The agent will prompt you for authorization before executing the tool and injecting the target context:

*   `trace symbol <symbol>`: Resolves call-chains (incoming callers and outgoing callees).
*   `blast radius <symbol>`: Evaluates upstream breaking risks across the workspace.
*   `read function <symbol>`: Retrieves the exact source code block of a function or class.
*   `find symbol <pattern>` or `semantic search <concept>`: Performs rapid local substring searches or high-performance hybrid semantic matching using `sqlite-vec`.
*   `architecture overview`: Summarizes files, classes, functions, and relational counts.

---

### Token Savings Math

*   **Snippets vs. Files (~95%+ Saved):** Fetching a 10-line function block directly (roughly 120 tokens) replaces ingesting an entire 11KB source file (2,750 tokens).
*   **Flat Shorthand vs. JSON (~65% Saved):** Removing JSON syntax overhead (brackets, quotes, indents) compresses a 4,000-token project index to a high-density 1,500-token flat text map.
*   **Graph Tracing vs. Greps (~90%+ Saved):** Delivers a 5-line structural call tree directly to active context, replacing multi-file text search.
*   **Semantic Entrypoints (~99% Saved):** Resolves abstract conceptual questions (e.g. *"where do we handle audio pitch?"*) directly to a single codeblock, skipping brute-force codebase grepping entirely.
*   **Asset Ingestion (~100% Saved):** Catalogues massive assets (PNG, JPG, PDF) as tiny, 5-token metadata references.

