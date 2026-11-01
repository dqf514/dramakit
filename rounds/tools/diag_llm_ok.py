"""Does the configured LLM answer, through the client the pipeline uses?

The console is configured for MiniMax and the endpoint answers HTTP 200,
but a reasoning model spends tokens thinking before it speaks - a tiny
budget came back empty because all of it went to reasoning. This asks
through OpenAICompatLLM, the client the stages actually call, with room to
think, and also tries the structured-output path the catalog relies on.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.providers.llm import OpenAICompatLLM

out = []

cfg = Config.load(Path(r"E:\dramakit\config\default.yaml"))
llm = cfg.llm
out.append(f"模型: {llm.model} @ {llm.base_url}")
out.append("")

cli = OpenAICompatLLM(llm)

out.append("=== 普通问答 ===")
try:
    ans = cli.complete("你是一个测试助手。只回答四个字：一切正常", max_tokens=2048)
    out.append(f"  回答: {str(ans)[:200]!r}")
except Exception as e:  # noqa: BLE001
    out.append(f"  失败 -> {type(e).__name__}: {str(e)[:300]}")

out.append("")
out.append("=== 结构化输出（分章/分析用的那条路）===")
try:
    ans = cli.complete_json(
        "只输出JSON，不要解释。",
        '输出 {"ok": true, "note": "一切正常"}')
    out.append(f"  回答: {str(ans)[:200]!r}")
except Exception as e:  # noqa: BLE001
    out.append(f"  失败 -> {type(e).__name__}: {str(e)[:300]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\llmok.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
