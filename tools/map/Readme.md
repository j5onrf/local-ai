# Codebase Mapping: `skeleton-map` & `skeleton-map-ai`

This subsystem maps your project's directory structure into a lightweight, high-density semantic index, saving **95% to 99% in token overhead** compared to raw codebase ingestion.

It provides two distinct scanning profiles to match your workflow:
1. **Static Map (`skeleton-map`):** Purely local, instant line-scraping and Abstract Syntax Tree (AST) parsing. Requires **zero tokens** and zero API calls. Outputs strictly to `skeleton.json`.
2. **AI-Enriched Map (`skeleton-map-ai`):** Ingests local code files via AST, but dynamically aggregates all repository documentation (`.md` files) and semantically indexes them in **exactly 1 unified API request** using your central `call_service` cascade client. Outputs strictly to `skeleton-ai.json`.

---

### Expected Behavior

```text
~ ❯ sm
[01/02] ❯ [skeleton map] ~/.config/local-ai/tools/map/skeleton-map
[02/02] ❯ [skeleton map ai] ~/.config/local-ai/tools/map/skeleton-map-ai
:: ↵ run  Esc: 
```

#### Static Scan
```text
Scan target [Default: /home/user/local-ai]: 
ℹ Compiling skeleton map...
✔ Skeleton map compiled successfully at: /home/user/.config/local-ai/tools/map/skeleton.json
```

#### AI-Enriched Scan
```text
Scan target [Default: /home/user/local-ai]: 
ℹ Compiling skeleton map...
ℹ Loaded 9 rules from .gitignore.
[sys] Semantically indexing 37 markdown files in a single unified batch...
✔ Skeleton map compiled successfully at: /home/user/.config/local-ai/tools/map/skeleton-ai.json
```

*Pressing **Enter** at the `Scan target` prompt defaults to your current active working directory.*

---

### 🛡️ Dual-Guardrail Safety Gates

To protect your system performance and free-tier API request budgets from accidental runaway folder crawls (e.g., scanning a bloated home directory or system root):

* **Pre-Scan Path Disclosure:** The prompt explicitly displays your active working directory path before walking a single folder, preventing blind executions.
* **Home-Dir Warning Gate:** The filesystem crawler immediately halts and requires explicit, manual keyboard confirmation (`y/N`) if you attempt to scan your entire home directory (`~` or `/home/user`).
* **100-File Batch Limit:** If the directory contains more than 100 markdown files, the AI scanner automatically aborts the batch compile, flashes a warning, and exits safely to protect your token usage, directing you to scan a specific project subdirectory instead.

---

### Token Savings Math

* **Code (~98% Saved):** A 400-line Python file (~3,000 tokens) is reduced to a ~50-token JSON outline of imports, classes, and function structures.
* **Configs, Text & Shell (~99% Saved):** A 1,500-token Shell script or YAML configuration file is reduced to a ~15-token first-line summary.
* **Images & Binaries (~100% Saved):** Massive assets (like `.png` or `.pdf` files) are cataloged into a ~5-token reference without corrupting terminal output or wasting context window.
* **AI-Enriched Map vs. Static Map (~500 Tokens Difference):** Loading `skeleton-ai.json` into your central agent's active context window uses only about 500 more tokens than the static `skeleton.json`, but provides 100% accurate, high-density semantic explanations of every single custom tool and skill in your codebase.

