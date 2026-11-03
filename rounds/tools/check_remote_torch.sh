#!/usr/bin/env bash
# What is the remote's ComfyUI running on, and are its fast kernels on?
echo "=== 启动日志里的关键行 ==="
for c in comfyui-h3-a comfyui-h3-b; do
  echo "--- $c ---"
  docker logs "$c" 2>&1 | grep -iE 'cu130|optimized CUDA|backend (cuda|eager)|pytorch version' | head -6
done
echo
echo "=== 容器里的 torch ==="
docker exec comfyui-h3-a python -c 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_capability())' 2>&1 | tail -2
