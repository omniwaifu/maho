#!/bin/bash
set -e

# cachebuster script, this helps speed up docker builds

# Fix missing Chromium dependencies that might have been cached
echo "Installing missing Chromium dependencies..."
apt-get update && apt-get install -y --no-install-recommends \
    libgbm1 libxss1 libasound2t64 libgtk-3-0 libdrm2 libxrandr2

# No need to remove repo since Maho code is built into image

# run the original install script again
bash /ins/install_maho.sh "$@"

# remove python packages cache
. "/ins/setup_venv.sh" "$@"
pip cache purge
uv cache prune