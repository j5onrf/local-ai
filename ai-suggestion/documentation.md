# AI-Suggestion Agent (v0.7.7) — Documentation

An adaptive, local/cloud AI shell assistant designed to conform to your terminal environment. By leveraging a high-speed, local token-matrix cache alongside local or cloud LLMs, it provides interactive command suggestions, manages aliases, executes system tools, and answers conversational queries with zero background CPU overhead.

---

## 1. System Architecture Overview

The project operates under an on-demand execution model designed to protect terminal responsiveness:

* **Zero-Background Footprint:** No background daemons, cron-jobs, or continuous CPU-polling threads are used. Your shell experiences 0% idle RAM and 0% idle CPU overhead.
* **Dual-Layer Execution:** 
  * **Standard suggestions (direct shell inputs):** Bypasses the LLM completely. Suggestion queries are evaluated locally via a pure Python Sørensen-Dice set-intersection matrix in under 2ms.
  * **Conversational queries (using the `ai` prefix):** Run on-demand. If cloud API keys are set, it connects to Google Gemini; otherwise, it falls back to your local OpenAI-compatible completions API (such as `llama.cpp` or `Ollama` running on port 8080).
* **On-Demand Workspace Agents (`ai init`):** A custom indexing routine that scans your project directories, generates structural file trees, and launches a persistent, multi-turn copilot session targeted specifically to your codebase.
* **Offline Resilience:** If your local AI server and internet are offline, your command suggestions and custom aliases continue to work locally and instantly. Only conversational LLM chat requests are safely blocked.

### A. The Suggestion Loop (0% Idle CPU / Offline-Safe)

```text
                         [ Direct Shell Input ]
                                   │
                                   ▼
                        [ Token Matrix Search ]
                       Sørensen-Dice Coefficient
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
       ( Match Found )                           ( No Match Found )
              │                                         │
              ▼                                         ▼
      [ Match Carousel ]                      [ Unmapped Warning ]
    Up/Down Arrow Selector                   "ℹ <intent> is not mapping..."
              │                                         │
       ┌──────┴──────┐                                  ▼
       ▼             ▼                             [ Safe Exit ]
    [Enter]      [Any Key / Esc / Ctrl+C]       Returns to Bash Prompt
       │             │
       ▼             ▼
  Is Directory?    Cancel Menu
   /       \      (Buffer Flush)
 (No)      (Yes)
  /          \
Execute   Auto-Launch
Command    ai init <path>
```

### B. The Conversational Agent (On-Demand / Hybrid Local-Cloud)

```text
                         [ ai <conversational query> ]
                                      │
                                      ▼
                   [ Cloud Mode Active? (Env Key check) ]
                                 /      \
                        (No Key)/        \(API Key Sourced)
                               /          \
                     [ Local Port 8080 ]   [ Standard Cloud Routing ]
                     (Offline -> Safe      (Bypasses local checks)
                     Connection Error)            │
                               \                  /
                                ▼                ▼
                         [ Inline Latency Spinner ]
                           Displays Green Rotator
                                 (| / - \)
                                      │
                             [ Connection Opened ]
                           Wipes Spinner from Screen
                                      │
                           [ Tool-Intent Match? ]
                                 /          \
                            ( Yes )          ( No )
                              /                \
               [ Execute local tool ]      [ Standard Chat ]
                Inject Context (RAG)        Generic Response
                              \                /
                               ▼              ▼
                          [ Local/Cloud OpenAI-API ]
                          (Streams Response to Shell)
```

---

## 2. Cloud Integration

The agent natively supports **Google Gemini's OpenAI-compatible completions API**. This allows you to offload conversational reasoning and context-injected tool calls to the cloud with **0% local CPU/RAM overhead**.

### Environment Configuration (`~/.bashrc`)
To activate cloud mode, export your API key and preferred model at the bottom of your `~/.bashrc`:
```bash
export GEMINI_API_KEY="AIzaSyYourFullGeminiApiKeyHere"
export CLOUD_MODEL="gemini-3.1-flash-lite"
```

---

## 3. Configuration & The Semantic Index

Your agent's brain is managed by a plain-text configuration master file.

* **Path:** `~/.config/local-ai/ai-suggestion/ai-context.txt`
* **Syntax:** `[command] ---> [intent1], [intent2], [intent3]`

