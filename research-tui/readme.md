# DeepResearch-TUI

<img width="3840" height="2160" alt="20260605_214750" src="https://github.com/user-attachments/assets/29756032-7e3e-4802-813b-f30a06b5ebfa" />

---

An ultra-lightweight, terminal-native frontend for the **Odysseus** deep research engine.

### Overview
DeepResearch-TUI provides a keyboard-centric interface to trigger and view deep, multi-round research reports. It decouples the heavy-lifting extraction engine (Odysseus) from the presentation layer, allowing for fast, terminal-native scanning, link navigation, and clipboard export.

### Features
*   **Iterative Research:** Utilizes the robust Odysseus Think→Search→Extract→Synthesize loop.
*   **Native TUI:** Scrollable, searchable, and minimalist interface.
*   **Parallel Fetching:** Concurrent web crawling and search execution for speed.
*   **Keyboard-First:** Navigate reports, launch citations in your browser, and copy-all with `Ctrl+A`.
*   **Lightweight:** Zero external dependencies (only standard Python libraries).

### Setup
Ensure your Odysseus environment is configured and the `odysseus-cli` bridge is mapped in your research-tui directory.

```bash
# Usage
deep-research "your research topic here"
```

### Attribution
Built as a terminal interface bridge for the [Odysseus Research Engine](https://github.com/pewdiepie-archdaemon/odysseus/blob/dev/src/deep_research.py).
```
