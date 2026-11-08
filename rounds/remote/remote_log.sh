#!/bin/bash
echo "=== ComfyUI 最近的日志（看时间花在哪儿）==="
docker logs --tail 120 comfyui-h3-a 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | tail -80
echo
echo "=== GPU 状态 ==="
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader
