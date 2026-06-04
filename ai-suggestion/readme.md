# AI Suggestion Agent (v0.7.8)

<img alt="9nkqh39nkqh39nkq4" src="https://github.com/user-attachments/assets/02d6205c-4403-463c-acec-830305a38aec" />

`Qwen3.5-2B+` `Gemini-3.1-Flash-Lite` `OpenAI-Compatible API` `Python 3.10+` `Bash 4.0+` `Zsh 5.0+`

---

## How the Agent Works

All configurations, automations, and custom project workspaces are managed through a single master blueprint: **`ai-context.txt`**. When you trigger a mapped keyword, a cached similarity index provides a local terminal suggestion instantly. When you ask a question (using the `ai` prefix), the agent securely executes your custom local scripts using [tools], captures their outputs, and streams context-aware answers. 

When working inside a codebase, the agent compiles a safe, path-specific map of your workspace structure, allowing you to run a dedicated project-aware development copilot session on demand.

---
</div></div>
## Core Features</div></div>

* **Zero-Daemon Footprint:** No background processes or active runtimes. Runs only for the millisecond you execute a query.
* **Instant Local Suggestions:** Sørensen-Dice similarity matching suggests commands locally, completely bypassing the LLM.
* **On-Demand Workspace Agents:** Indexes project directory trees, parses architectural files, and launches codebase-aware copilot sessions.
* **Declarative Skills System:** Dynamically primes your conversational sessions with custom prompt guidelines, development roles (like system administrators or language-specific developers), and specific constraints mapped directly inside your configuration.
* **Subprocess RAG Tool Injection:** Executes custom local scripts and pipes outputs directly into the conversational AI context.
* **No Dependencies:** Written natively using Python's standard library—no `pip`, external dependencies, or heavy daemon environments required.
* **Ultra-Lightweight & Auditable:** Built for complete transparency with under 370 lines of highly readable, standard-library Python code.

---

## TUI Carousel Controls

* **`Up` / `Down` Arrow Keys:** Cycle through available suggestions
* **`Enter`:** Execute the highlighted command (or initialize a workspace if the suggestion is a directory path)
* **`Esc` / `Ctrl+C` / `Any Key`:** Cancel menu (features an anti-spam buffer flush to prevent command line leakage)

---

## Command Reference

* `ai`: Launch an interactive, multi-turn conversation session. Press `Ctrl+C` or type `exit`/`quit` to quit.
* `ai init <path>`: Index a directory and launch an interactive workspace agent primed with your codebase structure.
* `ai <query>`: Instantly answer a single question and return directly to your Bash prompt.

---

## The Brain: Configuration (`ai-context.txt`)

Add your shortcuts, dynamic tool integrations, on-demand skills, and project workspaces to `~/.config/local-ai/ai-suggestion/ai-context.txt`. The search index automatically compiles in under 2ms on your next execution.

```text
# Static Shortcut
~/.config/local-ai/media-tui/media.py ---> play music, run media

# On-Demand Prompt-Injection Skill
[TOOL] cat ~/.config/local-ai/ai-suggestion/tools/skills/sysadmin.txt ---> sysadmin, load sysadmin

# Specialized Workspace Initializer (Primes workspace with your "sysadmin" Skill!)
ai init ~/Projects/quickshell sysadmin ---> projects quickshell, projects
```

---

## Quick Setup

### 1. Install the Project Files
```bash
git clone https://github.com/j5onrf/local-ai.git ~/.config/local-ai && \
chmod +x ~/.config/local-ai/ai-suggestion/alias-ai.py && \
chmod +x ~/.config/local-ai/ai-suggestion/tools/init-projects
```

### 2. Append the Hook to Your `~/.bashrc`
```bash
echo '[ -f "$HOME/.config/local-ai/ai-suggestion/ai-hook.sh" ] && source "$HOME/.config/local-ai/ai-suggestion/ai-hook.sh"' >> ~/.bashrc
source ~/.bashrc
```

*(Optional)* Export your Gemini API key to activate cloud routing:
```bash
export GEMINI_API_KEY="AIzaSyYourGeminiKey"
```

---

<div align="center">

```diff
+ █████╗ ██╗     ███████╗██╗   ██╗ ██████╗  ██████╗ ███████╗███████╗████████╗██╗ ██████╗ ███╗   ██╗
+██╔══██╗██║     ██╔════╝██║   ██║██╔════╝ ██╔════╝ ██╔════╝██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║
+███████║██║     ███████╗██║   ██║██║  ███╗██║  ███╗█████╗  ███████╗   ██║   ██║██║   ██║██╔██╗ ██║
+██╔══██║██║     ╚════██║██║   ██║██║   ██║██║   ██║██╔══╝  ╚════██║   ██║   ██║██║   ██║██║╚██╗██║
+██║  ██║██║     ███████║╚██████╔╝╚██████╔╝╚██████╔╝███████╗███████║   ██║   ██║╚██████╔╝██║ ╚████║
+╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
-                     █████╗  ██████╗ ███████╗███╗   ██╗████████╗
-                    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
-                    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
-                    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
-                    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
-                    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝
```

</div>

---

*For detailed system architecture diagrams, custom tool development guidelines, and advanced prompt engineering, refer to the full **[documentation.md](documentation.md)**.*
