#!/usr/bin/env bash
# ==============================================================================
# PyCode Automated Setup & Build Script for Py-Agent
# ==============================================================================

set -eo pipefail

PYAGENT_DIR="${HOME}/.config/py-agent"
PYCODE_DIR="${HOME}/.config/pycode"
REPO_URL="https://github.com/j5onrf/pycode.git"

echo -e "\033[1;36m[pycode-setup]\033[0m Checking prerequisites..."

# 1. Check Node.js
if ! command -v node &>/dev/null; then
    echo -e "\033[1;31m[error]\033[0m Node.js is required. Please install Node.js 20+ (e.g. 'sudo pacman -S nodejs')."
    exit 1
fi

# 2. Check / Enable pnpm
if ! command -v pnpm &>/dev/null; then
    echo -e "\033[1;33m[pycode-setup]\033[0m pnpm not found. Enabling via corepack..."
    corepack enable || npm install -g pnpm
fi

# 3. Clone or Update PyCode repo
if [ ! -d "$PYCODE_DIR" ]; then
    echo -e "\033[1;36m[pycode-setup]\033[0m Cloning PyCode into $PYCODE_DIR..."
    git clone "$REPO_URL" "$PYCODE_DIR"
else
    echo -e "\033[1;36m[pycode-setup]\033[0m Existing PyCode installation found at $PYCODE_DIR."
fi

# 4. Install & Build
echo -e "\033[1;36m[pycode-setup]\033[0m Installing dependencies..."
cd "$PYCODE_DIR"
pnpm install

echo -e "\033[1;36m[pycode-setup]\033[0m Building PyCode frontend and server..."
pnpm build

# 5. Ensure launch script is executable
chmod +x "$PYAGENT_DIR/plugins/pycode/launch.sh" 2>/dev/null || true
chmod +x "$PYAGENT_DIR/plugins/pycode/bridge.py" 2>/dev/null || true

echo -e "\n\033[1;32m✔ PyCode installation complete!\033[0m"
echo -e "You can now launch the GUI from your terminal by running:\n"
echo -e "  \033[1;37mai\033[0m  ──►  \033[1;36m/pyc\033[0m (or \033[1;36m/pyc web\033[0m for browser mode)\n"
