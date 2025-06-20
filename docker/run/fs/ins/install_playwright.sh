#!/bin/bash
set -e

# activate venv
. "/ins/setup_venv.sh" "$@"

# install playwright if not installed (should be from requirements.txt)
uv pip install playwright

# set PW installation path to /maho/tmp/playwright
export PLAYWRIGHT_BROWSERS_PATH=/maho/tmp/playwright

# install chromium with dependencies  
apt-get install -y fonts-unifont libnss3 libnspr4 libatk1.0-0 libatspi2.0-0 libxcomposite1 libxdamage1 libatk-bridge2.0-0 libcups2 \
    libgbm1 libxss1 libasound2t64 libgtk-3-0 libdrm2 libxrandr2
playwright install chromium --only-shell
