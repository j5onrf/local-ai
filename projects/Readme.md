# Workspace & Session Manager Manual

Ultra-lite documentation for local agent workspaces, memory, and checkpoints.

---

## 1. Directory Structure

All session and context metadata resides inside `~/.config/local-ai/projects/`:
*   **`project-init/`**: Raw codebase structural blueprints (`.txt`).
*   **`database/`**: 
    *   `sessions.db`: SQLite database managing save states and long-term memory.

*(Active conversational histories are held strictly in RAM during execution.*

---

## 2. Long-Term Conversational Memory (RAG)

Sessions utilize an on-demand memory layout to prevent token overages:
*   **Active Window:** Kept in-memory (RAM) during your active session and capped at `8192` tokens. 
*   **Passive Memory Bank:** Every turn is passively logged to `sessions.db` in the background.
*   **Auto-Retrieval:** If your query references a past topic, the Jaccard engine pulls the 2 most relevant past exchanges and prompts you to recall them. If approved, they are injected as `### Relevant Past Discussion` [4]. The rest of your history remains asleep.

---

## 3. Checkpoints (Save States)

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

## 4. Context Control (Token-Slasher)

1 Token ≈ 4 Characters. Adjust the active memory window dynamically using `AI_MAX_TOKENS`:

*   **Inline Override (One-off):**
    ```bash
    AI_MAX_TOKENS=64000 session test
    ```
*   **Global Override (Active Terminal):**
    ```bash
    export AI_MAX_TOKENS=64000
    ```
