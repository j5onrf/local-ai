# Local-AI Agent (v0.8.1.1) — Documentation

An adaptive, local/cloud AI shell assistant designed to conform to your terminal environment with zero background overhead. By leveraging a high-speed, rarity-weighted (TF-IDF) sparse search index alongside local or cloud LLMs, it provides instant command suggestions, executes local RAG tools, manages specialized project skills, and handles natural-language conversational queries. It features a zero-daemon local network Voice Query Bridge for hands-on desktop automation and is capable of continuous offline learning by automatically capturing and inoculating terminal shortcuts directly from LLM outputs.

---

## 1. System Architecture Overview

The project operates under an on-demand execution model designed to protect terminal responsiveness:

* **Zero-Background Footprint:** No background daemons, cron-jobs, or continuous CPU-polling threads are used. Your shell experiences 0% idle RAM and 0% idle CPU overhead.
* **Dual-Layer Execution:** 
  * **Standard suggestions (direct shell inputs):** Bypasses the LLM completely. Suggestion queries are evaluated locally via an upgraded, rarity-weighted sparse index (using a customized Sørensen-Dice similarity metric with log-scale Inverse Document Frequency weights) in under 2ms.
  * **Conversational queries (using the `ai` prefix):** Run on-demand. The script utilizes a prioritized fallback hierarchy: Gemini Cloud API -> OpenRouter Cloud API -> Custom Cloud API -> Local AI Server (such as `llama.cpp` or `Ollama` running on port 8080).
* **Zero-Configuration Auto-Bootstrap:** On first-run, if no system profile is found, the script automatically executes safe, non-blocking local diagnostics to query your operating system, active kernel, CPU, GPU, and window manager to generate your bespoke `mysys.md` profile with zero user intervention.
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
    Up/Down Arrow Selector                   "Info: <intent> is not mapping..."
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

### C. Voice Query Bridge (Zero-Daemon / Zero-Local-Model)

The system features an optional lightweight voice companion served directly over your local Wi-Fi network. By running `voice`, your PC launches an on-demand, single-threaded HTTPS server on port 9999, completely avoiding any persistent background daemons [3].

When accessed by a tablet or phone on the same network, the browser serves a pure black, mobile-optimized HTML5 client. Speech recognition is offloaded entirely to a secure cloud API over HTTPS using your exported Gemini API key, meaning your PC runs with 0MB of local transcription models and 0% idle CPU overhead [2, 3].

---

## 2. Cloud Integration & Multi-Provider Fallbacks

