# Fusion Research Engine (Free Tier)

A compound Mixture-of-Agents (MoA) pipeline designed to maximize free-tier API endpoints. It parallelizes specialized free models—including temperature-diverse Self-Fusion paths—and synthesizes responses using Gemini 3.5 Flash as a Draco-aligned Judge.

---

## Architecture

```
       [User Prompt] ──> Mode Dispatcher
                               │
         ┌─────────────────────┴─────────────────────┐
         ▼ (coder: -c / --coder)                      ▼ (research: -r / --research)
    ├── Poolside Laguna M.1                      ├── GPT-OSS 120B (Temp 0.2) ┐ [Self-Fusion
    ├── GPT-OSS 20B                              ├── GPT-OSS 120B (Temp 0.8) ┘  Pathway]
    └── Llama 3.3 70B                            ├── Llama 3.3 70B
                                                 └── Mistral Small 24B
                                                      │
         └─────────────────────┬──────────────────────┘
                               ▼
                       [Local Audit Logs]
                               │
                               ▼
                    [Gemini 3.5 Flash Judge]
                 (Draco Benchmark Synthesis)
                               │
                               ▼
                        [Final Response]
```

---

## Setup

**Files & Directories:**
```text
~/.config/local-ai/local-ai-agent/tools/agentic/fusion/
├── f_research (executable)
├── README.md
└── logs/
```

**Environment Variables:**
```bash
export OPENROUTER_API_KEY="your_openrouter_key"
export GEMINI_API_KEY="your_gemini_key"
```

---

## Usage

Ensure the script has execution permissions (`chmod +x f_research`).

### Coding Tasks
```bash
./f_research -c "Create an async fastAPI middleware catching custom exceptions"
```

### Analytical Tasks
```bash
./f_research -r "Analyze the trade-offs of solid-state batteries vs traditional lithium-ion"
```

### Interactive Mode (On-Demand)
Launch the script with only a flag to trigger the interactive CLI prompt:
```bash
./f_research -r
```

---

## Technical Features

### 1. Self-Fusion
In `-r` mode, the engine queries the high-reasoning `openai/gpt-oss-120b:free` model twice concurrently at both low (`0.2`) and high (`0.8`) temperatures. This forces the model to explore divergent reasoning and semantic search paths, allowing the Judge to extract and preserve the most viable components of each run.

### 2. Multi-Level Fault Tolerance & Fallbacks
To combat free-tier provider instability, the script implements three defensive layers:
* **Cloud-Failover Arrays:** For OpenRouter calls, the script passes a prioritized array of fallback models (e.g., Llama 3.3 70B, Gemini 2.5 Flash). If the primary specialist is down or rate-limited, OpenRouter automatically routes the query to the next available model in the cloud.
* **Parameter Soft-Recovery:** If a restricted free-tier provider rejects custom temperature settings with an HTTP 400 Bad Request, the query interceptor automatically strips the `temperature` parameter and retries the request instantly.
* **Specialist Isolation:** Thread pool execution isolates specialist connection errors. If a specialist fails completely, the engine logs the error and allows the Judge to proceed with the successful responses rather than halting.

### 3. Strict Judge Lock (Fail-Fast)
To prevent output quality degradation, the synthesis phase is locked exclusively to **Gemini 3.5 Flash** (via native Google AI Studio or OpenRouter). If Gemini 3.5 Flash is unavailable or rate-limited, the pipeline intentionally aborts rather than falling back to legacy models that cannot handle the large context and Draco-alignment constraints.

### 4. Draco-Aligned Synthesis
The Gemini 3.5 Flash Judge synthesizes specialist reports based on four weighted criteria adapted from Perplexity's Draco Deep Research Benchmark:
* **Factual Accuracy (50%):** Validates claims, removes contradictions, and filters hallucinations.
* **Breadth, Depth & Trade-offs (25%):** Weighs opposing data to produce actionable guidance.
* **Presentation Quality (15%):** Strips conversational text and formats output cleanly.
* **Citation & Technical Integrity (10%):** Preserves specific parameters and configuration blocks.

---

## Capabilities & Limitations

* **Capabilities:** Highly effective at minimizing blind spots, validating cross-model logical conflicts, and acting as a cost-free daily research utility.
* **Limitations:** Not designed for deeply sequential or long-horizon tasks where multi-step memory and strict state tracking are required across multiple files.
```
