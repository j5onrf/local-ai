# DeepResearch-TUI

<img alt="20260606_100004" src="https://github.com/user-attachments/assets/3b5dc15e-11e3-4d0b-850d-03010ba7165e" />

---

An ultra-lightweight, terminal-native frontend for the **[Odysseus](https://github.com/pewdiepie-archdaemon/odysseus)** and **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** deep research engines.

### Overview
DeepResearch-TUI provides a keyboard-centric interface to trigger and view deep, multi-round research reports. It decouples the heavy-lifting research logic from the presentation layer, allowing for fast, terminal-native reading and automated read-aloud summaries without the need for a web browser or daemon.

### How it Works
This tool acts as a **CLI Bridge**. It offloads the research heavy-lifting—Think→Search→Extract→Synthesize—to your local research backend, then captures the output in a clean, terminal-wrapped layout. 
* **Frontend:** Your TUI (Keyboard-driven, no external dependencies).
* **Backend:** Dynamic routing. Runs your reports through either the **Odysseus Engine** (default) or the **Nous Research Hermes Agent** (--hermes) [1].

### Features
*   **Production-Grade Engine:** Powered by the Odysseus Iterative Research loop or Hermes tool-calling pipelines [1].
*   **Dynamic Column Scaling:** Automatically clears your screen and wraps paragraphs to perfectly match your active terminal or window splits.
*   **AI Summary & Read-Aloud Bridge:** Press `s` to automatically pass the generated report to your `llmsum.py` summary engine. It compiles a "Core Takeaways" summary and immediately launches the **KoKo text-to-speech reader** with responsive line-by-line highlighting.
*   **Keyboard-First:** Press `s` to trigger the AI summary read-aloud, or press any other key to exit cleanly.
*   **Zero-Dependency UI:** Built using standard Python libraries only.
*   **Dual-Engine Toggling:** Swap your research backend dynamically with a simple CLI flag.

### Setup
1. Ensure your Odysseus environment is configured at `/opt/odysseus/`.
2. Map both the `odysseus-cli` and `hermes-cli` bridges in your config directory.
3. Ensure `llmsum.py` (AI Summary TUI) and `koko` are configured on your system paths.
4. *(Optional)* Optimize search speed and remove fallback warnings by installing the API client inside the Odysseus virtual environment:
   ```bash
   /opt/odysseus/venv/bin/pip install duckduckgo-search
   ```

### Usage

```bash
# Standard usage (via Odysseus)
deep-research "your research topic here"

# Dynamic routing (via Hermes Agent)
deep-research --hermes "your research topic here"
```

***
