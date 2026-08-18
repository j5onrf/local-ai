# Custom Plugins & Tools: `tools/plugins/`

User-extensible directory for custom standalone scripts, feature extensions, and automation tools.

---

## How to Add a Plugin

1. **Create an Executable Script:** Place your `.py` or `.sh` script in this folder and make it executable:
   ```bash
   chmod +x ~/.config/local-ai/tools/plugins/my-plugin
   ```

2. **Include a Shebang:** Ensure the first line defines the interpreter so `index-map` indexes AST symbols:
   ```python
   #!/usr/bin/env python3
   """Summary of plugin capability."""
   ```

3. **Map Trigger in `ai-context.md`:** Add a single line to `~/.config/local-ai/ai-context.md` for shortcut routing:
   ```properties
   # --- My Custom Plugin ---
   [TOOL] ~/.config/local-ai/tools/plugins/my-plugin --cat ---> my plugin, run feature, custom tool
   ```

---

## Capabilities

* **Zero Core Edits:** Add or remove tools anytime without touching core agent modules.
* **Auto-Indexed:** `index-map` automatically indexes functions, imports, and docstrings from all scripts in this directory.
* **Dual Execution:** Callable directly from shell shortcuts or injected into AI context turns.

