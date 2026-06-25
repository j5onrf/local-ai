# Workspace & Session Manager Manual

Ultra-lite documentation for local agent workspaces, memory, checkpoints, and RAG tools.

```text
~ ❯ sess
[01/01] ❯ [projects session] ai init ~/.config/local-ai/projects/session-test -init
:: ↵ run  Esc: 
ℹ Compiling index map...
✔ Compressed index-map compiled successfully at: ~/.config/local-ai/projects/session-test/index-map-session-test.txt
AI Agent Session Initialized | Context Loaded [init] | Ctrl+C to exit.
[sys] Startup context: 178 tokens | Database memory: 17 turns (asleep)

Agent: Workspace loaded. Awaiting instructions.
❯ 
```

---

## 1. Directory Structure & Files

All project metadata and structural blueprints are managed cleanly without cluttering your active codebase:

*   **`~/.config/local-ai/projects/database/`**
    *   `*.db`: Isolated, project-specific SQLite databases managing your save checkpoints and memory logs.
*   **`~/your-project-folder/` (Your active workspace)**
    *   `index-map-<project-name>.txt`: Codebase structural blueprint compiled on-the-fly by `tools/map/index-map` on startup.
    *   `history.md`: A human-readable chronological Markdown ledger of every input and output.

*(Active conversational histories are held strictly in RAM during execution. No temporary JSON files are written to your drive).*

---

## 2. Dynamic File Context Insertion (On-Demand RAG)

Avoid manual copy-pasting. You can pull the full contents of any file directly into the model's active context on-the-fly using the integrated local tool execution pipeline:

*   **Command:** Type this inside your active chat:
    ```text
    ❯ view file <filename>
    ```
    *(Or `read file <filename>` / `show file <filename>`)*
*   **Execution:** The agent runs a local `cat` behind the scenes and injects the raw file contents into the system context for immediate reasoning.

---

## 3. Long-Term Conversational Memory (Recall)

Sessions utilize an on-demand, gated memory layout to prevent token bloat:

*   **Active Window:** Capped at `8192` tokens and managed dynamically in RAM.
*   **Passive Memory Bank**: Every turn is logged to your workspace's unique SQLite `.db` database.
*   **Selective Recall**: If your query matches a past turn's keywords, the agent prompts you before loading:
    ```text
    [sys] Recall past memory: "Please review this Python..."? [↵ load  d: disable  Esc]: 
    ```
    *   Press **`Enter`** to approve and inject the memory.
    *   Press **`d`** to skip and **disable** memory recall for the rest of your session. *(Type `/m` at your prompt to re-enable).*
    *   Press **`Esc`** to skip the recall but **proceed** with your original query.

---

## 4. Checkpoints (Save States & Timelines)

Save or rollback workspace states inside an active chat session. Checkpoints bypass the filesystem and stream directly to SQLite.

*   **Save Current State:**
    ```text
    ❯ -save <tag>
    ```
*   **Rollback State:**
    ```text
    ❯ -load
    ```
    *(Or `-timeline`). Displays your saved snapshots. Type the target index number (e.g., `0`) and press **`Enter`**. The interface is wrapped in a fail-safe input loop to prevent accidental menu crashes if an invalid key or arrow key is pressed.*

---

## 5. On-Demand Specialist Skills

Inject custom, role-based onboarding instructions dynamically during any active session.

*   **Search and Load:** Type this command inside your chat:
    ```text
    ❯ /skill <search_term>
    ```
    *(Or `/s <search_term>`. Use `/skill` with no term to list your entire skill library).*
*   **Selection & Execution:** Use your `Up` and `Down` arrow keys to cycle through matches, then press `Enter` to apply or `Esc` to cancel.

---

## 6. In-Session Toggle & Diagnostic Commands

Type these quick commands during any active conversation to adjust your settings on-the-fly:

*   **`/tok`**: Displays your live context window usage in a visual progress bar.
*   **`/d` / `/e`**: Manually **disable** or **enable** the offline spellcheck engine.
*   **`/m`**: Manually **toggle** long-term memory recall on or off.

```text
❯ /tok

[sys] Context Window: 115/8192 tokens
[sys] Usage: [░░░░░░░░░░░░░░░░░░░░] 1.4%
[sys] Remaining: 8077 tokens

❯ 
```

---

## 7. Context Window Limits (Token-Slasher)

1 Token ≈ 4 Characters. Adjust the active sliding-window threshold dynamically using `AI_MAX_TOKENS`:

*   **Inline Override (One-off):**
    ```bash
    AI_MAX_TOKENS=16000 sess
    ```
*   **Global Override (Active Terminal):**
    ```bash
    export AI_MAX_TOKENS=16000
    ```

