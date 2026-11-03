#!/usr/bin/env bash
# Start the strata engine on the second card, and only the second card.
#
# The engine lives under /root, which this account cannot read, and sudo
# wants a password. A container runs as root, so the engine is started
# from one: the machine's own /root and model data are mounted into it,
# the network is the host's (so the port is the host's port), and the
# cards are the host's cards - and the engine is told to use the second
# one, because the first one is making the films.
#
# The container is left running: the engine is its child, and when the
# container goes, the engine goes with it.
set -u

echo "=== 启动前的显存和内存 ==="
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
free -g | head -2

echo
echo "=== 旧容器 ==="
docker rm -f strata-engine 2>/dev/null && echo "  旧的已删" || echo "  没有旧的"

echo
echo "=== 启动（卡 1） ==="
docker run -d --name strata-engine \
  --network host --ipc host --pid host \
  --gpus all \
  -v /root:/root \
  -v /data/strata-data:/data/strata-data \
  -e HOME=/root \
  python:3.12-slim \
  sh -c 'export PATH=/root/.local/bin:$PATH; \
        strata launch --preset lan --gpu 1 --yes --no-tui; \
        echo "=== 启动器已返回，容器保持存活 ==="; \
        tail -f /dev/null' 2>&1 | tail -3

sleep 5
echo
echo "=== 容器状态 ==="
docker ps --filter name=strata-engine --format '{{.Names}} | {{.Status}}'
echo
echo "=== 启动日志 ==="
docker logs strata-engine 2>&1 | tail -40
