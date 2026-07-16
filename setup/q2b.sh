#!/bin/env bash

# Configuration
PORT=8080
MODEL_PATH="/home/user/models/Qwen3.5-2B-Claude-4.6-OS-Auto-Variable-HERETIC-UNCENSORED-THINKING.Q4_K_M.gguf"
LOG_DIR="/home/user/models/serv"
LOG_FILE="$LOG_DIR/server.log"

LLAMA_SERVER_BIN="/home/user/llama.cpp/build/bin/llama-server"
mkdir -p "$LOG_DIR"

if command -v lsof >/dev/null 2>&1; then
    TARGET_PID=$(lsof -t -i :$PORT)
    if [ -n "$TARGET_PID" ]; then
        kill -15 "$TARGET_PID" 2>/dev/null || kill -9 "$TARGET_PID" 2>/dev/null
        sleep 0.5
    fi
fi

# Fixed: Removed the redundant 'uwsm app --' and used the proper absolute path variable
exec uwsm app -- llama-server \
  -m "$MODEL_PATH" \
  -c 8192 \
  -np 1 \
  -t 6 \
  -b 512 \
  -ub 128 \
  --flash-attn on \
  --reasoning on \
  --reasoning-format deepseek \
  --reasoning-budget -1 \
  --reasoning-budget-message " ... reasoning budget exceeded, let's answer now.\n" \
  --chat-template-kwargs '{"enable_thinking":false}' \
  --context-shift \
  --jinja \
  --temp 0.15 \
  --min-p 0.05 \
  --repeat-penalty 1.15 \
  --repeat-last-n 256 \
  --presence-penalty 0.15 \
  --no-ui \
  --port "$PORT" >> "$LOG_FILE" 2>&1
