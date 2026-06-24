# Workspace & Session Manager Manual

Ultra-lite documentation for local agent workspaces, memory, and checkpoints.

```text
~ ❯ session test
[01/01] ❯ [projects session] ai init ~/.config/local-ai/projects/session-test
:: ↵ run  Esc: 
Project 'session-test' indexed successfully.
AI Agent Session Initialized | Context Loaded | Ctrl+C to exit.
[sys] Startup context: 57 tokens | Database memory: 23 turns (asleep)

Agent: I am ready to assist with your development tasks...
❯ 
```

## 1. Directory Structure

All metadata is isolated inside your configuration tree to prevent polluting your codebase:
*   **`~/.config/local-ai/projects/project-init/`**
    *   `*.txt`: Compiled codebase structural blueprints generated on-the-fly by `tools/init-projects` [1].
*   **`~/.config/local-ai/projects/database/`**
    *   `*.db`: Isolated, project-specific SQLite databases managing your save states and memory logs [4].
*   **`~/your-project-folder/` (Your active workspace)**
    *   `history.md`: A human-readable chronological Markdown ledger of your conversation [1].

*(Active conversational histories are held strictly in RAM during execution. No temporary JSON files are written to your drive).*

---

## 2. On-Demand Specialist Skills

You can dynamically inject custom, role-based onboarding guides (e.g., finance reviews, legal rules) during any active session on-the-fly [1, 2].

*   **Search and Load:** Type this command inside your chat [1]:
    ```text
    ❯ /skill <search_term>
    ```
    *(Or `/s <search_term>`. Use `/skill` with no term to list your entire department skill library).*
*   **Carousel Selection:** Use your `Up` and `Down` arrow keys to cycle through matches, displaying the file path and live description [1].
*   **Execution:** Press `Enter` to dynamically inject the skill instructions into your active system prompt, or `Esc` to cancel [1].

---

## 3. Long-Term Conversational Memory (RAG)

Sessions utilize an on-demand, gated memory layout to prevent token bloat:
*   **Active Window:** Kept in RAM during execution and capped at `8192` tokens. 
*   **Passive Memory Bank:** Every turn is passively logged to your workspace's unique `.db` file in the background [4].
*   **Auto-Retrieval:** If your query references a past topic, your terminal will stop and prompt you for permission before recalling [4]:
    ```text
    [sys] Recall past memory: "Please review this Python..."? [↵ load  Esc]: 
    ```
    *   Press **`Enter`** to approve and inject [4].
    *   Press **`Esc`** to completely skip the recall and abort your turn [4], returning you to a clean prompt `❯` without making a single LLM request.

---

## 4. Checkpoints (Save States)

Save or rollback workspace states inside an active chat session. Checkpoints are piped directly to/from SQLite using standard streams, completely bypassing the filesystem [4].

*   **Save current state:**
    ```text
    ❯ -save <tag>
    ```
*   **Rollback / List timeline:**
    ```text
    ❯ -timeline
    ```
    *(Or `-load`. Select an index key to restore history and erase conversational drift).*

---

## 5. Context Control (Token-Slasher)

1 Token ≈ 4 Characters. Adjust the active memory window dynamically using `AI_MAX_TOKENS`:

*   **Inline Override (One-off):**
    ```bash
    AI_MAX_TOKENS=64000 session test
    ```
*   **Global Override (Active Terminal):**
    ```bash
    export AI_MAX_TOKENS=64000
    ```
