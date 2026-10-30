#!/bin/bash
docker exec comfyui-h3-a bash -lc "sed -n '1,120p' /opt/ComfyUI/comfy_extras/nodes_minimax_h3.py" > /tmp/h3node.txt 2>&1
echo "=== 前 120 行 ==="
cat /tmp/h3node.txt
echo
echo "=== ref_image / encode 相关 ==="
docker exec comfyui-h3-a bash -lc "grep -n 'ref_image\|ref_images\|Picture\|encode\|clip.encode\|encode_image' /opt/ComfyUI/comfy_extras/nodes_minimax_h3.py | head -40"
