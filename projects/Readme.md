# Workspace & Session Manager Manual

Ultra-lite documentation for local agent workspaces, memory, and checkpoints.

---

## 1. Directory Structure

All session and context metadata resides inside `~/.config/local-ai/projects/`:
*   **`project-init/`**: Raw codebase structural blueprints (`.txt`).
*   **`database/`**: 
    *   `sessions.db`: SQLite database managing save states and long-term memory.
    *   `<workspace>.json`: Active conversation state log.

---

## 2. Long-Term Conversational Memory (RAG)

Sessions utilize a dual-layer memory layout to prevent token bloat:
*   **Active Window:** Locked at `8192` tokens by default (recent dialogue remains detailed).
*   **Passive Memory Bank:** Every turn is passively logged to `sessions.db` in the background.
*   **Auto-Retrieval:** If your query references a past topic, the Jaccard engine pulls the 2 most relevant past exchanges and injects them as `### Relevant Past Discussion`. The rest of the history remains asleep.

---

## 3. Checkpoints (Save States)

Save or rollback workspace states inside an active chat session.

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

