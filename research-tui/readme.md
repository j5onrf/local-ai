# DeepResearch-TUI

<img width="3840" height="2160" alt="20260605_225005" src="https://github.com/user-attachments/assets/90951db8-0b21-442e-bf8a-5ad8959dfe11" />

---

An ultra-lightweight, terminal-native frontend for the **[Odysseus](https://github.com/pewdiepie-archdaemon/odysseus)** deep research engine.

### Overview
DeepResearch-TUI provides a keyboard-centric interface to trigger and view deep, multi-round research reports. It decouples the heavy-lifting research logic from the presentation layer, allowing for fast, terminal-native scanning, keyword filtering, link navigation, and clipboard export without the need for a web browser or daemon.

### How it Works
This tool acts as a **CLI Bridge**. It offloads the research heavy-lifting—Think→Search→Extract→Synthesize—to the robust Odysseus engine, then captures the output in a clean, scrollable TUI. 
* **Frontend:** Your TUI (Keyboard-driven, no external dependencies).
* **Backend:** Odysseus Engine (Stateful, research-hardened, API-resilient).

### Features
*   **Production-Grade Engine:** Powered by the Odysseus Iterative Research loop.
*   **Terminal-Native TUI:** Scroll, filter, and read reports directly in your shell.
*   **Keyboard-First:** Use `/` to scan keywords, `o` to launch source links, and `Ctrl+A` to copy the full report.
*   **Zero-Dependency UI:** Built using standard Python libraries only.
*   **Parallel Fetching:** Concurrent web crawling for near-instant round execution.

### Setup
1. Ensure your Odysseus environment is configured at `/opt/odysseus/`.
2. Map the `odysseus-cli` bridge in your config directory.
3. Place `deep-research` in your `ai-suggestion/tools/agentic/` path.

```bash
# Direct usage
deep-research "your research topic here"
```

### Attribution
Built as a terminal interface bridge for the [Odysseus Research Engine](https://github.com/pewdiepie-archdaemon/odysseus/blob/dev/src/deep_research.py).

***

