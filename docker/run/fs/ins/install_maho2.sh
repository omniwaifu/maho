#!/bin/bash
set -e

# cachebuster script, this helps speed up docker builds

# No need to remove repo since Maho code is built into image

# run the original install script again
bash /ins/install_maho.sh "$@"

# remove python packages cache
. "/ins/setup_venv.sh" "$@"
pip cache purge
uv cache prune