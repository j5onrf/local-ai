# Fusion Research Engine (Free Tier)

A compound Mixture-of-Agents (MoA) pipeline designed to maximize free-tier API endpoints. It parallelizes specialized free models—including temperature-diverse Self-Fusion paths—and synthesizes responses using Gemini 3.5 Flash as a Draco-aligned Judge.

---

## Architecture

```
       [User Prompt] ──> Mode Dispatcher
                               │
             ┌─────────────────┴─────────────────┐
             ▼ (coder)                           ▼ (research)
        ├── Poolside Laguna M.1             ├── GPT-OSS 120B (Temp 0.2) ┐ [Self-Fusion
        ├── Qwen3 Coder                     ├── GPT-OSS 120B (Temp 0.8) ┘  Pathway]
        └── GPT-OSS 120B                    ├── DeepSeek R1
                                            └── Nemotron-3 Super
             │                                   │
             └─────────────────┬─────────────────┘
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
├── fusion_research.py
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

**Coding Tasks:**
```bash
python3 fusion_research.py --mode coder "Create an async fastAPI middleware catching custom exceptions"
```

**Analytical Tasks:**
```bash
python3 fusion_research.py --mode research "Analyze the trade-offs of solid-state batteries vs lithium-ion"
```

---

## Technical Features

### 1. Self-Fusion
In `research` mode, the engine queries the high-reasoning `openai/gpt-oss-120b:free` model twice concurrently at both low (`0.2`) and high (`0.8`) temperatures. This forces the model to explore divergent reasoning and semantic search paths, allowing the Judge to extract and preserve the most viable components of each run.

### 2. Draco-Aligned Synthesis
The Gemini Flash Judge acts as an analytical filter, grading and synthesizing reports based on four weighted criteria adapted from Perplexity's Draco Deep Research Benchmark:
* **Factual Accuracy (50%):** Validates claims, removes contradictions, and filters hallucinations.
* **Breadth, Depth & Trade-offs (25%):** Weighs opposing data to produce actionable guidance.
* **Presentation Quality (15%):** Strips conversational text and formats output cleanly.
* **Citation & Technical Integrity (10%):** Preserves specific parameters and configuration blocks.

### 3. Fault-Tolerant Logging
Raw specialist reports are logged to `./logs/fusion_research_[mode]_[YYYYMMDD_HHMMSS].md` before synthesis. If a free-tier endpoint fails or suffers a rate limit (HTTP 429), the error is isolated within the logs, and the Judge generates a final response using the remaining successful drafts.

---

## Capabilities & Limitations

* **Capabilities:** Highly effective at minimizing blind spots, validating cross-model logical conflicts, and acting as a cost-free daily research utility.
* **Limitations:** Not designed for deeply sequential or long-horizon tasks where multi-step memory and strict state tracking are required across multiple files.

