"""How the strata engine answers, and how many tokens it needs.

It is a reasoning model: the thinking comes back in
`reasoning_content` and the answer in `content`.  Given a small token
budget the thinking uses it all and the answer is never written - which
the pipeline reads as a failure, and retries, and eventually calls it a
timeout.
"""
import json
import time
import urllib.request

URL = "http://192.168.31.8:8080/v1/chat/completions"
MODEL = "qwen3.8-flash-next-iq3_xxs"


def ask(mt, extra=None, prompt="只输出JSON：{\"a\":1}"):
    body = {"model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": mt, "stream": False}
    if extra:
        body.update(extra)
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    m = d["choices"][0]["message"]
    content = m.get("content")
    reason = m.get("reasoning_content") or ""
    print("  max_tokens=%-7s %5.1fs  content=%r  finish=%-8s 用了 %d token"
          % (mt, time.time() - t0, (content or "")[:44],
             d["choices"][0].get("finish_reason"),
             d.get("usage", {}).get("completion_tokens", 0)))
    return content, reason, d


print("不同 token 预算：")
for mt in (32, 300, 2000):
    ask(mt)

print()
print("带 response_format（JSON 模式）：")
ask(2000, {"response_format": {"type": "json_object"}})

print()
print("一段真的活（模拟流水线要的 JSON）：")
c, r, d = ask(3000, {"response_format": {"type": "json_object"}},
               prompt="写一个短剧的一集剧本，只要 JSON，"
                      "格式 {\"scenes\":[{\"summary\":\"\",\"lines\":[]}]}")
print("  思考的前 120 字:", (r or "")[:120])
print("  正文:", (c or "")[:200])
