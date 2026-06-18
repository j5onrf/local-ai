# Skeleton Map

Maps your project's code structure into a lightweight semantic index, saving **95% to 99% in token overhead** compared to raw code ingestion. 

Instead of feeding full files to an AI, this tool uses Abstract Syntax Tree (AST) parsing to extract classes, functions, and markdown headers. Your agent uses this map first, then requests only the specific files it needs to modify.

---

### Expected Behavior

```text
~ ❯ sm
[01/01] ❯ [skeleton map] ~/.config/local-ai/local-ai-agent/tools/map/skeleton-map
:: ↵ run  any skip: 
Scan target [.]:
✔ Skeleton map compiled successfully.
~ ❯ 
```

*Pressing **Enter** at the `Scan target [.]:` prompt defaults to the current working directory.*

---

### Token Savings Math

* **Code (~98% Saved):** A 400-line Python file (~3,000 tokens) is reduced to a ~40-token JSON outline.
* **Docs (~99% Saved):** A 1,500-token Markdown file is reduced to a ~15-token title summary.

---

### Output Schema (`skeleton.json`)

```json
"tools/subsec/media/media.py": {
  "type": "python",
  "classes": [],
  "functions": [
    "trigger_robust_toggle",
    "get_system_volume",
    "adjust_system_volume",
    "run_media_control"
  ]
}
```

---

### Files

* `skeleton-map`: Python 3 AST parser (features auto `.gitignore` support).
* `skeleton.json`: Auto-generated structural mapping database.
* `readme.md`: This file.

