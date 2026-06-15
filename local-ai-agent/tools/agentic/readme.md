# Identity Layer (`agentic/identity/`)

<img alt="Adaptive Identity Layer for AI Agents" src="https://github.com/user-attachments/assets/67553dc5-f348-48ff-9c82-7368bc5b758b" />

This directory houses domain personas, situational roles, and behavioral guardrails. It decouples raw programmatic execution (what a script *does*) from contextual translation (how the agent *behaves*).

## Architecture

You can create any number of custom subdirectories here to organize your domains. The pipeline follows a 3-step model based on a split execution workflow: **Data Acquisition** vs. **Contextual Translation**.

| 1. Data Acquisition | | 2. Contextual Translation | | 3. Presentation |
| :--- | :---: | :--- | :---: | :--- |
| **Any Script**<br>*(Fetches data / logs)* | ──> | **identity/[domain].md**<br>*(Alters Role & Nuance)* | ──> | **Contextual Output**<br>*(Tailored to Audience)* |

1. **The Scripts (Data):** A script can do anything—query a database, read local markdown logs, or scan workout metrics. It passes this raw, objective context forward.
2. **The Identity Profiles (Perspective):** The matching identity markdown file is injected to provide the exact professional lens, tonal parameters, and requirements needed to interpret that data.
3. **Contextual Output (Presentation):** The inference engine handles the final generation, streaming a response filtered through the target identity's constraints and formatting rules.

---

