#!/usr/bin/env bash
# ==============================================================================
# T3 Code WebApp Launcher (Auto-Captures Pairing Token)
# ==============================================================================

PORT=3773
DEFAULT_URL="http://localhost:${PORT}"
LOG_FILE="/tmp/t3code.log"
BROWSER=$(command -v brave-origin || command -v brave || command -v chromium || command -v google-chrome)
PROFILE_DIR="$HOME/.config/py-agent/.cache/t3-webapp-profile"

# 1. Load central .env
if [[ -f "$HOME/.config/py-agent/.env" ]]; then
    set -a
    source "$HOME/.config/py-agent/.env"
    set +a
fi

# Fallback local endpoints
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://127.0.0.1:8080/v1}"
export OPENAI_API_BASE="${OPENAI_BASE_URL:-http://127.0.0.1:8080/v1}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-local-model}"

# 2. Cleanup Function on window close
cleanup() {
    echo -e "\n[T3 Code] WebApp closed. Shutting down background server..."
    if [[ -n "$T3_PID" ]]; then
        kill "$T3_PID" 2>/dev/null || true
    fi
    pkill -f "t3/dist" 2>/dev/null || true
    rm -f "$LOG_FILE"
    echo "[T3 Code] Server stopped cleanly."
    exit 0
}
trap cleanup EXIT INT TERM

# 3. Start T3 Code Server and log to temp file
echo "[T3 Code] Starting server on port ${PORT}..."
BROWSER=none t3 > "$LOG_FILE" 2>&1 &
T3_PID=$!

# 4. Wait for server and extract the Pairing URL automatically
TARGET_URL="$DEFAULT_URL"
echo "[T3 Code] Waiting for server and pairing token..."
for i in {1..30}; do
    if grep -q "pairingUrl:" "$LOG_FILE" 2>/dev/null; then
        TARGET_URL=$(grep "pairingUrl:" "$LOG_FILE" | awk '{print $NF}' | tr -d '\r\n')
        break
    elif curl -s "$DEFAULT_URL" > /dev/null 2>&1; then
        break
    fi
    sleep 0.4
done

# 5. Launch Brave directly to the pre-authenticated pairing URL
if [[ -n "$BROWSER" ]]; then
    mkdir -p "$PROFILE_DIR"
    echo "[T3 Code] WebApp running. Close window to stop server."
    "$BROWSER" --app="$TARGET_URL" --user-data-dir="$PROFILE_DIR" --class=T3Code
else
    echo "Error: No supported browser found."
    exit 1
fi
