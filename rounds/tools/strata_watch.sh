#!/usr/bin/env bash
# Watch the engine load, and see which physical card it lands on.
echo "=== 现在的显存 ==="
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
for i in $(seq 1 12); do
  echo "--- $(date +%H:%M:%S) ---"
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' '
  echo
  docker logs strata-engine 2>&1 | tail -4
  if docker logs strata-engine 2>&1 | grep -q "Ready:"; then
    echo ">>> 引擎就绪"
    break
  fi
  sleep 20
done
