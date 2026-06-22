> Testing (Concepts & Prototypes)

### The Ultra-Lite "PixelBrowse" Tool Design

# A clean, single-file Python script:
~/.config/local-ai/tools/subsec/headless-chromium/pixel-browse
How It Works:
The Command: You run pixel-browse <URL> "<Your Question>".
Ingestion: It executes your native, headless system chromium to take a fast 1280x1600 screenshot of the page, saving it to /tmp.
Execution: It converts the image to base64, packages it with your question, and sends it directly to your Gemini API . It prints the final, visually accurate explanation to your screen.

# Ultra-Lite Philosophy
No Memory Bloat: It does not load large visual embedding or PyTorch models locally. Your workstation's physical RAM and CPU remain completely free and unburdened.
No Data Loss: By taking a screenshot, it preserves the exact spatial coordinates of side-by-side elements, pricing grids, and visual headers.
Extremely Low Code Weight: It uses Python's standard library and pre-installed system chromium package, keeping the tool's footprint tiny and easy to maintain.

# First Test Example: (headless-chrome-browser)

```text
~ ❯ pixel browse
[01/01] ❯ [pixel browse] ~/.config/local-ai/tools/subsec/headless-chromium/pixel-browse | cat
:: ↵ run  Esc: 
[Pixel] Enter target URL: https://github.com/j5onrf/local-ai
[Pixel] Enter your question: what does the banner image say
── PIXEL-BROWSE RESULTS ────────────────────────────────────────────────────
The banner image contains the following text:

*   **Center:** "LOCAL-AI AGENT"
*   **Top Left:** "ai <query>"
*   **Top Right:** "ai init"
*   **Bottom Left:** "ai init"
*   **Bottom Right:** "ai status"
*   **Hexagon Labels:** "Tools", "Skills", "GEMINI", "MULTI-TURN CHAT", "WORKSPACE AGENTS"
*   **Bottom Center:** "Python 3.10+" and "Bash / Zsh 5.0+"
*   **Center Icon:** A terminal prompt symbol `~>_`
────────────────────────────────────────────────────────────────────────────

~ ❯ 
```
