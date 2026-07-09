#!/usr/bin/env bash

# Configuration
PORT=8080
MODEL_PATH="/home/user/models/Qwen3.6-35B-A3B.gguf"
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

# Launch wrapped in UWSM context with idle I/O and low CPU priority
exec ionice -c 3 nice -n 19 "$LLAMA_SERVER_BIN" \
  -m "$MODEL_PATH" \
  -c 8192 \
  -np 1 \
  -t 6 \
  -b 512 \
  -ub 128 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --flash-attn on \
  --reasoning on \
  --reasoning-format deepseek \
  --reasoning-budget -1 \
  --reasoning-budget-message " ... reasoning budget exceeded, let's answer now.\n" \
  --context-shift \
  --jinja \
  --temp 0.45 \
  --dynatemp-range 0.45 \
  --min-p 0.05 \
  --no-ui \
  --port "$PORT" >> "$LOG_FILE" 2>&1
