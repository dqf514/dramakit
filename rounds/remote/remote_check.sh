#!/bin/bash
for c in comfyui-h3-a comfyui-h3-b; do
  n=$(docker logs "$c" 2>&1 | grep -c "got prompt")
  echo "$c  收到任务数: $n"
done
echo "--- 队列 ---"
for p in 8188 8189; do
  echo -n "$p: "
  curl -s --max-time 5 "http://127.0.0.1:$p/queue" | head -c 160
  echo
done
echo "--- 容器 ---"
docker ps --format '{{.Names}} {{.Status}}'
