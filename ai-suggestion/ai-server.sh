#!/usr/bin/env bash

# Start the llama server in the background
llama-server \
  -m /home/j5/ollama_backup/Qwen3.5-2B-UD-Q4_K_XL.gguf \
  -c 8192 \
  -t 6 \
  -b 512 \
  --cache-type-k q4_0 \
  --cache-type-v q8_0 \
  --flash-attn on \
  --reasoning off \
  --reasoning-budget 0 \
  --context-shift \
  --jinja \
  --temp 0.0 \
  --top-p 0.8 \
  --top-k 20 \
  --min-p 0.0 \
  --presence-penalty 1.5 \
  --no-webui \
  --port 8080 &

# Wait for the port to open, then launch the browser
sleep 2
xdg-open "http://localhost:8080"