*Example:*
```text
omarchy-launch-webapp https://music.youtube.com/ ---> youtube music
```

### A. Automatic Compilation on the Fly
Every time you interact with the agent, the Python script compares modification timestamps (`getmtime`) of your files. If the plain-text configuration has been modified, it silently rebuilds your minified, single-line lookup index (`ai-context.idx`) in under 2ms before executing.

### B. Triple-Redundancy Self-Healing Index
To prevent index corruption or empty cache loads from breaking command suggestions, the `matrix_search` function implements an active validation cycle:
1. **Missing Cache Detection:** If the `.idx` file is deleted, it compiles a new one instantly on the next query.
2. **Malformed JSON Recovery:** If the index file contains corrupt or interrupted data, it catches `json.JSONDecodeError` and forces a fresh rebuild.
3. **Empty Index Validation (`[]`):** If the index successfully loads but parses as empty (`[]`) while the source configuration file actually has text lines, the script flags this as a logic failure and immediately forces a rebuild.

---

## 4. Active System Tools & Project Workspace Agents

### A. Local Context-Injected RAG (`[TOOL]`)
You can turn any standard Linux command, package, binary, or custom script into an AI tool by prefixing the command with `[TOOL]` in your `ai-context.txt`:
```text
[TOOL] df -h / ---> check my nvme drive, is my hard drive full, show disk space
```
When you run a conversational query targeting that intent, the script executes the tool behind the scenes (protected by a **15-second safety timeout**), captures its raw stdout, and injects it directly into the LLM's prompt context as real-time system data.

### B. Project Workspace Agents (`ai init`)
When analyzing codebase folders, running raw chat queries lacks necessary structural context. Running `ai init <path>` triggers a dedicated indexing binary (`tools/init-projects`) that:
1. Resolves the absolute directory path and extracts the project name.
2. Generates a recursive directory structure map down to three folder levels.
3. Packages workspace-specific agent guidelines and system instructions.
4. Permanently caches the compiled payload inside the isolated `projects/` directory under a path-sanitized filename (e.g., `projects/home-user-Projects-quickshell.txt`).

This bypasses manual initialization cycles, allowing the Workspace Agent to read your directory trees, recognize active config files (like `hypr_api_ref.lua`), and respond to design questions with precise codebase awareness.

### C. Command Interceptor Directory Routing
To make project initialization frictionless, you can map absolute directory paths directly inside your `ai-context.txt`:
```text
~/Projects/quickshell ---> projects quickshell, projects
```
If you search for `projects` and execute the suggestion, the `ai_handle_missing` shell hook detects that the target command is an existing directory path, bypasses standard execution, and seamlessly launches `ai init` on the target path automatically.

---

## 5. Mathematical, Structural, & Interface Optimizations

### A. Conversational-Resilient Stop Words
To prevent natural conversational padding (like *"what about...", "is it...", "do you have..."*) from causing keyword collisions in your local set-intersection matrix, the `tokenize()` function automatically filters out a pre-compiled set of common English stop words. This ensures that a phrase like `"is it going to rain in the next few days?"` resolves strictly to `["rain"]` under the hood.

### B. Theme-Adaptive, Thread-Safe Latency Spinner
To keep the terminal interface responsive during network handshakes and LLM processing delays, a lightweight daemon thread runs an inline spinner (`|`, `/`, `-`, `\`) at 12 FPS. 

By utilizing standard 4-bit ANSI colors (`\033[1;32m` / Bold Green Theme Accent) rather than hardcoded 24-bit TrueColor hex codes, **the interface automatically and dynamically adapts to your system theme.** The spinner, `Agent:`, and `AI:` labels will seamlessly inherit the precise accent hue of your active terminal color palette (such as Tokyo Night, Nord, or Gruvbox) completely on the fly.

When the first stream chunk is returned from the host, the spinner thread is joined, the carriage return line is wiped (`\r\x1b[K`), and the response begins outputting smoothly.

### C. Multi-Turn Memory (State Preservation)
Unlike single-turn command completions, interactive conversation sessions maintain state through a local, memory-resident `chat_history` list. The stream loop compiles the incoming text chunks and appends the assistant's response to the active array, ensuring the model retains full context of previous messages and initialized project configurations.
```
---
