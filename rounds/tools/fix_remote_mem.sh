#!/usr/bin/env bash
# Put the two workers back on their feet, and stop them doing it again.
#
# The card came back with both ComfyUI instances answering nothing while
# the kernel still accepted connections - the shape a host runs out of
# memory. Each instance loads about 45 GB of H3 weights (19.5 GB model +
# 25.3 GB text encoder), and until the second worker was enabled only one
# card ever loaded anything, so this pressure is new.
#
# So: read what the machine says happened, restart both containers, and
# put the smaller weights on them - the model the local card has in the
# w6a8 version is 14.9 GB against 19.5 GB for the int8 one, and the
# text encoder in nvfp4_awq is 14.6 GB against 25.3 GB for the int8 one.
# Whether an Ampere card can run the 4-bit text encoder is the one thing
# that has to be tested rather than assumed.
set -u
echo "=== 内存 ==="
free -g
echo
echo "=== OOM 证据 ==="
dmesg -T 2>/dev/null | grep -iE "out of memory|oom-kill|killed process" | tail -12 \
  || journalctl -k --since "-3 hours" 2>/dev/null | grep -iE "oom|killed process" | tail -12 \
  || echo "  (拿不到 dmesg)"
echo
echo "=== 磁盘 ==="
df -h /data | tail -2
echo
echo "=== 重启两个容器 ==="
docker restart comfyui-h3-a comfyui-h3-b 2>&1 | tail -4
sleep 40
echo
echo "=== 是否恢复 ==="
for p in 8188 8189; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 "http://127.0.0.1:$p/queue")
  echo "  :$p /queue -> $code"
done
echo
echo "=== GPU ==="
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader
echo
echo "=== 现有的 H3 权重 ==="
ls -la /data/comfyui/models/diffusion_models/ 2>/dev/null | grep -iE "ref2va|fl2va"
ls -la /data/comfyui/models/text_encoders/ 2>/dev/null | grep -iE "qwen3vl_32b"
