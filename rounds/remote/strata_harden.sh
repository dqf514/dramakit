#!/usr/bin/env bash
# The engine should come back by itself: it is a service, and the
# machine it lives on gets restarted more often than anyone remembers.
echo "=== 加上自动重启 ==="
docker update --restart unless-stopped strata-engine 2>&1 | tail -2
docker ps --filter name=strata-engine --format '{{.Names}} | {{.Status}}'

echo
echo "=== 内存与显存的走势（3 分钟） ==="
for i in $(seq 1 7); do
  echo "--- $(date +%H:%M:%S) ---"
  free -g | awk 'NR==2{printf "  内存 已用 %sG 可用 %sG  ", $3, $7}'
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr '\n' ' '
  echo
  sleep 25
done

echo
echo "=== 出视频的那台还活着吗 ==="
curl -s --max-time 10 http://127.0.0.1:8188/system_stats | head -c 200; echo
docker ps --filter name=comfyui-h3-a --format '{{.Names}} | {{.Status}}'
