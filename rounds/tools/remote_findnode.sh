#!/bin/bash
echo "=== 找 H3 节点 ==="
grep -rl "MiniMaxH3ReferenceToVideo" /data/comfyui/custom_nodes/ 2>/dev/null | head -5
echo
for f in $(grep -rl "MiniMaxH3ReferenceToVideo" /data/comfyui/custom_nodes/ 2>/dev/null | head -3); do
  echo "=== $f ==="
  ls -la "$f"
done
