# Custom Plugins & Tools: `plugins/`

User-extensible directory for custom standalone scripts, feature extensions, and automation tools.

---

## How to Add a Plugin

1. **Create an Executable Script:** Place your `.py` or `.sh` script in this folder and make it executable:
   ```bash
   chmod +x ~/.config/py-agent/plugins/my-plugin
   ```

2. **Include a Shebang:** Ensure the first line defines the interpreter so `index-map` indexes AST symbols:
   ```python
   #!/usr/bin/env python3
   """Summary of plugin capability."""
   ```

3. **Map Trigger in `ai-context.md`:** Add a line to `~/.config/py-agent/ai-context.md` for shortcut routing:
   ```properties
   # --- My Custom Plugin ---
   [TOOL] ~/.config/py-agent/plugins/my-plugin --cat ---> my plugin, run feature
   ```

---

## Execution & Output Flags (`ai-context.md`)

| Format | Output Behavior |
| :--- | :--- |
| `[TOOL] <path>` | Formatted output through Rich Markdown (`\| view`). |
| `[TOOL] <path> --cat` | Direct raw terminal output (`\| cat`). |
| `[TOOL] <path> --s` | Silent execution (bypasses authorization gate). |
| `<path>` (No `[TOOL]`) | Native foreground execution (for interactive TUIs and curses apps). |

---

## Capabilities

* **Zero Core Edits:** Add or remove tools anytime without touching core agent modules.
* **Dual Execution:** Callable directly from shell shortcuts or injected into AI context turns.
