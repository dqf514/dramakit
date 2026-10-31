#!/bin/bash
echo "=== 驱动支持的算子（看 nvfp4 是 native 还是 emulated）==="
nvidia-smi -q 2>/dev/null | grep -i -A2 "product name" | head -4
docker logs comfyui-h3-a 2>&1 | grep -m1 -i -E "Native ops|emulated" | sed 's/\x1b\[[0-9;]*m//g'

echo
echo "=== 3090 机器上 text_encoders 有哪些 ==="
ls -la /data/comfyui/models/text_encoders/ 2>/dev/null

echo
echo "=== diffusion_models 有哪些 ==="
ls -la /data/comfyui/models/diffusion_models/ 2>/dev/null

echo
echo "=== 最近一个任务实际加载的模型 ==="
curl -s --max-time 15 "http://127.0.0.1:8188/history?max_items=1" > /tmp/h.json
python3 - <<'EOF'
import json
d = json.load(open('/tmp/h.json'))
for pid, h in list(d.items())[:1]:
    g = (h.get('prompt') or [0,0,{}])[2]
    for nid, n in g.items():
        ct = n.get('class_type','')
        if 'CLIPLoader' in ct or 'UNETLoader' in ct or 'VAELoader' in ct or 'Lora' in ct:
            print(' ', nid, ct, '->', {k:v for k,v in n.get('inputs',{}).items() if k.endswith('name') or 'name' in k})
EOF
