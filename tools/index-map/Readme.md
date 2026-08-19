# Codebase Mapping & Relational Knowledge Graph: `index-map`

Maps codebase structure into a flat shorthand index (`.txt`) and a parallel SQLite relational graph (`.db`), cutting token ingestion by **95% to 99%**.

* **AST & Shebang Parser:** Full AST for Python (including extensionless scripts via `#!` shebang) + regex state machines for Rust, Go, JS/TS, Lua, and C/C++.
* **Hybrid Semantic Graph:** Embeds codeblocks into `sqlite-vec` virtual tables with fallback to relational SQLite call/inheritance trees.
* **Dual Output Routing:** Saves directly to `.agent/` in workspace mode (`--agent`) or project root in standalone mode.

---

## CLI Usage

#### Standalone Project Mapping
```console
# Option 1: cd into directory and map
cd /path/to/project && index-map

# Option 2: Map any directory from anywhere
index-map /path/to/project
```

#### Graph & Symbol Commands
```console
index-map architecture       # Overview of files, classes, functions & call count
index-map search <pattern>   # Substring or vector semantic search
index-map trace <symbol>     # Call tree (callers & callees)
index-map blast-radius <sym> # Upstream breaking-change dependency tree
index-map snippet <symbol>   # Extract exact source block via cached line offsets
index-map query "<SQL>"      # Direct SQLite graph queries
```

---

## Agent Tool Integrations

| Intent Command | Agent Tool | Action |
| :--- | :--- | :--- |
| `architecture overview` | `architecture_overview` | Structural summary of codebase |
| `read function <sym>` | `read_symbol` | Ingests only the target function/class block |
| `trace symbol <sym>` | `trace_symbol` | Maps incoming callers & outgoing callees |
| `blast radius <sym>` | `blast_radius` | Traces upstream breaking risks (depth $\le$ 5) |
| `find symbol <pattern>` | `find_symbol` | Substring search or semantic vector retrieval |

---

## Token Efficiency

* **Snippets vs. Files (~95% Saved):** Ingests only the targeted 10-line block (~120 tokens) instead of the entire 11KB file (~2,750 tokens).
* **Flat Map vs. JSON (~65% Saved):** High-density tag shorthand (`[python:core] fn:...`) eliminates JSON syntax overhead.
* **Graph Tracing (~90% Saved):** Replaces multi-file grep scans with a direct 5-line structural call tree.
* **Asset Indexing (~100% Saved):** Catalogs images and binaries as 5-token metadata tags (`dim:1376x768 | size:1.0MB`).

