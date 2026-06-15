# Identity Layer (`skills/identity/`)

This directory houses domain personas, situational roles, and behavioral guardrails. It decouples raw programmatic execution (what a script *does*) from contextual translation (how the agent *behaves*).

## Architecture

You can create any number of custom subdirectories here to organize your domains. The pipeline always follows a 3-step model based on a split execution workflow: **Data Acquisition** vs. **Contextual Translation**.

┌──────────────────────────┐     ┌──────────────────────────┐     ┌──────────────────────────┐
│     1. Any Script        │ ──> │ 2. identity/[domain].md  │ ──> │   3. Contextual Output   │
│  (Fetches data / logs)   │     │ (Alters Role & Nuance)   │     │  (Tailored to Audience)  │
└──────────────────────────┘     └──────────────────────────┘     └──────────────────────────┘

1. **The Scripts (Data):** A script can do anything—query a database, read local markdown logs, or scan workout metrics. It passes this raw, objective context forward.
2. **The Identity Profiles (Perspective):** The matching identity markdown file is injected to provide the exact professional lens, tonal parameters, and requirements needed to interpret that data.
3. **Contextual Output (Presentation):** The inference engine handles the final generation, streaming a response filtered through the target identity's constraints and formatting rules.

---

