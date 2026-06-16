### Conceptual Alignment

| File Placeholder | Proposed Real Name | Primary Objective | Maps to Folder |
| :--- | :--- | :--- | :--- |
| `prom-te.md` | `Technical & Execution` | Precise, functional output with rigid logic constraints | `coding` / `system` |
| `prom-sa.md` | `Synthesis & Analysis` | Deep objective evaluation, fact-finding, and reasoning | `research` / `notes` |
| `prom-od.md` | `Orchestration & Delegation` | Task routing, modular instructions, and state tracking | `sub-agents` / `system` |

---

### Implementation Advice
To make these files active tools:
1. When your agent receives a request, it should read `scaf.md` to establish the base layout logic.
2. It can then classify the user's intent to decide whether it needs `prom-te.md`, `prom-sa.md`, or `prom-od.md`.
3. It fills in the template variables (e.g., `{{LANGUAGE}}`, `{{OBJECTIVE}}`, etc.) and prepends or injects this newly built prompt before querying the main model.
