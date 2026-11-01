"""Why does doctor call the LLM a failure when the endpoint answers?

doctor asks for one word with max_tokens=10. MiniMax-M3.1-Flash reasons
before it speaks, so a ten-token budget can be spent entirely on thinking
- and the question is what the response looks like then. If the endpoint
returns an empty choices list, the client's choices[0] raises IndexError
and the shape is blamed for a budget problem.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.providers.llm import OpenAICompatLLM

cfg = Config.load(Config.discover())
cli = OpenAICompatLLM(cfg.llm)

out = [f"模型: {cfg.llm.model}", ""]

for budget in (10, 256, 2048):
    out.append(f"=== max_tokens={budget}（doctor 那句原话）===")
    try:
        r = cli.complete("You are a test.", "Reply with the single word: OK",
                         max_tokens=budget)
        out.append(f"  客户端成功: {r.text!r}")
        out.append(f"  tokens: 提示 {r.prompt_tokens} / 补全 {r.completion_tokens}")
    except Exception as e:  # noqa: BLE001
        out.append(f"  客户端失败 -> {type(e).__name__}: {str(e)[:220]}")
    out.append("")

# and the raw response at the budget doctor uses, so the shape is not a guess
out.append("=== 原始响应（max_tokens=10）===")
try:
    import urllib.request
    req = urllib.request.Request(
        cfg.llm.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": cfg.llm.model,
                         "messages": [{"role": "system", "content": "You are a test."},
                                      {"role": "user", "content": "Reply with the single word: OK"}],
                         "max_tokens": 10, "stream": False}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + (cfg.llm.api_key or "")},
        method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        body = json.loads(r.read())
    out.append("  choices 长度: " + str(len(body.get("choices") or [])))
    out.append("  完整响应: " + json.dumps(body, ensure_ascii=False)[:600])
except Exception as e:  # noqa: BLE001
    out.append(f"  失败 -> {type(e).__name__}: {str(e)[:200]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\budget.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
