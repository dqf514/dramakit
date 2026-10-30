#!/bin/bash
echo "=== 容器里找 H3 节点 ==="
docker exec comfyui-h3-a bash -lc "grep -rl 'MiniMaxH3ReferenceToVideo' /usr/local/lib/python3.12/dist-packages/ 2>/dev/null | head -5"
echo
echo "=== comfy_kitchen 里的 H3 ==="
docker exec comfyui-h3-a bash -lc "ls /usr/local/lib/python3.12/dist-packages/ | grep -i -E 'h3|minimax|kitchen' | head -10"
