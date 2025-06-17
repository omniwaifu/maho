#!/bin/bash
set -e

# Exit immediately if a command exits with a non-zero status.
# set -e

# branch from parameter
if [ -z "$1" ]; then
    echo "Error: Branch parameter is empty. Please provide a valid branch name."
    exit 1
fi
BRANCH="$1"

git clone -b "$BRANCH" "https://github.com/frdel/agent-zero" "/git/agent-zero" || {
    echo "CRITICAL ERROR: Failed to clone repository. Branch: $BRANCH"
    exit 1
}

. "/ins/setup_venv.sh" "$@"

# moved to base image
# # Ensure the virtual environment and pip setup
# pip install --upgrade pip ipython requests
# # Install some packages in specific variants
# pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install A0 python packages using pyproject.toml (modern approach)
echo "Installing Maho dependencies using pyproject.toml..."
cd /git/agent-zero
uv pip install -e . || {
    echo "WARNING: Failed to install from pyproject.toml, falling back to requirements.txt"
    uv pip install -r requirements.txt
}

# Verify MCP installation
python -c "import mcp; from mcp import ClientSession; print(f'DEBUG: mcp and mcp.ClientSession imported successfully. mcp path: {mcp.__file__}')" || {
    echo "ERROR: mcp package or mcp.ClientSession not importable. Attempting manual install..."
    uv pip install -v mcp==1.9.0
}

# install playwright
bash /ins/install_playwright.sh "$@"

# Preload A0 using new script location
python /git/agent-zero/scripts/preload.py --dockerized=true || {
    echo "WARNING: New preload script failed, trying old location..."
    python /git/agent-zero/preload.py --dockerized=true
}
