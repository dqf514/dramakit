#!/usr/bin/env bash
# What did the engine reserve, and does it still answer?
echo "=== 引擎日志里的 KV / 上下文 ==="
docker exec strata-engine sh -c 'tail -60 /root/.local/state/strata/launch/lan.engine.log' 2>&1 | grep -iE 'kv|context|ctx|memory|cache|ready|model load' | tail -15

echo
echo "=== 问答测速 ==="
time curl -s --max-time 120 http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next-iq3_xxs","max_tokens":150,"messages":[{"role":"user","content":"用一句话说说什么是短剧"}]}' \
  | head -c 400
echo

echo
echo "=== 长一点的输入（顺便看上下文真的能用） ==="
python3 - <<'PY'
import json, urllib.request, time
long_text = ("这是一段用来占位置的背景文字。短剧是单集时长较短、节奏快、冲突集中的剧集。" * 400)
body = json.dumps({
    "model": "qwen3.8-flash-next-iq3_xxs",
    "max_tokens": 120,
    "messages": [
        {"role": "user", "content": long_text + "\n\n上面这段讲的是什么？一句话。"}],
}).encode()
req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    print("  用时 %.1f 秒" % (time.time() - t0))
    print("  输入 %d token，输出 %d token" % (
        d["usage"]["prompt_tokens"], d["usage"]["completion_tokens"]))
    print("  回答:", d["choices"][0]["message"]["content"][:200])
except Exception as e:
    print("  失败:", type(e).__name__, str(e)[:200])
PY

echo
echo "=== 内存与 swap ==="
free -g | head -3
