# Local-AI Agent (v0.7.9.5) — Documentation

An adaptive, local/cloud AI shell assistant designed to conform to your terminal environment. By leveraging a high-speed, local token-matrix cache alongside local or cloud LLMs, it provides interactive command suggestions, manages aliases, executes system tools, and answers conversational queries with zero background CPU overhead.

---

## 1. System Architecture Overview

The project operates under an on-demand execution model designed to protect terminal responsiveness:

* **Zero-Background Footprint:** No background daemons, cron-jobs, or continuous CPU-polling threads are used. Your shell experiences 0% idle RAM and 0% idle CPU overhead [1].
* **Dual-Layer Execution:** 
  * **Standard suggestions (direct shell inputs):** Bypasses the LLM completely. Suggestion queries are evaluated locally via a pure Python set-intersection matrix in under 2ms.
  * **Conversational queries (using the `ai` prefix):** Run on-demand. The script utilizes a robust, prioritized fallback hierarchy: Gemini Cloud API $\rightarrow$ OpenRouter Cloud API $\rightarrow$ Custom Cloud API $\rightarrow$ Local AI Server (such as `llama.cpp` or `Ollama` running on port 8080) [1.1].
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

### B. The Conversational Agent (On-Demand / prioritized cascading fallback)

```text
                                 [ ai <conversational query> ]
                                               │
                                               ▼
                              [ Gemini API Key Exported? ]
                                      /         \
                             (Yes)  /             \ (No)
                                   /               \
                       [ Google Gemini API ]    [ OpenRouter API Key Exported? ]
                       (Success -> Return)              /         \
                                  │            (Yes)  /             \ (No)
                                  │                  /               \
                                  │       [ OpenRouter API ]    [ Custom API Sourced? ]
                                  │       (Models Fallback List)        /      \
                                  │                  │          (Yes) /          \ (No)
                                  │                  │               /            \
                                  │      [ Custom Cloud ]   [ Local Port 8080 ]
                                  │             │           (Offline -> Safe
                                  │             │           Connection Error)
                                  ▼             ▼                  ▼
                                ┌─────────────────────────────────────────────────────┘
                                │
                                ▼
                    [ Inline Latency Spinner ]
                      Displays Accent Rotator
                          (⠋ ⠙ ⠹ ⠸ ...)
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
                    [ Selected OpenAI-API Endpoint ]
                     (Streams Response to Shell)
```

---

## 2. Cloud Integration & Multi-Provider Fallbacks

The agent features a dynamic, cascading failover connection pipeline [1.1]. This ensures your conversational queries and agentic tool integrations resolve reliably, shifting from cloud systems to local infrastructure seamlessly if credentials expire or endpoints go offline [1.1].

### A. Environment Configuration (`~/.bashrc`)
To configure your cloud access priorities, export your keys and models at the bottom of your `~/.bashrc`:

```bash
# Primary: Google Gemini Cloud API Configuration
export GEMINI_API_KEY="AIzaSyYourFullGeminiApiKeyHere"
export CLOUD_MODEL="gemini-3.1-flash-lite"

# Fallback: OpenRouter Configuration
export OPENROUTER_API_KEY="sk-or-v1-YourFullOpenRouterKeyHere"
export OPENROUTER_MODEL="poolside/laguna-m.1:free"
```

### B. OpenRouter Model-Level Fallbacks
When falling back to OpenRouter, the agent automatically configures a robust multi-model fallback chain directly inside the API request payload. By sending a prioritized `models` array, OpenRouter handles congestion mitigations on its own servers:

```json
{
  "model": "poolside/laguna-m.1:free",
  "models": [
    "poolside/laguna-m.1:free",
    "qwen/qwen3-coder:free",
    "openrouter/free"
  ]
}
```
If the primary free coding model (`Laguna M.1`) is congested or rate-limited, OpenRouter automatically failovers to the next highest-priority model in the array without dropping your request.

---

## 3. Configuration & The Semantic Index

Your agent's brain is managed by a plain-text configuration master file.

* **Path:** `~/.config/local-ai/local-ai-agent/ai-context.txt`
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

### B. Agentic Diagnostic Tool (`ai-status`)
The system features a dedicated local diagnostic script located at `~/.config/local-ai/local-ai-agent/tools/agentic/ai-status`. It operates as a dual-purpose tool:
* **As a Native Shell Shortcut (Section 4):** Typing `ai-status` on the command line invokes the suggestion carousel, strips the `[TOOL]` prefix, and prints a beautiful colorized diagnostics panel showing key masks, endpoint connectivity, and your active fallback routing.
* **As an Agentic Chat Tool (Section 3):** Typing `status check` inside an active chat session executes the script silently. It injects active API diagnostics and strict markdown instruction sets directly into the LLM context, enabling the model to conversationalize your connection details in under two sentences.

