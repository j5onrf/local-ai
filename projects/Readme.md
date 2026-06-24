# Agent Workspace & Session Manager

Documentation for managing codebase-aware agent sessions, checkpoints, and token limits.

---

## 1. Directory Structure

The `/home/user/.config/local-ai/projects/` directory is organized into isolated, backup-ready subfolders:

*   **`project-init/`**
    *   Stores your compiled codebase structural maps (`.txt`).
    *   Generated on-the-fly by `tools/init-projects` when you run `ai init` or `session test`.
*   **`database/`**
    *   `sessions.db`: The SQLite database managing your archived checkpoints.
    *   `<workspace-signature>.json`: The active, raw chat history state log.
*   **`Readme.md`**
    *   This documentation file.

---

## 2. Checkpoint-Branching (Save States)

You can save, list, and restore checkpoints (Git-like timeline states) natively during any active workspace (`--talk-chat`) session.

### Save a Checkpoint
To save your current conversational timeline state, type:
```text
❯ -save <checkpoint_name>
```
*   *Example:* `❯ -save feature_added_v1`
*   This instantly commits a copy of your chat history array to the SQLite database.

### View & Restore a Checkpoint
To view available checkpoints or roll back your active session timeline, type:
```text
❯ -timeline
```
*(or `-load`)*
*   A numbered list of checkpoints will display.
*   Press the corresponding index key (e.g., `0`) to restore that exact state.
*   *Tip:* Rolling back to a previous clean state deletes unwanted conversational noise from the model's active memory, keeping your prompt clean.

---

## 3. Dynamic Token-Slasher Context Control

To prevent your agent sessions from consuming massive amounts of tokens as they grow, your orchestrator dynamically prunes conversational history right before invoking the LLM api.

*   **Heuristic:** 1 Token ≈ 4 Characters of text.
*   **Default Context Cap:** `8192` tokens.

### How to Increase/Adjust the Context Window
You can dynamically adjust the sliding context window limit on-the-fly using the `AI_MAX_TOKENS` environment variable.

*   **Temporary Override (Single Run):**
    Scale up your window (e.g., up to 64K tokens) for a specific session:
    ```bash
    AI_MAX_TOKENS=64000 session test
    ```
    Or up to 128K tokens for deep-context models (like Hermes or Gemini):
    ```bash
    AI_MAX_TOKENS=128000 ai init .
    ```

*   **Global Override (Current Terminal Session):**
    Set the limit globally for all subsequent agent runs in your active terminal:
    ```bash
    export AI_MAX_TOKENS=64000
    ```