The agent features a dynamic, cascading failover connection pipeline. This ensures your conversational queries and agentic tool integrations resolve reliably, shifting from cloud systems to local infrastructure seamlessly if credentials expire or endpoints go offline.

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
[TOOL] cat ~/.config/local-ai/local-ai-agent/tools/skills/mysys.md ---> mysys
```

### A. Automatic Compilation and Rarity Weighting
Every time you interact with the agent, the Python script compares modification timestamps (`getmtime`) of your files. If the plain-text configuration has been modified, it silently rebuilds your compiled index (`ai-context.idx`) in under 2ms.

During compilation, the indexer calculates the Document Frequency (DF) of every token across your entire configuration blueprint. It then assigns a log-scale Inverse Document Frequency (IDF) weight to each term:

$$IDF(t) = \ln\left(1 + \frac{N}{DF(t)}\right)$$

This means that highly unique keywords (like `hyprctl`, `nmtui`, or `wttr`) carry immense mathematical weight, while common words (like `show`, `get`, or `run`) are dynamically down-weighted to near-zero. This completely eliminates keyword collisions and false-positive trigger loops.

### B. Triple-Redundancy Self-Healing Index
To prevent index corruption or empty cache loads from breaking command suggestions, the search function implements an active validation cycle:
1. **Missing Cache Detection:** If the `.idx` file is deleted, it compiles a new one instantly on the next query.
2. **Malformed JSON Recovery:** If the index file contains corrupt or interrupted data, it catches `json.JSONDecodeError` and forces a fresh rebuild.
3. **Empty Index Validation (`[]`):** If the index successfully loads but parses as empty (`[]`) while the source configuration file actually has text lines, the script flags this as a logic failure and immediately forces a rebuild.

### C. Collapsed 4-Step Syntax Guide
To keep the file indexer uncluttered, the configuration rules are managed by four standardized directives defined in the blueprint's commented header:
1. **Directory Path:** Indexes workspace and launches standard AI Workspace.
2. **'ai init' + Skill:** Indexes workspace and launches AI pre-primed with Skill.
3. **'[TOOL] command':** Executes local tool/utility (cat, script) for AI context.
4. **Raw Command:** Native terminal alias, interactive TUI, or document viewer.

---

## 4. Active System Tools, Auto-Routing, & Project Workspace Agents

### A. Zero-Bloat Semantic Auto-Routing
To prevent your custom hardware profile specifications from bloating the prompt context of every conversational query, your agent uses runtime semantic routing.

The script monitors your queries against a set of `SYSTEM_KEYWORDS` (such as `system`, `gpu`, `kernel`, `storage`, `network`, `disk`). If your tokenized query intersects with any of these keywords, the script silently loads `/tools/skills/mysys.md` behind the scenes and prepends it to the system context [1.1]. For general non-system tasks, the profile is completely bypassed to conserve context window space.

### B. On-Demand Skill Prefix Routing
You can dynamically execute queries with specialized role profiles on the fly by prefixing your command with the skill name (e.g., `ai coder explain this loop` or `ai admin check this configure`).

On execution, the script checks if the first word of your single-turn query matches a file inside your `tools/skills/` directory. If it matches, it reads the `.md` skill profile as your system prompt, strips that single keyword from your query, and forwards the rest of the question cleanly to the LLM [1.1].

### C. Local Context-Injected RAG (`[TOOL]`)
You can turn any standard Linux command, package, binary, or custom script into an AI tool by prefixing the command with `[TOOL]` in your `ai-context.txt` [1.1]:
```text
[TOOL] df -h / ---> check my nvme drive, is my hard drive full, show disk space
```
When you run a conversational query targeting that intent, the script executes the tool behind the scenes (protected by a **15-second safety timeout**), captures its raw stdout, and injects it directly into the LLM's prompt context as real-time system data.

#### The Dual-Track Formatting Pipeline (Smart Fallback & Auto-Piping)
To achieve maximum ease of use on the human side while guaranteeing clean inputs on the AI side, the agent implements a transparent formatting pipeline:
1. **The Human Terminal (Interactive Mode):** When a user runs a `[TOOL]` mapped command manually, the TUI interpreter `clean_tool_prefix(cmd)` automatically intercepts the command [1.1]. If the command is a script or text file that does not contain a viewer prefix, it dynamically appends a pipe (`| leaf --inline`) on the fly [1.1, 1.3.1]. You receive a beautifully styled terminal document that respects your native terminal themes and colors [1.1, 1.2.2].
2. **The AI Agent (Background Mode):** When running a background tool call, the Python script executes `run_local_tool(cmd)`. This function uses a global regex sweep (`re.sub(r'\|\s*leaf\b.*$', '', cmd)`) to cleanly strip off any trailing formatting pipe (`| leaf`) completely [4]. The tool runs, outputting the clean, unformatted raw Markdown directly to standard output, which feeds directly to the LLM without any ANSI terminal coloring markers [4].
3. **Dynamic Portability Fallback:** If you use this configuration on a system where `leaf` is not installed, the standard-library path helper (`shutil.which("leaf")`) automatically catches the absence, strips the pipeline, and falls back to standard `cat` for you, ensuring that commands never crash or return errors [1.1, 1.3.1].

### D. Agentic Diagnostic Tool (`ai-status` & `ai-system-diagnosis`)
The system features dedicated local diagnostic scripts located at `~/.config/local-ai/local-ai-agent/tools/agentic/`. They operate as dual-purpose tools:
* **As a Native Shell Shortcut (Section 4):** Typing `aistat` or `system health` on the command line invokes the suggestion carousel, strips the `[TOOL]` prefix, and automatically pipes the output into `leaf --inline`, rendering a beautiful, high-contrast diagnostics panel showing key masks, active process hogs, and your active fallback routing [1.1, 1.3.1].
* **As an Agentic Chat Tool (Section 3):** Typing `status check` or `system diagnostics` inside an active chat session executes the scripts silently. It automatically strips out `| leaf` pipelines completely, injecting raw connectivity details, system loads, and strict markdown rules directly into the LLM context, enabling the model to conversationalize your diagnostic details [1.1, 4].

### E. Project Workspace Agents (`ai init`)
When analyzing codebase folders, running raw chat queries lacks necessary structural context. Running `ai init <path>` triggers a dedicated indexing binary (`tools/init-projects`) that:
1. Resolves the absolute directory path and extracts the project name.
2. Generates a recursive directory structure map down to three folder levels.
3. Packages workspace-specific agent guidelines and system instructions.
4. Permanently caches the compiled payload inside the isolated `projects/` directory under a path-sanitized filename (e.g., `projects/home-user-Projects-quickshell.txt` in a clean, code-fenced Markdown format).

This bypasses manual initialization cycles, allowing the Workspace Agent to read your directory trees, recognize active config files (like `hypr_api_ref.lua`), and respond to design questions with precise codebase awareness.

### F. Specialized Workspace Initialization with Custom Skills
Rather than using heavy wrapper utilities or custom prefixes, you can initialize a project with a custom role-persona by simply appending the skill name directly after your directory path in your master configuration file [1.1]:

```text
# --- Specialized Project Initializer (Primes workspace with "coder" Skill!) ---
~/Projects/quickshell coder ---> projects quickshell, projects
```

When you search for `projects quickshell` and execute the suggestion:
1. The Bash hook (`ai_handle_missing`) detects that the matched command consists of a valid directory path followed by a trailing word (`coder`).
2. It automatically separates the path from the skill name and executes: `ai init ~/Projects/quickshell coder`.
3. The `init-projects` worker locates the matching `/skills/coder.md` instruction sheet and merges it directly into the compiled project context file [1.1].
4. When `alias-ai.py` boots, it dynamically scans the payload, extracts the active skill tag, and displays it highlighted inside your starting banner:
   ```text
   AI Agent Session Initialized | Context Loaded [coder] | Ctrl+C to exit.
   ```

### G. Command Interceptor Directory Routing
To make project initialization frictionless, you can map absolute directory paths directly inside your `ai-context.txt`:
```text
~/Projects/qwen-hypr ---> projects qwen, projects
```
If you search for `projects qwen` and execute the suggestion, the `ai_handle_missing` shell hook detects that the target command is an existing directory path, bypasses standard execution, and seamlessly launches `ai init` on the target path automatically.

---

## 5. Mathematical, Structural, & Interface Optimizations

### A. Conversational-Resilient Stop Words
To prevent natural conversational padding (like *"what about...", "is it...", "do you have..."*) from causing keyword collisions in your local set-intersection matrix, the `tokenize()` function automatically filters out a pre-compiled set of common English stop words. This ensures that a phrase like `"is it going to rain in the next few days?"` resolves strictly to `["rain"]` under the hood.

### B. Sparse Index Matching (Rarity Math)
Instead of treating all matching terms as equal integer counts, the similarity algorithm uses rarity-weighted sparse matching scores to evaluate the best matches.

For every index candidate, the matching calculation divides the sum of the matching term IDF weights by the total weights of the query and candidate entry:

$$\text{Score} = \frac{2.0 \times \sum_{t \in Q \cap E} IDF(t)}{\sum_{t \in Q} IDF(t) + \sum_{t \in E} IDF(t)}$$

A perfect-subset score bonus (`+0.20`) is subsequently applied if and only if the matched words represent the entire candidate entry, and cover at least 50% of the active query tokens. This completely isolates short shortcuts from being accidentally matched on generic conversational sentences.

### C. Theme-Adaptive, Thread-Safe Latency Spinner
To keep the terminal interface responsive during network handshakes and LLM processing delays, a lightweight daemon thread runs an inline 10-step Braille spinner (`⠋`, `⠙`, `⠹`, ...) at 12 FPS. 

By utilizing standard 4-bit ANSI colors (`\033[1;32m` / Bold Green Theme Accent) rather than hardcoded 24-bit TrueColor hex codes, the interface automatically and dynamically adapts to your system theme. The spinner, `Agent:`, and `AI:` labels will seamlessly inherit the precise accent hue of your active terminal color palette completely on the fly.

When the first stream chunk is returned from the host, the spinner thread is joined, the carriage return line is wiped cleanly using `\r\x1b[2K\r` across standard output and standard error, preventing line-overlapping at the absolute bottom of the terminal viewport.

### D. Multi-Turn Memory (State Preservation)
Unlike single-turn command completions, interactive conversation sessions maintain state through a local, memory-resident `chat_history` list. The stream loop compiles the incoming text chunks and appends the assistant's response to the active array, ensuring the model retains full context of previous messages and initialized project configurations.

### E. Continual Learning Auto-Inoculation
To systematically build your personal dictionary, your agent is capable of automated command learning. 

During conversational turns, the script parses incoming assistant messages for fenced markdown code blocks or inline terminal commands enclosed in backticks. If a valid, single-line command is extracted that does not already exist in your config, the agent prompts you:
```text
[Learn shortcut] Map "your query" ---> command? (y/N):
```
If accepted, the script appends the new mapping directly to your `ai-context.txt` and removes `ai-context.idx`. The next time you type your query, it will be executed locally in $<2\text{ms}$ without ever querying the LLM.

### F. Local-Network Voice Bridge & Secure Browser Context

To enable seamless microphone access on mobile devices, modern web standards require a secure context (HTTPS) [1.3.3]. Plain HTTP connections over local Wi-Fi will forcefully reject microphone permissions with an `ERROR: NOT-ALLOWED` exception [1.3.3].

The Voice Bridge overcomes this limitation by implementing a self-healing secure layer:
1. **Automatic Certificate Generation**: On startup, if no certificate is found, the server utilizes your system's native `openssl` binary to generate a local self-signed SSL certificate (`server.pem`) bound directly to your PC's active network IP [3].
2. **HTML5 MediaRecorder Integration**: Instead of relying on proprietary, Google system libraries on the tablet, the client interface uses the completely open-source, standard-library browser `MediaRecorder` API to capture raw audio [2].
3. **Push-to-Talk (Hold to Speak)**: By capturing pointer events (`pointerdown` / `pointerup`), the browser records only while your finger is physically pressing the button [1, 2]. The exact millisecond you release your finger, it terminates recording and POSTs the raw binary audio array to your PC [1, 2].
4. **Cloud-Assisted Multimodal Transcription**: Your Python server base64-encodes the raw audio array and forwards it directly to Google's active stable `gemini-3.1-flash-lite` model over the network [2]. This completely bypasses local model compilation, packages, and dependencies while returning high-precision transcriptions with zero local overhead [2].

### G. High-Speed 1-to-1 Markdown Cheatsheet Generator (`cheatsheet`)
To replace traditional, help outputs or hardcoded aliases, the project features a dedicated cheatsheet generator located at `~/.config/local-ai/local-ai-agent/tools/blueprint`.
* **Dynamic Content Extraction**: The script reads your live `ai-context.txt` master mapping index on the fly, dynamically parses out Section Headers, and collapses multi-synonym aliases down to their single, primary trigger keyword or phrase [1.1].
* **Unified Pipeline Filtering**: It automatically strips absolute directory paths down to their base filenames and extracts raw URLs from complex command wrappers [1.1]. It is formatted as a beautiful, grid-aligned Markdown table that respects your terminal's native colors and fonts when rendered via `leaf` [1.1, 1.2.2].

---

> **Status: Alpha** | This is a minimal base template for developers, but primarily customized to make my personal system function exactly how I want.

<br><br>

