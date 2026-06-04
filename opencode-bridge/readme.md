# OpenCode Bridge Orchestrator

<img alt="20260603_160047" src="https://github.com/user-attachments/assets/21982191-2c00-4f89-a139-55ecb6800482" />

---

Integrating with OpenCode is a brilliant way to solve the performance bottleneck of smaller or slower local LLMs. 

When a local LLM gets overloaded with massive system prompts or 15 to 20 tool definitions upfront, its reasoning latency tanks, and it often struggles to pick the correct function. Turning off the tools in OpenCode and using your custom lightweight agent as the primary orchestrator is exactly the right move.

Instead of porting everything, this bridge maps them using an **Orchestrator-Worker pattern**. A fast local agent handles the intent routing, while OpenCode is invoked purely as a programmatic sub-agent command-line task runner when it's time to build or execute.

---

## The Bridge Architecture

Rather than treating OpenCode as an active, independent system that listens for everything, this bridge transforms it into a dedicated, isolated "execution block" inside your agent's routing layer.

```text
                      [ User Input / Goal ]
                                |
                                v
                    +-----------------------+
                    |   Custom Orchestrator |  <-- Light, Fast Local LLM
                    |    (Intent / Router)  |      (e.g., ai-suggestion)
                    +-----------------------+
                                |
                     Is it complex engineering?
                        /               \
                      YES                NO
                      /                    \
                     v                      v
          +-------------------+    +---------------------+
          | OpenCode Worker   |    | Fast Local Tools    |
          | (Bypasses LLM tool|    | (Simple edits, chat)|
          |  overhead entirely)|    +---------------------+
          +-------------------+
```

---

## Core Features

*   **Zero-Token-Drain Cloud Profile:** An ultra-lean Gemini profile that blocks automated background workspace crawling, ensuring you only use API tokens explicitly when you reference assets with inline operations (e.g., `@filename` or `!command`).
*   **Context-Isolated Local Profile:** Completely disables built-in tooling and context gathering, freeing smaller local models (like Qwen 35B) from devastating Time-To-First-Token (TTFT) initialization lag.
*   **Dynamic Cascade Runtime Selection:** The bridge engine evaluates your current shell environment at execution runtime to load the optimal performance profile automatically.

---

## System Configuration Layout

The project isolates runtime behaviors across modular blueprint files managed by a centralized configuration orchestrator:

```text
~/.config/local-ai/opencode-bridge/
├── opencode-bridge      # The execution launcher script (ocb)
├── opencode.cloud.json  # Locked-down Gemini API cloud profile
└── opencode.local.json  # Fast, toolless local inference profile
```

### Cascade Fallback Sequence

When you invoke the `ocb` command utility inside a project directory, the launcher computes the environment state using this strict order of precedence:

```text
[ocb execution]
|
├──> Is GEMINI_API_KEY set & opencode.cloud.json present?
│    └── YES: Spins up high-speed Cloud Profile.
│
├──> Is GEMINI_API_KEY empty & opencode.local.json present?
│    └── YES: Spins up context-isolated Local Profile.
│
└──> Profiles missing or unreadable?
     └── FALLBACK: Unsets profile overrides; defers natively to standard opencode.json.
```

---

## Operational Mechanics

### Environment Sourcing
The bridge natively interfaces with your active environment variables. No plain-text keys are saved inside configuration tracking files:

```bash
# Sourced directly within your ~/.bashrc or session configuration
export GEMINI_API_KEY="AIzaSyYourSecretAPIKey"
export CLOUD_MODEL="gemini-3.1-flash-lite"
```

### Execution Usage

Run the bridge command from any active code workspace:

```bash
# Automatically detects environment context & launches the optimal profile
ocb

# Temporarily force the local profile loop even if a cloud API key is present
GEMINI_API_KEY="" ocb
```
