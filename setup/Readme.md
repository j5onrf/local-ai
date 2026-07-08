# Local Server Configuration (Reasoning Models)

This directory contains resources to configure and deploy a local `llama-server` instance designed to run reasoning-enabled models (such as `Qwen3.6-35B-A3B`) alongside this CLI agent.

To support the agent's dynamic reasoning toggles (`/r` and `/r <tokens>`) without restarting the server or splitting your VRAM, the backend server must be configured with a specific combination of template variables, format parsers, and budget defaults.

---

## 1. Core Server Parameters

The `example-server.sh` launch script is configured with the following critical parameters to enable client-controlled reasoning on-the-fly:

| Parameter | Recommended Setting | Description |
| :--- | :--- | :--- |
| `--reasoning` | `on` | Activates the server's reasoning evaluation pipeline. |
| `--reasoning-format` | `deepseek` | Separates `<think>` tags into `reasoning_content` to keep the standard `content` stream clean. |
| `--reasoning-budget` | `-1` | Set to unrestricted. This allows the client payload to dynamically dictate the budget per request. |
| `--reasoning-budget-message` | `" ... reasoning budget exceeded, let's answer now.\n"` | Injects a graceful transition message if a client-side budget limit is reached mid-thought, preventing formatting leaks. |
| `--chat-template-kwargs` | `'{"enable_thinking":false}'` | **Crucial:** Sets the global template default to OFF. All standard scripts, subroutines (like `/a`), and standard agent prompts bypass reasoning and generate instantly. |
| `--jinja` | *Enabled* | Required to parse the embedded Jinja chat templates inside Qwen GGUFs. |

---

## 2. Setup & Execution

Follow these steps to deploy your local backend:

### Step 1: Prepare the Model
Ensure you have downloaded a compatible Qwen reasoning model in GGUF format (e.g., `Qwen3.6-35B-A3B.gguf`).

### Step 2: Configure the Launch Script
Open `example-server.sh` and update the configuration variables at the top of the file to match your local paths:

```bash
# Configuration
PORT=8080
MODEL_PATH="/path/to/your/models/Qwen3.6-35B-A3B.gguf"
LOG_DIR="/path/to/your/logs/serv"
LOG_FILE="$LOG_DIR/server.log"
LLAMA_SERVER_BIN="/path/to/your/llama.cpp/build/bin/llama-server"
```

### Step 3: Run the Server
Make the script executable and launch it:
```bash
chmod +x example-server.sh
./example-server.sh
```
*Note: The script wraps execution in a UWSM / `nice` priority window (`nice -n 19 ionice -c 3`) to prevent local server operations from causing system GUI stuttering on consumer hardware during heavy inference loads.*

---

## 3. How the Client Controls Reasoning

By starting the server with reasoning `on` but default template thinking set to `false`, the client script (`ai-agent.py`) takes absolute control over when reasoning is used:

* **Normal Queries:** The agent sends standard API payloads containing `"enable_thinking": false`. The server skips reasoning and responds instantly.
* **Brainstorms/Follow-ups (`/a`, `/f`):** These background subroutines send normal payloads, keeping background generations fast and lightweight.
* **Reasoning Toggle (`/r`):** Toggling `/r` (or specifying a custom budget like `/r 1500`) tells the agent to append `"chat_template_kwargs": {"enable_thinking": true}` and `"thinking_budget_tokens": <limit>` to the request payload. The server dynamically spins up the reasoning pipeline specifically for that single turn.

---

# 1. Interactive TUI Selector (`model-select-local.py`)

A standalone terminal interface to switch active local GGUF models, unload memory, and launch background server containers.

### Features
* **Active Status Detection:** Scans system processes via `pgrep` to show which GGUF is currently loaded on Port 8080.
* **RAM & VRAM Power Clean:** Executes a graceful `SIGTERM` (escalating to `SIGKILL` if hanging) and flushes system page caches (`drop_caches`).
* **Detached Sessions:** Spawns backend servers in independent process groups (`start_new_session=True`), keeping the model running after closing the selector UI.

### Configuration
Edit the top variables in `model-select-local.py` to point to your script paths and models:

```python
MODELS_DIR = "/home/user/models"
SERV_DIR = "/home/user/models/serv"

LOCAL_MODELS = [
    {"name": "Qwen 3.5 2B (Ultra-Light)", "file": "Qwen3.5-2B.gguf", "script": "q2b.sh"},
    {"name": "Qwen 3.6 35B (4-bit Uncensored)", "file": "Qwen3.6-35B-A3B.gguf", "script": "q35b.sh"},
    {"name": "Qwen 3.6 35B (Reasoning-On)", "file": "Qwen3.6-35B-A3B.gguf", "script": "q35b-on.sh"},
]
```

---

## 2. Quickstart

1. **Make scripts executable:**
   ```bash
   chmod +x example-server.sh model-select-local.py
   ```

2. **Launch the TUI Model Selector:**
   ```bash
   ./model-select-local.py
   ```
   * Use **▲/▼ Arrows** to select a model and press **Enter** to switch.
   * Select **Unload All Local Models** to completely free up system RAM/VRAM.

