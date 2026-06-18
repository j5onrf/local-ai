# Skeleton Map

Maps your project's code structure into a lightweight semantic index, saving **95% to 99% in token overhead** compared to raw code ingestion. 

Instead of feeding full files to an AI, this tool uses Abstract Syntax Tree (AST) parsing to map Python classes/functions/imports, and leverages custom regex parsers for Rust, Go, Lua, and QML. For all other languages, config files (`.yaml`, `.toml`, `.env`), and text files (`.txt`), it extracts a first-line summary, while safely cataloging images and binary assets (`binary/png`, `binary/jpg`) without context pollution.

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

* **Code (~98% Saved):** A 400-line Python file (~3,000 tokens) is reduced to a ~50-token JSON outline (including root imports).
* **Configs, Text & Shell (~99% Saved):** A 1,500-token Markdown, Shell script, or YAML file is reduced to a ~15-token summary.
* **Images & Binaries (~100% Saved):** Massive assets (like `.png` or `.pdf` files) are safe-cataloged into a ~5-token reference without corrupting terminal output.

---

### Output Schema (`skeleton.json`)

```json
{
  "README.md": {
    "type": "markdown",
    "summary": "local-ai"
  },
  "local-ai-agent/ai-context.md": {
    "type": "markdown",
    "summary": "Local-AI Agent Blueprint"
  },
  "local-ai-agent/alias-ai.py": {
    "type": "python",
    "imports": [
      "json",
      "os",
      "re",
      "readline",
      "select",
      "shutil",
      "subprocess",
      "sys",
      "termios",
      "threading",
      "time",
      "tty",
      "urllib"
    ],
    "classes": [
      "InlineSpinner"
    ],
    "functions": [
      "sanitize_input",
      "tokenize",
      "check_danger",
      "ensure_mysys_exists",
      "find_skill_file",
      "load_skill_content",
      "print_stock_error",
      "run_local_tool",
      "load_context_entries",
      "jaccard_search",
      "get_key",
      "clean_tool_prefix",
      "get_system_context",
      "run_interactive_selection",
      "stream_llm_response",
      "__init__",
      "_spin",
      "start",
      "stop"
    ]
  },
  "local-ai-agent/readme.md": {
    "type": "markdown",
    "summary": "Local-AI Agent <kbd>v0.8.6.1</kbd>"
  },
  "local-ai-agent/ai-hook.sh": {
    "type": "shell",
    "summary": "Local-Ai Agent Hook v0.8.6.2 [j5onrf] [06-18-26]"
  },
  "local-ai-agent/tools/agentic/identity/logo.png": {
    "type": "binary/png"
  },
  "config.toml": {
    "type": "toml",
    "summary": "[server]"
  }
}
```

---

### Files

* `skeleton-map`: Python 3 AST and regex parser (features auto `.gitignore` and universal fallback/binary support).
* `skeleton.json`: Auto-generated structural mapping database.
* `readme.md`: This file.

