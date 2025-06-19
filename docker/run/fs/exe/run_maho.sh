#!/bin/bash

. "/ins/setup_venv.sh" "$@"
. "/ins/copy_maho.sh" "$@"

python /maho/scripts/prepare.py --dockerized=true
python /maho/scripts/preload.py --dockerized=true

echo "Starting Maho..."
exec python /maho/scripts/start_ui.py \
    --dockerized=true \
    --port=80 \
    --host="0.0.0.0" \
    --code_exec_docker_enabled=false \
    --code_exec_ssh_enabled=false \
    # --code_exec_ssh_addr="localhost" \
    # --code_exec_ssh_port=22 \
    # --code_exec_ssh_user="root" \
    # --code_exec_ssh_pass="toor"
