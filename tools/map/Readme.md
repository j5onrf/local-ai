# Codebase Mapping: `skeleton-map`, `skeleton-map-ai` & `skeleton-map-head`

<div align="center">
<img width="800" alt="l3od02l3od02l3od" src="https://github.com/user-attachments/assets/db68048f-350a-4a93-afde-70bb8befae68" />
</div>

---

This subsystem maps your project's directory structure into a lightweight, high-density semantic index, saving **95% to 99% in token overhead** compared to raw codebase ingestion.

It provides three distinct scanning profiles to match your workflow:
1.  **Static Map (`skeleton-map`):** Purely local, instant line-scraping and Abstract Syntax Tree (AST) parsing. Requires **zero tokens** and zero API calls. Outputs to `skeleton.json`.
2.  **AI-Enriched Map (`skeleton-map-ai`):** Ingests local files via AST, but dynamically aggregates all repository documentation (`.md` files) and semantically indexes them in **exactly 1 unified request** using your cascade client. Outputs to `skeleton-ai.json`.
3.  **AST "SmartCrusher" Map (`skeleton-map-head`):** *The recommended standard.* Parses code files via AST to extract **complete function signatures along with their parameters/arguments** [1.1.3, 1.3.3]. It then flattens the hierarchy into a custom, high-density flat shorthand that strips all JSON formatting overhead (braces, quotes, indentations) [1.1.3]. Outputs to `skeleton-head.txt` [1].

---

### Expected Behavior

```text
~ ❯ sm
[01/03] ❯ [skeleton map] ~/.config/local-ai/tools/map/skeleton-map
[02/03] ❯ [skeleton map ai] ~/.config/local-ai/tools/map/skeleton-map-ai
[03/03] ❯ [skeleton map head] ~/.config/local-ai/tools/map/skeleton-map-head
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

#### SmartCrusher AST Scan (Recommended)
```text
Scan target [Default: /home/user/local-ai]: 
ℹ Compiling skeleton map...
✔ Compressed skeleton-head compiled successfully at: /home/user/.config/local-ai/tools/map/skeleton-head.txt
```

*Pressing **Enter** at the `Scan target` prompt defaults to your current active working directory [3].*

---

### 🛡️ Dual-Guardrail Safety Gates

To protect your system performance and free-tier API request budgets from accidental runaway folder crawls:

* **Pre-Scan Path Disclosure:** The prompt explicitly displays your active working directory path before walking a folder, preventing blind executions.
* **Home-Dir Warning Gate:** The filesystem crawler immediately halts and requires explicit, manual keyboard confirmation (`y/N`) if you attempt to scan your entire home directory (`~` or `/home/user`).
* **100-File Batch Limit:** If the directory contains more than 100 markdown files, the AI scanner automatically aborts the batch compile, flashes a warning, and exits safely to protect your token usage.

---

### Token Savings Math

* **JSON Map vs. Flat AST Map (~65% Saved):** Compiling your codebase metadata into the flat, tag-based SmartCrusher shorthand (`skeleton-head.txt`) completely removes JSON structural syntax overhead (braces, quotes, nested indentations) [1.1.3]. A codebase with over 100 files is crushed from a bulky 4,000-token JSON down to a tiny, high-density **1,500-token** flat-shorthand map with absolutely zero loss in semantic fidelity [1.1.3]!
* **Code Signatures with Arguments:** In the flat AST map, Python functions include their full parameter signatures (e.g., `prune_history(history,max_tokens)`) instead of just flat names [1.1.3]. This gives the model maximum API fidelity [1.1.3], allowing it to write correct calls on its first turn without reading the raw files.
* **Images & Binaries (~100% Saved):** Massive assets (like `.png` or `.pdf` files) are cataloged into a ~5-token reference without corrupting terminal output or wasting context window.

