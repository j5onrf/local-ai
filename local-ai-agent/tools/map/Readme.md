# Skeleton Map

Give your AI agent a complete semantic index of your repository or project while saving up to **90% in token overhead**.

Unlike standard file listings (`ls -R`), this utility leverages Abstract Syntax Tree (AST) parsing to map the actual internal interfaces (classes and functions) of your codebase without exposing raw, token-heavy code logic.

---

### Expected Input/Output Behavior

```text
~ ❯ sm
[01/01] ❯ [skeleton map] ~/.config/local-ai/local-ai-agent/tools/map/skeleton-map
:: ↵ run  any skip: 
✔ Skeleton map compiled successfully.
~ ❯ 

```

---

## Generated Artifact Structure

The script outputs a structured `skeleton.json` directly into this folder. When sent to the AI alongside an active workspace file, it acts as an immediate semantic index:

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

## File Manifest

* `skeleton-map`: The core Python 3 executable parsing engine.
* `skeleton.json`: The latest compiled structural mapping database (auto-generated).
* `readme.md`: This file.


