#!/usr/bin/env bash
# Raise the context and see whether the machine can still afford it.
#
# The context is set when the engine starts. Going from 128K to 256K
# doubles the conversation memory: eight gigabytes more, on a machine
# that is already holding a film render's worth of weights.
#
# So: change it, start it, and watch what the memory does.
set -u

echo "=== 改之前的内存 ==="
free -g | head -2
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader

echo
echo "=== 停掉旧的引擎容器 ==="
docker rm -f strata-engine 2>&1 | tail -1

echo
echo "=== 用 256k 重启（上下文保持 q4_0） ==="
docker run -d --name strata-engine \
  --network host --ipc host --pid host \
  --gpus all \
  -v /root:/root \
  -v /data/strata-data:/data/strata-data \
  -e HOME=/root \
  python:3.12-slim \
  sh -c 'export PATH=/root/.local/bin:$PATH; \
        strata launch --preset lan --gpu 1 --context 256k --yes --no-tui; \
        echo "=== 启动器已返回，容器保持存活 ==="; \
        tail -f /dev/null' 2>&1 | tail -2

echo
echo "=== 加载过程（看内存和显存） ==="
for i in $(seq 1 14); do
  echo "--- $(date +%H:%M:%S) ---"
  free -g | awk 'NR==2{printf "  内存 已用 %sG 可用 %sG  ", $3, $7}'
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' '
  echo
  docker logs strata-engine 2>&1 | tail -2
  if docker logs strata-engine 2>&1 | grep -q "Ready:"; then
    echo ">>> 就绪"
    break
  fi
  sleep 20
done

echo
echo "=== 健康检查（max_context 应该是 262144） ==="
curl -s --max-time 10 http://127.0.0.1:8080/health; echo
echo
echo "=== 现在的内存 ==="
free -g | head -3
