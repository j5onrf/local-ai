# Department Specialist Skills

Documentation for building, organizing, and executing dynamic, on-demand specialist skills.

---

## 1. Directory Structure

The `/home/j5/.config/local-ai/skills/dept/` directory holds your specialized, role-based "onboarding guides." You can organize them recursively to maintain clean organizational lines:

```text
skills/dept/
├── Readme.md (this manual)
├── finance/
│   └── mfr.md (monthly financial review guide)
├── legal/
│   └── contract-auditor.md
└── reviewer.md (general code reviewer)
```

---

## 2. Standardized Skill Header (The Contract)

To allow your agent to index and discover your skills without reading entire documents, every `skill.md` file must define its triggers on the **first line** of the file using your standard delimiter:

```markdown
# [SKILL] <name> ---> <intent_trigger_1>, <intent_trigger_2>, <intent_trigger_3>
```

*   **Example (`reviewer.md`):**
    ```markdown
    # [SKILL] reviewer ---> review, check, audit, bug, standard, code review
    ```
*   **The Blueprint Cache:** The agent reads only this first line at startup (costs 0 active conversational tokens). It tokenizes the triggers to match your `/skill` searches.

---

## 3. On-Demand Activation

Dynamic skills are strictly **on-demand**. No unsolicited automated prompts or context-window hijacking.

### Search and Load a Skill
While inside an active conversation session (`ai` or `session test`), type:
```text
❯ /skill <search_term>
```
*(or `/s <search_term>`)*

*   **List All Skills:** Type `/skill` or `/s` with no search term to list your entire department skill library.
*   **Arrow-Key Carousel:** Use your `Up` and `Down` arrow keys to cycle through matched skills.
*   **Execution:** Press `Enter` to dynamically inject the chosen skill into your current session's active system prompt, or press `Esc` to cancel.

---

## 4. Operational Demonstration

Here is an actual trace of what to expect when searching, injecting, and executing an on-demand department skill inside your terminal session:

```text
~ ❯ ai
Local AI Conversation Mode. Ctrl+C to quit.

❯ /s review
[01/01] ❯ [skill] reviewer (reviewer.md)
   "1. Analyze all incoming code for syntax errors, logic flaws, and structural bloat." [↵ load  Esc]: 
```
