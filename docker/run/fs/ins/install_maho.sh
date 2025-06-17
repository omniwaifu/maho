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

# Maho code is already copied to /maho in the Dockerfile
echo "Using Maho code already available at /maho"

. "/ins/setup_venv.sh" "$@"

# moved to base image
# # Ensure the virtual environment and pip setup
# pip install --upgrade pip ipython requests
# # Install some packages in specific variants
# pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install Maho python packages using pyproject.toml (modern approach)
echo "Installing Maho dependencies using pyproject.toml..."
cd /maho

# Use the existing virtual environment from base image
export VIRTUAL_ENV=/opt/venv
export PATH="/opt/venv/bin:$PATH"

# Install dependencies directly with uv pip to avoid venv conflicts
uv pip install -e .

# Verify MCP installation
python -c "import mcp; from mcp import ClientSession; print(f'DEBUG: mcp and mcp.ClientSession imported successfully. mcp path: {mcp.__file__}')" || {
    echo "ERROR: mcp package or mcp.ClientSession not importable. Attempting manual install..."
    uv pip install -v mcp==1.9.0
}

# install playwright
bash /ins/install_playwright.sh "$@"

# Preload Maho using new script location
python /maho/scripts/preload.py --dockerized=true
