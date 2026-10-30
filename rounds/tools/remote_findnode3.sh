#!/bin/bash
echo "=== 节点实现在哪 ==="
docker exec comfyui-h3-a bash -lc "grep -rl 'class MiniMaxH3ReferenceToVideo' / --include='*.py' 2>/dev/null | head -5"
echo
echo "=== 官方文档 ==="
docker exec comfyui-h3-a bash -lc "cat /usr/local/lib/python3.12/dist-packages/comfyui_embedded_docs/docs/MiniMaxH3ReferenceToVideo/en.md 2>/dev/null | head -60"
