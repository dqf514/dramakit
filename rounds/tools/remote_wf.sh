#!/bin/bash
mkdir -p /tmp/h3wf
cd /data/comfyui/user/default/workflows/H3
for f in *.json; do
  cp "$f" "/tmp/h3wf/$f" 2>/dev/null
done
ls -la /tmp/h3wf/
echo
echo "=== 每个工作流的结构 ==="
for f in /tmp/h3wf/*.json; do
  echo "--- $(basename "$f") ($(stat -c%s "$f") 字节) ---"
  python3 - "$f" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
nodes = d.get('nodes') or []
print(f"  节点数 {len(nodes)}")
for n in nodes:
    t = str(n.get('type', ''))
    if t in ('KSampler','KSamplerAdvanced','SamplerCustomAdvanced','LatentUpscale',
             'ModelSamplingFlux','EmptyHunyuanLatentVideo','EmptyLatentImage',
             'BasicScheduler','RandomNoise','SamplerCustom','GuiderBasic',
             'CFGGuider','BasicGuider','VAEDecode','SaveVideo','CreateVideo',
             'CLIPLoader','UNETLoader','VAELoader','LoadImage','LoraLoader',
             'LoraLoaderModelOnly','LatentFromBatch','RepeatLatentBatch'):
        w = (n.get('widgets_values') or [])
        extra = ''
        if t == 'KSampler':
            extra = f"steps={w[0] if len(w)>0 else '?'} cfg={w[1] if len(w)>1 else '?'} sampler={w[2] if len(w)>2 else '?'} sched={w[3] if len(w)>3 else '?'} denoise={w[4] if len(w)>4 else '?'}"
        elif t == 'SamplerCustomAdvanced':
            extra = f"noise={n.get('inputs',{}).get('noise')}"
        elif t == 'LatentUpscale':
            extra = f"upscale_method={w[0] if w else '?'}"
        elif t in ('BasicScheduler',):
            extra = f"steps={w[1] if len(w)>1 else '?'} scheduler={w[2] if len(w)>2 else '?'}"
        elif t == 'UNETLoader':
            extra = f"unet={w[0] if w else '?'}"
        elif t == 'LoraLoaderModelOnly':
            extra = f"lora={w[0] if w else '?'} strength={w[1] if len(w)>1 else '?'}"
        print(f"    {n.get('id')}: {t:<26} {extra}")
EOF
done
