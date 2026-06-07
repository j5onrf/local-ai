# llmsum.py

<img alt="20260523_220348" src="https://github.com/user-attachments/assets/fdd2d2b2-d938-4177-8bd2-4cda27668f06" />

`Qwen3.5-2B+` `Gemini-3.1-Flash-Lite` `llama.cpp` `Python 3.10+` `Bash / Zsh 5.0+`

---

An ultra-lightweight, high-performance terminal companion designed to instantly summarize clipboard text, transcripts, and documents with zero background system overhead. Featuring an optimized neural Text-to-Speech (TTS) reader with a dynamic sliding-window progressive highlighter.

---

## Core Features

* **Zero-Dependency Footprint:** Written entirely in standard Python without requiring any `pip` package installations.
* **Hybrid Cloud-Local Intel:** Automatically routes requests to Google Gemini's completions API if a `GEMINI_API_KEY` is present. If offline or missing a key, it falls back seamlessly to your local `llama.cpp` server (port 8080).
* **Automatic Markdown Typesetting:** Automatically strips raw markdown formatting tokens (bolding asterisks, code backticks) and typesets the text into a perfectly aligned sequential numbered list.
* **Dynamic Sliding-Window Highlighting:** Resolves cumulative pacing drift over long summaries (10 to 50 lines). Features a moving 3-line high-contrast visual window that centers the active spoken line, leaving a 1-line lookback buffer above and a 1-line lookahead buffer below.
* **Integrated TTS Toggle:** Instantly toggle Text-to-Speech narration on or off directly from the start menu by pressing **`t`**.

---

## TUI Architecture

```text
Terminal Keyword: llmsum
              │
              ▼
      ┌───────────────┐
      │   llmsum.py   │
      └───────┬───────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌───────────────┐   ┌───────────────┐
│   Local LLM   │   │  Gemini (API) │
├───────────────┤   ├───────────────┤
│ • llama.cpp   │   │ • Cloud API   │
│ • 0ms Network │   │ • High-Speed  │
│ • 100% Private│   │ • Offloaded   │
└───────────────┘   └───────────────┘
```

---

## Quick Launch via Local-Ai Agent

This TUI is designed to integrate seamlessly with your **Local-Ai Agent**. By registering `llmsum.py` in your semantic mapping index, you can launch the summary engine on-demand simply by typing the `llmsum` keyword:

```text
# Add this line to your ~/.config/local-ai/local-ai-agent/ai-context.txt
~/.config/local-ai/ai-summary/llmsum.py ---> llmsum, ytsum, summary
```

Once mapped, typing `llmsum` in any standard terminal window will instantly trigger the suggestion menu, allowing you to run your clipboard summary TUI with a single keypress.

---

## Global Neural TTS Reader (Hyprland Binds)

To trigger instant, system-wide reading of any text on your screen (your active clipboard selection) and bind a panic switch to kill running audio instantly, add these binds to your window manager configuration:

```bash
# --- Optimized Neural Kokoro TTS Reader ---
bind = SUPER SHIFT, R, exec, bash -c 'TEXT=$(wl-paste --primary); [ -n "$TEXT" ] && koko --style am_echo --speed 1.15 text "$TEXT" -o /dev/shm/tts.wav && pw-play /dev/shm/tts.wav'

# --- Kill TTS Audio Output Instantly ---
bind = SUPER SHIFT, X, exec, pkill -9 -f "pw-play|koko"
```

---

## Configuration

The script reads and formats text dynamically using five pre-compiled prompt profiles. You can configure your local server address directly at the top of `llmsum.py`:

```python
# --- Configuration ---
LOCAL_API_URL = "http://localhost:8080/v1/chat/completions"

# Text-to-Speech Settings
TTS_ENABLED = True
```

### Environment Routing (Optional)
To activate cloud routing, export your Gemini API key and preferred model in your environment config (e.g., `~/.bashrc` or `~/.zshrc`):
```bash
export GEMINI_API_KEY="AIzaSyYourFullGeminiApiKey"
export CLOUD_MODEL="gemini-3.1-flash-lite"  # Optional: Customize cloud model
```

---


