# Local Server Configuration (Reasoning Models) (CPU Only / Must Config for GPU)

This directory contains scripts to deploy and manage local `llama-server` instances configured for Qwen reasoning models, enabling reasoning toggles (`/r`) without splitting VRAM or restarting processes.

*Note: The included `example-server.sh` defaults to **CPU execution** and runs in a headless state.*

---

## 1. Server Configuration (`example-server.sh`)

To support client-side reasoning overrides while keeping background tools fast, `llama-server` must be launched with specific flag combinations:

* **`--reasoning on` & `--reasoning-budget -1`**: Enables reasoning pipeline while delegating token limits to client requests.
* **`--chat-template-kwargs '{"enable_thinking":false}'`**: **(Critical)** Sets default thinking to **OFF**. Standard queries, skills, and background tools (`/a`, `/f`) execute instantly.
* **`--reasoning-format deepseek`**: Separates `<think>` tags from `content` to prevent raw output leaks.
* **`--reasoning-budget-message`**: Injects a clean transition prompt if a token ceiling is reached mid-thought.
* **`--no-ui`**: Disables the embedded web assets to optimize startup time and reduce memory overhead.

### GPU Acceleration Setup
To enable hardware acceleration (CUDA/ROCm/Metal), edit your launcher script and add the **`-ngl`** (number of GPU layers) parameter to the `llama-server` command:
```bash
  -ngl 99 \  # Offloads all layers to the GPU
```

### Accessing the llama.cpp Web UI
If you prefer to use the built-in browser-based playground instead of a purely headless backend, edit `example-server.sh` and **remove** the following line:
```bash
  --no-ui \
```
Once removed, restarting the server allows you to access the interactive web interface directly at `http://localhost:8080`.

---

## 2. Interactive TUI Selector (`model-select-local.py`)

A standalone terminal interface to switch active local GGUF models, unload memory, and launch background server containers.

### Features
* **Active Status Detection:** Scans system processes via `pgrep` to show which GGUF is currently loaded on Port 8080.
* **RAM & VRAM Power Clean:** Executes a graceful `SIGTERM` (escalating to `SIGKILL` if hanging) and flushes system page caches (`drop_caches`).
* **Detached Sessions:** Spawns backend servers in independent process groups (`start_new_session=True`), keeping the model running after closing the selector TUI.

### Configuration
Edit the top variables in `model-select-local.py` to point to your script paths and models:

```python
MODELS_DIR = "/home/user/models"
SERV_DIR = "/home/user/models/serv"

LOCAL_MODELS = [
    {"name": "Qwen 3.5 2B (Ultra-light)", "file": "Qwen3.5-2B.gguf", "script": "q2b.sh"},
    {"name": "Qwen 3.6 35B (4-bit Uncensored)", "file": "Qwen3.6-35B-A3B.gguf", "script": "q35b.sh"},
]
```

---

## 3. Quickstart

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
