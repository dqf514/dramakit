#!/bin/bash
echo "=== 3090 机器上现在有哪些出图模型 ==="
ls -la /data/comfyui/models/diffusion_models/ 2>/dev/null | grep -i -E "flux|klein" || echo "  （没有 flux/分类模型）"
echo "--- text_encoders ---"
ls -la /data/comfyui/models/text_encoders/ 2>/dev/null | head -8
echo "--- vae ---"
ls -la /data/comfyui/models/vae/ 2>/dev/null | head -8
echo "--- loras ---"
ls -la /data/comfyui/models/loras/ 2>/dev/null | head -8
echo
echo "=== 本机（5080）的出图模型 ==="
ls -la /opt/ComfyUI/models/diffusion_models/ 2>/dev/null | head -3 || true
echo
echo "=== 显存占用 ==="
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader
