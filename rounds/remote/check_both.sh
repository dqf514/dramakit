#!/usr/bin/env bash
# Check both ComfyUI workers: are they up, on which card, and do they have
# the acceleration node and the weights the workflow needs.
set -u
echo "=== 容器状态 ==="
docker ps --filter name=comfyui-h3 --format '{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}'
echo
echo "=== 启动参数 / 设备 ==="
for c in comfyui-h3-a comfyui-h3-b; do
  echo "-- $c"
  docker inspect "$c" --format '   image : {{.Config.Image}}'
  docker inspect "$c" --format '   cmd   : {{join .Config.Cmd " "}}'
  docker inspect "$c" --format '   cuda  : {{range .Config.Env}}{{println .}}{{end}}' \
    | grep -E '^CUDA_VISIBLE' | sed 's/^/   /'
  docker inspect "$c" --format '   devices: {{.HostConfig.DeviceRequests}}'
done
echo
echo "=== GPU ==="
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader
echo
echo "=== 两个端点是否响应 ==="
for p in 8188 8189; do
  code=$(curl -s -o /tmp/s$p.json -w '%{http_code}' --max-time 25 http://127.0.0.1:$p/system_stats || echo 000)
  echo "  :$p -> HTTP $code"
  if [ "$code" = "200" ]; then
    python3 -c "
import json,sys
d=json.load(open('/tmp/s$p.json'))
s=d.get('system',{})
dev=(d.get('devices') or [{}])[0]
print('     ComfyUI', s.get('comfyui_version'), '|', dev.get('name'), '| VRAM %.1f/%.1f GB' % (dev.get('vram_free',0)/2**30, dev.get('vram_total',0)/2**30))
" 2>/dev/null || true
  fi
done
echo
echo "=== 关键节点是否安装 ==="
for p in 8188 8189; do
  code=$(curl -s -o /tmp/o$p.json -w '%{http_code}' --max-time 40 http://127.0.0.1:$p/object_info || echo 000)
  if [ "$code" = "200" ]; then
    python3 -c "
import json
d=json.load(open('/tmp/o$p.json'))
need=['PathchSageAttentionKJ','MiniMaxH3ReferenceToVideo','ComfyMathExpression','ComfySwitchNode','KSamplerSelect','BasicScheduler']
miss=[n for n in need if n not in d]
print('  :$p 节点总数', len(d), '| 缺失:', miss or '无')
s=d.get('PathchSageAttentionKJ',{}).get('input',{}).get('required',{}).get('sage_attention')
if isinstance(s,list) and s and isinstance(s[0],list):
    print('     sage 模式数:', len(s[0]), '首项:', s[0][0])
"
  else
    echo "  :$p HTTP $code (还在启动?)"
  fi
done
echo
echo "=== 模型（两实例共用 /data/comfyui/models）==="
ls -1 /data/comfyui/models/diffusion_models/ 2>/dev/null | sed 's/^/  diffusion\//'
ls -1 /data/comfyui/models/text_encoders/ 2>/dev/null | sed 's/^/  text_enc\//'
ls -1 /data/comfyui/models/loras/ 2>/dev/null | sed 's/^/  lora\//'
