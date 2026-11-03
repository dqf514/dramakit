#!/usr/bin/env bash
# Is it actually answering, and what did it cost the machine's memory?
echo "=== 健康检查 ==="
curl -s --max-time 10 http://127.0.0.1:8080/health; echo

echo
echo "=== 模型列表 ==="
curl -s --max-time 10 http://127.0.0.1:8080/v1/models; echo

echo
echo "=== 真问一句（计时） ==="
time curl -s --max-time 180 http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next-iq3_xxs","max_tokens":200,"messages":[{"role":"user","content":"用一句话说你是谁"}]}' \
  | head -c 900
echo

echo
echo "=== 显存 ==="
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
echo
echo "=== 内存 ==="
free -g | head -3
