#!/bin/bash
cd /maho
export PATH="/root/.local/bin:$PATH"
exec uv run scripts/start_tunnel.py --dockerized=true --port=80 --tunnel_api_port=55520 --host=0.0.0.0
