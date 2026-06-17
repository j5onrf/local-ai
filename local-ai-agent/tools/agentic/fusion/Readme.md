# Fusion Research Engine (Free Tier)

A compound Mixture-of-Agents (MoA) pipeline designed to maximize free-tier API endpoints. It parallelizes specialized free models—including temperature-diverse Self-Fusion paths—and synthesizes responses using a native, cascading Gemini Flash Judge.

---

## Architecture

```
       [User Prompt] ──> Mode Dispatcher
                               │
         ┌─────────────────────┴─────────────────────┐
         ▼ (coder: -c )                      ▼ (research: -r )
    ├── Poolside Laguna M.1                      ├── GPT-OSS 120B (Temp 0.2) ┐ [Self-Fusion
    ├── GPT-OSS 20B                              ├── GPT-OSS 120B (Temp 0.8) ┘  Pathway]
    └── Qwen3 Coder                              ├── DeepSeek R1
                                                 └── Llama 3.3 70B
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
                        [Final Response] ──> logs/final_output.md
```

---

## Setup

**Files & Directories:**
```text
~/.config/local-ai/local-ai-agent/tools/agentic/fusion/
├── f_research (executable)
├── README.md
└── logs/
    └── final_output.md (most recent synthesis)
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
To input your prompt on the fly with safe cursor containment, run the script with only a flag:
```bash
./f_research -r
```

---

## Technical Features

### 1. Self-Fusion
In `-r` mode, the engine queries the high-reasoning `openai/gpt-oss-120b:free` model twice concurrently at both low (`0.2`) and high (`0.8`) temperatures. This forces the model to explore divergent reasoning and semantic search paths, allowing the Judge to extract and preserve the most viable components of each run.

### 2. Multi-Level Fault Tolerance & Fallbacks
To combat free-tier provider instability, the script implements three defensive layers:
* **Cloud-Failover Arrays:** For OpenRouter calls, the script passes a prioritized array of fallback models (e.g., Llama 3.3 70B). If the primary specialist is down or rate-limited, OpenRouter automatically routes the query to the next available model in the cloud.
* **Parameter Soft-Recovery:** If a restricted free-tier provider rejects custom temperature settings with an HTTP 400 Bad Request, the query interceptor automatically strips the `temperature` parameter and retries the request instantly.
* **Specialist Isolation:** Thread pool execution isolates specialist connection errors, preserving successful runs to write to disk.

### 3. Cascading Native Judge (Fail-Safe)
The synthesis phase is locked strictly to your native Google key (`GEMINI_API_KEY`), removing OpenRouter dependencies to prevent payment-required (402) errors. To ensure stable completion, the Judge implements a cascading native fallback chain:
* **Primary:** `gemini-3.5-flash`
* **Fallback:** `gemini-3.1-flash-lite` (if 3.5 suffers a transient 503 or 429 outage)

### 4. Draco-Aligned Synthesis & Export
The Judge synthesizes reports based on four weighted criteria adapted from Perplexity's Draco Deep Research Benchmark:
* **Factual Accuracy (50%):** Validates claims, removes contradictions, and filters hallucinations.
* **Breadth, Depth & Trade-offs (25%):** Weighs opposing data to produce actionable guidance.
* **Presentation Quality (15%):** Strips conversational text and formats output cleanly.
* **Citation & Technical Integrity (10%):** Preserves specific parameters and configuration blocks.

Upon completion, the final synthesized Markdown response is written directly to **`logs/final_output.md`**, ready for on-demand paging.

