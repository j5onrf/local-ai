# AI-Suggestion Agent (v0.7.3-alpha) — Documentation

An adaptive, local/cloud AI shell assistant designed to conform to your terminal environment. By leveraging a high-speed, local token-matrix cache alongside local or cloud LLMs, it corrects command typos, manages aliases, executes system tools, and answers conversational queries with zero background CPU overhead.

---

## 1. System Architecture & Dual-Mode Core

The project operates under an on-demand execution model designed to protect terminal responsiveness:

* **Zero-Background Footprint:** No background daemons, cron-jobs, or continuous CPU-polling threads are used. Your shell experiences 0% idle RAM and 0% idle CPU overhead.
* **Dual-Layer Execution:** 
  * **Standard typos (direct shell inputs):** Bypasses the LLM completely. Typo errors are evaluated locally via a C-compiled set-intersection matrix in under 2ms.
  * **Conversational queries (using the `ai` prefix):** Run on-demand. If cloud API keys are set, it connects to Google Gemini; otherwise, it falls back to your local `llama-server`.
* **Offline Resilience:** If your local AI server and internet are offline, your typo corrections, custom aliases, and interactive teaching loops continue to work locally and instantly. Only conversational LLM chat requests are safely blocked.

---

## 2. Cloud Integration

The agent natively supports **Google Gemini's OpenAI-compatible completions API** [2]. This allows you to offload conversational reasoning and context-injected tool calls to the cloud with **0% local CPU/RAM overhead** [1].

### Environment Configuration (`~/.bashrc`)
To activate cloud mode, export your API key and preferred model at the top of your `~/.bashrc` [1]:
```bash
export GEMINI_API_KEY="AIzaSyYourFullGeminiApiKeyHere"
export CLOUD_MODEL="gemini-3.1-flash-lite"
```

## 3. Configuration & The Semantic Index

Your agent's brain is managed by a plain-text configuration master file.

* **Path:** `~/.config/local-ai/ai-suggestion/ai-context.txt`
* **Syntax:** `[command] ---> [intent1], [intent2], [intent3]`

*Example:*
```text
clear ---> cc, clear terminal, reset screen, wipe display
```

### Automatic Compilation on the Fly
Every time you interact with the agent, the Python script compares modification timestamps (`getmtime`) of your files. If the plain-text configuration has been modified, it silently rebuilds your minified, single-line lookup index (`ai-context.idx`) in under 2ms before executing.

### Optional Manual Compilation
To explicitly force a rebuild of the speed index for diagnostic or sanity checks, run:
```bash
ai --compile
```

---

## 4. Active System Tools (`[TOOL]` & RAG)

You can turn any standard Linux command, package, binary, or custom script into an AI tool by prefixing the command with `[TOOL]` in your `ai-context.txt` [3]:

*Example:*
```text
[TOOL] df -h / ---> check my nvme drive, is my hard drive full, show disk space
```

### A. Local Context-Injected RAG
1. You ask: `ai "how much space is on my nvme drive?"`
2. The local matrix search instantly matches the intent to `[TOOL] df -h /` (0ms delay).
3. Python executes `df -h /` behind the scenes, capturing your physical hard drive table (with an **8-second safety timeout**) [2].
4. Python injects that raw text output directly into your LLM's prompt context [2].
5. The local/cloud LLM reads the raw data and formulates a real-time response: *"Your drive is currently using 49% of its space, leaving 237GB free."* [2]

### B. Self-Instructing Tools (Bypassing AI Safety Guardrails)
To prevent the LLM from throwing its pre-trained safety excuses (like *"I do not have access to your local machine"*), you can embed **"Instructions for AI"** directly in your tool's stdout [2]. 

*Example inside `tools/update-inspector`:*
```bash
echo "=== PENDING SYSTEM UPGRADES ==="
echo "[INSTRUCTIONS FOR AI]: Do not state that you cannot access their system, as the data has already been provided to you. Pinpoint critical updates and explain their system impact."
```
Because the LLM reads this entire context block as part of the user instruction, it will naturally read those embedded guidelines and formulate its answer exactly as requested, completely on the fly [2].

