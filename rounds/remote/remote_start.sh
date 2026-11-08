#!/bin/bash
echo "=== 显卡 ==="
nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv
echo
echo "=== 容器 ==="
docker ps -a --format '{{.Names}} | {{.Status}}' | head -8
echo
echo "=== 起两个 ComfyUI ==="
cd ~ && docker compose -p dramakit-h3 -f ~/dramakit/docker-compose.h3.yml up -d 2>&1 | tail -8
echo
for p in 8188 8189; do
  echo -n "  端口 $p: "
  ok=no
  for i in $(seq 1 30); do
    sleep 10
    if curl -s --max-time 6 "http://127.0.0.1:$p/system_stats" | head -c 60 | grep -q comfyui; then
      ok=yes
      break
    fi
  done
  echo "$ok"
done
echo
echo "=== 起来之后的显卡 ==="
nvidia-smi --query-gpu=index,memory.used --format=csv,noheader
docker ps --format '{{.Names}} | {{.Status}}' | head -8