### C. Project Workspace Agents (`ai init`)
When analyzing codebase folders, running raw chat queries lacks necessary structural context. Running `ai init <path>` triggers a dedicated indexing binary (`tools/init-projects`) that:
1. Resolves the absolute directory path and extracts the project name.
2. Generates a recursive directory structure map down to three folder levels.
3. Packages workspace-specific agent guidelines and system instructions.
4. Permanently caches the compiled payload inside the isolated `projects/` directory under a path-sanitized filename (e.g., `projects/home-user-Projects-quickshell.txt`).

This bypasses manual initialization cycles, allowing the Workspace Agent to read your directory trees, recognize active config files (like `hypr_api_ref.lua`), and respond to design questions with precise codebase awareness.

### D. Specialized Workspace Initialization with Custom Skills
Rather than using heavy wrapper utilities or custom prefixes, you can initialize a project with a custom role-persona by simply appending the skill name directly after your directory path in your master configuration file:

```text
# --- Specialized Project Initializer (Primes workspace with "coder" Skill!) ---
~/Projects/quickshell coder ---> projects quickshell, projects
```

When you search for `projects quickshell` and execute the suggestion:
1. The Bash hook (`ai_handle_missing`) detects that the matched command consists of a valid directory path followed by a trailing word (`coder`).
2. It automatically separates the path from the skill name and executes: `ai init ~/Projects/quickshell coder`.
3. The `init-projects` worker locates the matching `/skills/coder.txt` instruction sheet and merges it directly into the compiled project context file.
4. When `alias-ai.py` boots, it dynamically scans the payload, extracts the active skill tag, and displays it highlighted inside your starting banner:
   ```text
   AI Agent Session Initialized | Context Loaded [coder] | Ctrl+C to exit.
   ```

### E. Command Interceptor Directory Routing
To make project initialization frictionless, you can map absolute directory paths directly inside your `ai-context.txt`:
```text
~/Projects/qwen-hypr ---> projects qwen, projects
```
If you search for `projects qwen` and execute the suggestion, the `ai_handle_missing` shell hook detects that the target command is an existing directory path, bypasses standard execution, and seamlessly launches `ai init` on the target path automatically.

---

## 5. Mathematical, Structural, & Interface Optimizations

### A. Conversational-Resilient Stop Words
To prevent natural conversational padding (like *"what about...", "is it...", "do you have..."*) from causing keyword collisions in your local set-intersection matrix, the `tokenize()` function automatically filters out a pre-compiled set of common English stop words. This ensures that a phrase like `"is it going to rain in the next few days?"` resolves strictly to `["rain"]` under the hood.

### B. Match Coverage Collision Protection (Conflict Prevention Math)
To prevent short, generic mappings (e.g. `[TOOL] .../ai-status ---> status`) from triggering on conversational sentences containing that word (e.g. `what is the status of the world`), the similarity algorithm uses a **Match Coverage constraint**.

The perfect-subset score bonus (`+0.20`) is only applied if the matched words represent at least 50% of the user's active search query:
```python
if match_count == entry_len and (match_count / len_q >= 0.50):
    score += 0.20
```
This forces conversational sentences with lower overlap ratios to drop below your standard conversational threshold (e.g. `0.65`), preserving your generic terminal shortcuts without polluting conversational chats.

### C. Theme-Adaptive, Thread-Safe Latency Spinner
To keep the terminal interface responsive during network handshakes and LLM processing delays, a lightweight daemon thread runs an inline 10-step Braille spinner (`⠋`, `⠙`, `⠹`, ...) at 12 FPS [1.1]. 

By utilizing standard 4-bit ANSI colors (`\033[1;32m` / Bold Green Theme Accent) rather than hardcoded 24-bit TrueColor hex codes, **the interface automatically and dynamically adapts to your system theme.** The spinner, `Agent:`, and `AI:` labels will seamlessly inherit the precise accent hue of your active terminal color palette (such as Tokyo Night, Nord, or Gruvbox) completely on the fly.

When the first stream chunk is returned from the host, the spinner thread is joined, the carriage return line is wiped (`\r\x1b[K`), and the response begins outputting smoothly.

### D. Multi-Turn Memory (State Preservation)
Unlike single-turn command completions, interactive conversation sessions maintain state through a local, memory-resident `chat_history` list. The stream loop compiles the incoming text chunks and appends the assistant's response to the active array, ensuring the model retains full context of previous messages and initialized project configurations.
```
---
```
