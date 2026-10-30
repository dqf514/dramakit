#!/bin/bash
docker cp comfyui-h3-a:/opt/ComfyUI/comfy_extras/nodes_minimax_h3.py /tmp/nodes_minimax_h3.py 2>&1
echo "=== 关键行 ==="
grep -n "ref_image\|Picture\|ref_idx\|ref_images\|def .*reference\|encode_ref\|images\[" /tmp/nodes_minimax_h3.py | head -50
echo
echo "=== 行数 ==="
wc -l /tmp/nodes_minimax_h3.py
