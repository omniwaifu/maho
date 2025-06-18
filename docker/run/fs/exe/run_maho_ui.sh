#!/bin/bash
cd /maho
export PATH="/root/.local/bin:$PATH"

# Handle signals properly
trap 'kill -TERM $PID' TERM INT
uv run scripts/start_ui.py --dockerized=true --port=80 --host=0.0.0.0 &
PID=$!
wait $PID
trap - TERM INT
wait $PID
EXIT_STATUS=$?
