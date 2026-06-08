# Local-AI Agent (v0.7.9)

<img alt="9nkqh39nkqh39nkq4" src="https://github.com/user-attachments/assets/02d6205c-4403-463c-acec-830305a38aec" />

`Laguna-M.1` `Qwen3-Coder` `Gemini-3.1-Flash-Lite` `Python 3.10+` `Bash / Zsh 5.0+`

---

## How the Agent Works

All configurations, automations, and custom project workspaces are managed through a single plain-text master blueprint: **`ai-context.txt`**. The agent resolves your inputs into one of four execution paradigms:

* **No Session (Direct suggestions)**: Typing custom commands or shortcuts prompts a local set-intersection matrix to suggest options instantly without querying an LLM.
* **Single-Turn Agent (`ai <query>`)**: Typing `ai <query>` instantly answers a single question and returns you directly to your Bash prompt, silently running local diagnostic tools to gather context when your keywords are matched.
* **Multi-Turn Chat (`ai` alone)**: Typing `ai` alone initiates an interactive, persistent conversation session with local state preservation and multi-turn context memory.
* **Workspace Agents (`ai init <path>`)**: Compiles a path-specific structural tree of your repository, launching a dedicated, codebase-aware co-pilot session.

---

## Core Features

| Pillar | Capability | Description |
| :--- | :--- | :--- |
| **Performance** | **Zero-Daemon Footprint** | Consumes 0% idle CPU and 0% idle RAM with absolutely no background processes or active polling threads. |
| | **Instant Local Suggestions** | Sørensen–Dice coefficient token matching evaluates shortcuts locally in $<2\text{ms}$, bypassing the LLM. |
| **Resiliency** | **Cascading Fallback Chain** | Seamlessly cascades from Gemini $\rightarrow$ OpenRouter $\rightarrow$ Custom Cloud down to local servers if an endpoint drops offline. |
| | **OpenRouter Failover** | Sends a prioritized model array payload to automatically route around free-tier model congestion on the server side. |
| **Integration** | **Subprocess RAG (`[TOOL]`)** | Executes local scripts behind the scenes, injecting standard terminal output directly into prompt contexts. |
| | **Collision-Resilient Search** | Restricts the perfect-subset score bonus to queries with $\ge 50\%$ match coverage, protecting short command aliases. |
| **Portability** | **Zero Dependencies** | Written natively using the Python standard library—no `pip` installs or third-party packages required. |
| | **Auditable Codebase** | Designed with full transparency in under 390 lines of clean, standard-library Python code. |

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

<div align="center">

```
                            ██╗      ██████╗  ██████╗  █████╗ ██╗             █████╗ ██╗   
                            ██║     ██╔═══██╗██╔════╝ ██╔══██╗██║            ██╔══██╗██║   
                            ██║     ██║   ██║██║      ███████║██║  ███████╗  ███████║██║   
                            ██║     ██║   ██║██║      ██╔══██║██║  ╚══════╝  ██╔══██║██║   
                            ███████╗╚██████╔╝╚██████╗ ██║  ██║███████╗       ██║  ██║██║   
                         ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝       ╚═╝  ╚═╝╚═╝
                             
                           █████╗  ██████╗ ███████╗███╗   ██╗████████╗
                          ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
                          ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
                          ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
                          ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
                          ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
```

---

</div>

*For detailed system architecture diagrams, custom tool development guidelines, and advanced prompt engineering, refer to the full **[documentation.md](documentation.md)**.*

