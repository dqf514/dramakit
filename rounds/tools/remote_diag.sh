#!/bin/bash
echo "=== nvidia-smi -L（物理显卡）==="
nvidia-smi -L
echo
echo "=== lspci 里的 NVIDIA ==="
lspci | grep -i nvidia
echo
echo "=== 驱动 ==="
nvidia-smi --query-gpu=index,name,uuid,pci.bus_id --format=csv
echo
echo "=== 容器状态 ==="
docker ps -a --format '{{.Names}} | {{.Status}}' | head -8
echo
echo "=== comfyui-h3-a 的日志尾部 ==="
docker logs comfyui-h3-a 2>&1 | tail -15
echo
echo "=== 8188 的系统状态 ==="
curl -s --max-time 8 http://127.0.0.1:8188/system_stats | head -c 200
echo
echo "=== 宿主机上的端口 ==="
ss -ltnp 2>/dev/null | grep -E '818[89]' | head -4
