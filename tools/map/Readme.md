# Codebase Mapping: `index-map` & `index-map-ai`

<div align="center">
<img width="800" alt="l3od02l3od02l3od" src="https://github.com/user-attachments/assets/db68048f-350a-4a93-afde-70bb8befae68" />
</div>

---

This subsystem maps your project's directory structure into a lightweight, high-density shorthand index, saving **95% to 99% in token overhead** compared to raw codebase ingestion.

*   **`index-map` (Recommended Standard):** Parses code files via AST to extract **complete function signatures along with their parameters/arguments**. It then flattens the hierarchy into a custom, high-density flat shorthand that strips all JSON formatting overhead (braces, quotes, indentations). For markdown files, it extracts the top title lines or headers locally, making the tool 100% offline and cost-free (**0 tokens**). Outputs to `index-map-{proj_name}.txt`.
*   **`index-map-ai` (Optional/Manual):** Identical directory and AST-based mapping as the standard tool, but routes markdown files in small batches of 5 to an LLM (Gemini 3.1 Flash Lite, falling back to OpenRouter or localhost) to write deep, 1-sentence architectural summaries. It uses more tokens but offers enhanced semantic details for documentation.

---

### Expected Behavior

```text
~ ❯ index map
[01/01] ❯ [index map] ~/.config/local-ai/tools/map/index-map
:: ↵ run  Esc: 
```

#### SmartCrusher AST Scan (Standard)
```text
[sys] Compile index map for session-test? [↵ run  Esc]: 
Scan target [Default: /home/user/projects/session-test]: 
ℹ Compiling index map...
✔ Compressed index-map compiled successfully at: /home/user/projects/session-test/index-map-session-test.txt
```

*Pressing **Enter** at the target prompt defaults to scanning your current active working directory.*
*Pressing **Esc** (or `n`/`N`) at the confirmation gate bypasses compilation safely without crashing parent automation.*

---

### 🛡️ Dual-Guardrail Safety Gates

To protect your system performance and free-tier API request budgets from accidental runaway folder crawls:

*   **Pre-Scan Path Disclosure:** The prompt explicitly displays your active working directory path before walking a folder, preventing blind executions.
*   **Home-Dir Warning Gate:** The filesystem crawler immediately halts and requires explicit, manual keyboard confirmation (`y/N`) if you attempt to scan your entire home directory (`~` or `/home/user`).
*   **100-Markdown Limit (`index-map-ai` only):** If the directory contains more than 100 markdown files, the AI-integrated scanner automatically aborts the compilation, flashes a warning, and exits safely to protect your token usage.

---

### Token Savings Math

*   **JSON Map vs. Flat AST Map (~65% Saved):** Compiling your codebase metadata into the flat, tag-based SmartCrusher shorthand (`index-map-{proj_name}.txt`) completely removes JSON structural syntax overhead (braces, quotes, nested indentations). A codebase with over 100 files is crushed from a bulky 4,000-token JSON down to a tiny, high-density **1,500-token** flat-shorthand map with no loss in semantic fidelity.
*   **Code Signatures with Arguments:** In the flat AST map, Python functions include their full parameter signatures (e.g., `prune_history(history,max_tokens)`) instead of just flat names. This gives the model maximum API fidelity, allowing it to write correct calls on its first turn without reading the raw files.
*   **Images & Binaries (~100% Saved):** Massive assets (like `.png` or `.pdf` files) are cataloged into a ~5-token reference without corrupting terminal output or wasting context window.

