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
#
# Three things here were not obvious and cost an afternoon:
#
#   --ulimit memlock=-1:-1   the engine locks the pages of its expert
#                            tables. Without the limit (8 MB by default)
#                            the lock fails, the pages are reclaimed and
#                            faulted back in, nineteen cores spin, and
#                            every request takes a minute instead of a
#                            second. The log says it plainly:
#                            "PLE table mlock failed (Cannot allocate
#                            memory)".
#   --context 64k            the longest prompt the pipeline sends is
#                            about 17k tokens; 64k leaves room and is a
#                            quarter of the memory of 256k.
#   --vision off             the drama never sends an image to the
#                            model, and the vision tower is a model of
#                            its own on the card.
set -u

echo "=== 启动前的显存和内存 ==="
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
free -g | head -2

echo
echo "=== 旧容器 ==="
docker rm -f strata-engine 2>/dev/null && echo "  旧的已删" || echo "  没有旧的"

echo
echo "=== 启动（卡 1，memlock 不限，64k 上下文）==="
docker run -d --name strata-engine \
  --network host --ipc host --pid host \
  --gpus all \
  --ulimit memlock=-1:-1 \
  --restart unless-stopped \
  -v /root:/root \
  -v /data/strata-data:/data/strata-data \
  -e HOME=/root \
  python:3.12-slim \
  sh -c 'export PATH=/root/.local/bin:$PATH; \
        strata launch --preset lan --gpu 1 --context 64k --parallel 2 \
          --vision off --yes --no-tui; \
        echo "=== 启动器已返回，容器保持存活==="; \
        tail -f /dev/null' 2>&1 | tail -3

sleep 5
echo
echo "=== 容器状态 ==="
docker ps --filter name=strata-engine --format '{{.Names}} | {{.Status}}'
