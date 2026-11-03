#!/usr/bin/env bash
# Is the card actually computing, or is it stuck waiting for something?
#
# Two videos were due around 02:04 and had not appeared by 02:30, and the
# card stopped answering /history. The three questions that separate
# "computing" from "stuck" are: is the GPU busy, what is the queue
# holding, and what did the card's own log say last.
echo "=== GPU ==="
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader
echo
echo "=== GPU 上的进程 ==="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
echo
echo "=== 容器 ==="
docker ps --filter name=comfyui-h3 --format '{{.Names}} | {{.Status}}'
echo
echo "=== 队列（curl，超时短） ==="
for p in 8188 8189; do
  echo "--- :$p ---"
  timeout 12 curl -s --max-time 10 http://127.0.0.1:$p/queue | head -c 400
  echo
done
echo
echo "=== 两个容器日志最后 12 行 ==="
for c in comfyui-h3-a comfyui-h3-b; do
  echo "--- $c ---"
  timeout 15 docker logs --tail 12 "$c" 2>&1 | sed 's/^/  /'
done
echo
echo "=== 宿主机的负载 ==="
uptime
free -g | head -3
