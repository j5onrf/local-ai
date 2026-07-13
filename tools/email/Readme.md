# Email TUI Monitor: `email-agent`

---

A standalone, local-first email monitoring utility. Integrates an interactive selection terminal (TUI) to let you instantly review unread matching tag filter messages on-device.

*   **Parallel Ingestion**: Queries multiple independent IMAP servers concurrently using standard Python thread pools (`ThreadPoolExecutor`) to eliminate sequential connection latencies.
*   **Lazy-Loaded Performance**: Fetches only lightweight headers (`RFC822.HEADER`) first, filters strictly by subject line, and only peeks a tiny 500-char plain-text snippet (`BODY.PEEK[1]<0.500>`) for matching messages (reducing bandwidth by 99.9%).
*   **Dynamic Tag Highlighting**: Scans your Subject and Preview lines, dynamically highlighting matched keywords in **bold yellow** while preserving original letter casing and surrounding text styles.
*   **Isolated & Secure**: Keeps all mailbox credentials completely self-contained within a private, local `.email` file inside the same directory.

---

### Expected Behavior

During the secure mailbox handshake and query cycle:
```console
~ ❯ email
[01/01] ❯ [email agent] ~/.config/local-ai/tools/email/email-agent | mdcat
:: ↵ run  Esc: 
⠋ Connecting to mailboxes... 
```

Once connected, your filtered inbox is rendered with matched tags highlighted:
```console
[01/01] ❯ [youremail@gmail.com] ❯ [From] ntfy <ntfy@ntfy.sh>
   Subject: "Verify your email for **ntfy**"
   Preview: Click the link below to verify this email address for your **ntfy** account: ht
   [Arrows to navigate  Esc to exit]: 
```

---

### In-Session Actions

*   **Manual Interactive TUI** (`email-agent`): Boots an arrow-key navigateable, cursor-hidden terminal selection board to browse unread filtered headers. Press **Enter**, **Esc**, or **q** to exit.

---

### Local Configuration: `.email`

Store your credentials in the same directory under `~/.config/local-ai/tools/email/.email`:

```bash
# --- Global Fallbacks ---
IMAP_SERVER=imap.gmail.com

# --- Account 1 (Personal) ---
EMAIL_USER_1=personal@gmail.com
EMAIL_APP_PASSWORD_1=tmrd aobk szfv quny
ALLOWED_TAGS_1=[tag], tag2, ntfy

# --- Account 2 (Work) ---
EMAIL_USER_2=work@gmail.com
EMAIL_APP_PASSWORD_2=tmrd aobk szfv quny
ALLOWED_TAGS_2=[alert], jira, slack
```