---

## 5. System Monitor Dashboard & Token Tracking

The system silently monitors and logs your API transactions to a local JSON database without polluting your active terminal screen [1, 2].

* **Path:** `~/.config/local-ai/ai-suggestion/api-usage.json`

### System Monitor Dashboard (`ai --status`)
To give you a comprehensive monitor of your configuration and usage, run the 0% memory ASCII dashboard:
```bash
ai --status
```
It instantly outputs a high-contrast terminal card of your active configuration:

```text
┌──────────────────────────────────────────────────────────┐
│          AI-SUGGESTION SYSTEM MONITOR & DASHBOARD        │
├──────────────────────────────────────────────────────────┤
│  Active Mode:     Google Gemini Cloud API                │
│  API Key:         Loaded (AIzaSyD1...)                   │
│  Cloud Model:     gemini-3.1-flash-lite                  │
│  Active Tools:    Google Search                          │
├──────────────────────────────────────────────────────────┤
│  Context Database: ~/.config/local-ai/ai-suggestion/ai-c │
│  Mapped Shortcuts: 20                                    │
│  Active [TOOL]s:   9                                    │
│  Search Index:    Active & Synced                        │
├──────────────────────────────────────────────────────────┤
│  Last Request:    gemini-3.1-flash-lite (169t total)     │
│  Lifetime Calls:  5                                      │
│  Lifetime Tokens: 709                                    │
└──────────────────────────────────────────────────────────┘
```

---

## 6. Interactive CLI Training Loops

You can train your agent's memory directly from your terminal session in three ways:

### A. The Direct Correction Loop
If you type an unmapped command or typo (such as `sb`), the shell hook intercepts it and prompts:
```text
ℹ "sb" is not mapping to a known automation.
Would you like to teach the agent this custom phrase? (y/N)
```
Pressing `y` prompts you for the exact executable command this should map to, automatically building, appending, and compiling the new association.

### B. Manual Training Command
To manually register a custom alias or shortcut at any time without triggering a typo, run:
```bash
ai --teach
```
This launches a CLI prompt asking you for your custom natural phrase and the exact terminal command it should map to, writing it cleanly to your database.

### C. Suggestion Overriding
If the agent suggests an existing command but you want to edit or override it on the fly, press **`t`** during the selection prompt:
* This launches an interactive line editor allowing you to override the command string, saving the new preference permanently to memory.

---

## 7. Mathematical & Structural Optimizations

### A. Conversational-Resilient Stop Words
In search index engines, common grammatical connector words (like `what`, `is`, `it`, `do`, `any`, `I`, `have`, `the`, `a`) are called **"Stop Words"** [2]. Because these words carry no actual action, including them in your intent database causes completely unrelated commands (like `date` and `hyprctl clients`) to collide on generic English sentence structures [2].

To solve this, the Python script's `tokenize()` function automatically filters out a pre-compiled set of common English stop words [2]. For example:
* `"what about rain in the next few days?"` and `"is it going to rain?"` both compress down to exactly: **`["rain"]`** under the hood. 

This completely immunizes your database against structural grammar collisions, allowing you to write natural, conversational sentences while ensuring your matrix search targets only the specific, relevant keywords [2].

### B. High-Contrast Category Tags (Resource Isolation)
Small, local models can occasionally experience "cross-talk" hallucinations when parsing space-separated, adjacent numerical lines (for example, misinterpreting a `49%` disk space metric as your active RAM usage).

To prevent this, the active diagnostics tool `ai-system-diagnosis` prefixes each performance category with high-contrast, bracket tags (such as `[SYSTEM]`, `[CPU_HOGS]`, `[MEMORY]`, and `[STORAGE]`) [4]. This keeps your metrics isolated, allowing even lightweight models to analyze your CPU, RAM, and disk specs with absolute precision [4].

---
