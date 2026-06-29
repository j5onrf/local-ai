# Workspace & Session Manager Manual

Ultra-light documentation for local agent workspaces, checkpoints, and security isolation.

```text
~ ❯ session
[02/02] ❯ [session test ai] ai init ~/projects/ai-session-test -init
:: ↵ run  Esc: 
ℹ Compiling index map...
✔ Compressed index-map: ~/projects/ai-session-test
╭──────────────────────────────────────────────╮
│  >_ Local-AI Agent (v0.8.9.8)                │
│                                              │
│  model:     gemini-3.1-flash-lite            │
│  directory: .../projects/ai-session-test     │
│  skill:     init                             │
│  database:  26 turns (asleep)                │
╰──────────────────────────────────────────────╯
[sys] Startup context: 92 tokens | Ctrl+C to exit.

Agent: Workspace loaded. Awaiting instructions.
❯ hello how are you
[sys] Memory recall skipped.
Agent: I am functioning within the workspace and ready for your development tasks. How 
can I assist you with your code today?
❯ how do rabbits get through metal fence so easy?
Agent: Rabbits bypass metal fences primarily by exploiting physical gaps or structural 
weaknesses...
❯ /tok

[sys] Context Window: 487/8192 tokens
[sys] Usage: [█░░░░░░░░░░░░░░░░░░░] 5.9%
[sys] Remaining: 7705 tokens

❯ 
```

## 1. Directory Structure & Files

All project metadata and structural blueprints are managed cleanly without cluttering your active codebase:

*   **`~/.config/local-ai/projects/database/`**
    *   `*.db`: Isolated, project-specific SQLite databases managing your save checkpoints and memory logs.
*   **`~/your-project-folder/` (Your active workspace)**
    *   `.agent/session.json`: Securely holds the server-side interaction tracking key when using stateful Gemini APIs.
    *   `index-map-<project-name>.txt`: Codebase structural blueprint compiled on-the-fly by `tools/map/index-map` on startup.
    *   `history.md`: A human-readable chronological Markdown ledger of every input and output.

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

## 3. Security Isolation (Docker & SkillSpector)

Because local python scripts run with standard user-level permissions, it is highly recommended to run the agent in a sandboxed, zero-trust environment:

*   **Docker Containerization**: For absolute system safety, run the agent inside a sandboxed **Docker container** to isolate the execution context entirely from your host workstation's files.
*   **Vetting Agent Skills**: Never run unvetted third-party skill modules. We recommend scanning all custom or community skills with [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) before importing them to identify privilege escalations, malicious shell commands, or prompt injections.

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
*   **`/clear` / `/reset`**: Securely deletes the server-side interaction history from Google's servers, resets chat history, and clears the local `.agent/session.json` state.
*   **`/d` / `/e`**: Manually **disable** or **enable** the context-aware grammar and spellchecking engine (which uses LanguageTool cloud/local API routing with an offline dictionary fallback).
*   **`/m`**: Manually **toggle** long-term memory recall on or off.
*   **Memory & Authorization Prompt Navigation**: Both standard memory recall (`[↵ load  d: disable  Esc/Arrows: skip]`) and tool authorization (`[Y/n]`) prompts are optimized for keyboard-only terminal workflows. Pressing **`Esc`** or **`Right Arrow`** instantly triggers a **No/Skip** action—safely printing `n` or clearing lines without outputting raw escape sequences, returning you directly to your conversation.

---

## 7. Context Window Limits (Token-Slasher)

1 Token ≈ 4 Characters. Adjust the active sliding-window threshold dynamically using `AI_MAX_TOKENS`:

*   **Inline Override (One-off):**
    ```bash
    AI_MAX_TOKENS=16000 session-test(your-project)
    ```
*   **Global Override (Active Terminal):**
    ```bash
    export AI_MAX_TOKENS=16000
    ```

---

## 8. Server-Side Context Tracking (Gemini Interactions API)

When configured with a `GEMINI_API_KEY`, your agent bypasses standard stateless completion limits and communicates statefully via Google's modern `/v1beta/interactions` endpoint.

*   **Context Caching:** Your workspace directory index map is uploaded exactly *once* during initialization. Google holds this context in an high-speed server-side memory cache referenced by the ID in your local `.agent/session.json`.
*   **Bandwidth Savings:** Subsequent conversation turns only upload your new, brief query over the network rather than re-uploading the entire codebase structure, saving up to 90% in token costs and reducing average response latency.

