# Local-AI Agent (v0.7.9)

<div align="center">

```
                           ██╗      ██████╗  ██████╗  █████╗ ██╗               █████╗ ██╗   
                           ██║     ██╔═══██╗██╔════╝ ██╔══██╗██║              ██╔══██╗██║   
                           ██║     ██║   ██║██║      ███████║██║   ███████╗   ███████║██║   
                           ██║     ██║   ██║██║      ██╔══██║██║   ╚══════╝   ██╔══██║██║   
                           ███████╗╚██████╔╝╚██████╗ ██║  ██║███████╗         ██║  ██║██║   
                        ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝         ╚═╝  ╚═╝╚═╝
                            
                          █████╗  ██████╗ ███████╗███╗   ██╗████████╗
                         ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
                         ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
                         ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
                         ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
                         ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
```

</div>

`Laguna-M.1` `Qwen3-Coder` `Gemini-3.1-Flash-Lite` `Python 3.10+` `Bash 4.0+` `Zsh 5.0+`

---

## How the Agent Works

All configurations, automations, and custom project workspaces are managed through a single plain-text master blueprint: **`ai-context.txt`**. The agent resolves your inputs into one of four execution paradigms:

* **No Session (Direct suggestions)**: Typing custom commands or shortcuts prompts a local set-intersection matrix to suggest options instantly without querying an LLM.
* **Single-Turn Agent (`ai <query>`)**: Typing `ai <query>` instantly answers a single question and returns you directly to your Bash prompt, silently running local diagnostic tools to gather context when your keywords are matched.
* **Multi-Turn Chat (`ai` alone)**: Typing `ai` alone initiates an interactive, persistent conversation session with local state preservation and multi-turn context memory.
* **Workspace Agents (`ai init <path>`)**: Compiles a path-specific structural tree of your repository, launching a dedicated, codebase-aware co-pilot session.

---

## Core Features

* **Zero-Daemon Footprint:** No background processes, polling threads, or active runtimes. Consumes 0% idle RAM and 0% idle CPU.
* **Instant Local Suggestions:** Norwegian/Dice-coefficient token matching suggests custom commands locally in under 2ms, completely bypassing the LLM.
* **Cascading Fallback Chain:** Seamlessly cascades through configured cloud API keys (Gemini $\rightarrow$ OpenRouter $\rightarrow$ Custom Cloud API) down to local AI servers (such as `Ollama` or `llama.cpp`) if a service goes offline.
* **OpenRouter Model Failover:** Automatically configures multiple free backup models inside the OpenRouter API payload, failing over from specific coding models (like `poolside/laguna-m.1:free`) to general routers if the target is congested.
* **Subprocess RAG Tool Injection (`[TOOL]`):** Executes local scripts (such as diagnostic utilities or API status checks) behind the scenes, feeding their standard output straight into the LLM context for real-time system troubleshooting.
* **Collision-Resilient Search Math:** Restricts the subset-matching score bonus to queries where the matched words cover at least 50% of the active search, preventing conversational sentences from accidentally triggering short command aliases.
* **No Dependencies:** Written natively using Python's standard library—no `pip` installs or complex package runtimes required.
* **Ultra-Lightweight & Auditable:** Built with complete transparency in under 390 lines of highly readable, standard-library Python code.

---

## TUI Carousel Controls

* **`Up` / `Down` Arrow Keys:** Cycle through available ranked suggestions
* **`Enter`:** Execute the highlighted command (or initialize a workspace if the suggestion is a directory path)
* **`Esc` / `Ctrl+C` / `Any Key`:** Cancel menu (features an anti-spam buffer flush to prevent command line leakage)

---

## Command Reference

* `ai`: Launch an interactive, multi-turn conversation session. Press `Ctrl+C` or type `exit`/`quit` to quit.
* `ai init <path>`: Index a directory and launch an interactive workspace agent primed with your codebase structure.
* `ai <query>`: Instantly answer a single question and return directly to your Bash prompt.

---

## The Brain: Configuration (`ai-context.txt`)

Add your shortcuts, dynamic tool integrations, and project workspaces to `~/.config/local-ai/local-ai-agent/ai-context.txt`. The search index automatically compiles in under 2ms on your next execution.

```text
# --- AI Deep Research TUI ---
~/.config/local-ai/research-tui/deep-research ---> ai-research, deep research, research, deep-research

# Context-Injected Diagnostic Tool (Section 3)
[TOOL] ~/.config/local-ai/local-ai-agent/tools/agentic/ai-status ---> ai-status agentic, ai stack diagnostics

# Specialized Workspace Initializer (Primes workspace with your "coder" Skill!)
ai init ~/Projects/quickshell coder ---> projects quickshell, projects
```

---

## Quick Setup

### 1. Install the Project Files
```bash
git clone https://github.com/j5onrf/local-ai.git ~/.config/local-ai
```

### 2. Append the Hook to Your `~/.bashrc`
```bash
echo '[ -f "$HOME/.config/local-ai/local-ai-agent/ai-hook.sh" ] && source "$HOME/.config/local-ai/local-ai-agent/ai-hook.sh"' >> ~/.bashrc
source ~/.bashrc
```

*(Optional)* Export your cloud API keys to activate cloud routing and fallback logic:
```bash
export GEMINI_API_KEY="AIzaSyYourGeminiKey"
export OPENROUTER_API_KEY="sk-or-v1-YourOpenRouterKey"
```

---

<div align="center">

```
                     ██████╗  █████╗ ██╗      █████╗ ███╗   ███╗███████╗██████╗ ███████╗██████╗ 
                     ██╔══██╗██╔══██╗██║     ██╔══██╗████╗ ████║██╔════╝██╔══██╗██╔════╝██╔══██╗
                     ██████╔╝███████║██║     ███████║██╔████╔██║█████╗  ██║  ██║█████╗  ██║  ██║
                     ██╔═══╝ ██╔══██║██║     ██╔══██║██║╚██╔╝██║██╔══╝  ██║  ██║██╔══╝  ██║  ██║
                     ██║     ██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████╗██████╔╝███████╗██████╔╝
                     ╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚═════╝ ╚══════╝╚═════╝
                    𝘐𝘯𝘷𝘦𝘯𝘵𝘰𝘳 𝘰𝘧 Carousels
```

</div>

---

*For detailed system architecture diagrams, custom tool development guidelines, and advanced prompt engineering, refer to the full **[documentation.md](documentation.md)**.*


