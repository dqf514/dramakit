"""Does the configured LLM actually answer?

The catalog failed with a refused connection, and the reason turned out to
be a test script: Config() with no arguments takes the Pydantic field
default - Ollama on localhost:11434 - rather than the MiniMax endpoint in
default.yaml that the console loads through Config.load(). So this loads
the config the way the console does and asks the model one question.
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []

from dramakit.config import Config

cfg = Config.load(Path(r"E:\dramakit\config\default.yaml"))
llm = cfg.llm
out.append("=== 生效配置（Config.load）===")
out.append(f"  provider : {llm.provider}")
out.append(f"  base_url : {llm.base_url}")
out.append(f"  model    : {llm.model}")
out.append(f"  api_key  : {'已设 ' + str(len(llm.api_key or '')) + ' 字符' if llm.api_key else '未设'}")
out.append(f"  超时     : {llm.timeout}s   重试: {llm.max_retries}   并发: {llm.concurrency}")

out.append("")
out.append("=== 项目自己的 LLM 客户端 ===")
try:
    from dramakit.providers.llm import LLMProvider
    cli = LLMProvider(llm)
    ans = cli.complete("你是一个测试助手。只回答两个字：正常", max_tokens=16)
    out.append(f"  回答: {str(ans)[:150]!r}")
except Exception as e:  # noqa: BLE001
    out.append(f"  失败 -> {type(e).__name__}: {str(e)[:300]}")

out.append("")
out.append("=== 原始 HTTP 调用 ===")
try:
    req = urllib.request.Request(
        llm.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": llm.model,
                         "messages": [{"role": "user", "content": "回答两个字：正常"}],
                         "max_tokens": 16}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + (llm.api_key or "")},
        method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        body = json.loads(r.read())
    out.append(f"  HTTP {r.status}")
    out.append(f"  回答: {body.get('choices', [{}])[0].get('message', {}).get('content', '')!r}")
    out.append(f"  用量: {body.get('usage')}")
except urllib.error.HTTPError as e:
    out.append(f"  HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}")
except Exception as e:  # noqa: BLE001
    out.append(f"  失败 -> {type(e).__name__}: {str(e)[:250]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\llmreal.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
