#!/bin/bash
echo "=== comfyui-h3-b 最近的错误 ==="
docker logs comfyui-h3-b 2>&1 | tail -25
echo
echo "=== 显存 ==="
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
