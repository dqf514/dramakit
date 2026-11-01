"""Does the configured LLM answer, with room for a reasoning model to think?

MiniMax-M3.1-Flash spends tokens reasoning before it answers, so a tiny
budget comes back empty - the model used 15 of 16 tokens thinking and had
none left to say anything. This asks through the project's own client with
a realistic budget, and reports what the client class is.
"""
import inspect
import sys

sys.path.insert(0, r"E:\dramakit")

import dramakit.providers.llm as L
from dramakit.config import Config
from pathlib import Path

out = []

out.append("=== llm.py 里的类 ===")
for name, obj in inspect.getmembers(L, inspect.isclass):
    if obj.__module__.startswith("dramakit"):
        out.append(f"  {name}")

cfg = Config.load(Path(r"E:\dramakit\config\default.yaml"))
llm = cfg.llm

# find the client class the pipeline itself uses
Client = None
for name in ("LLM", "OpenAICompat", "OpenAICompatible", "LLMClient", "Provider"):
    if hasattr(L, name):
        Client = getattr(L, name)
        break
if Client is None:
    cands = [o for _, o in inspect.getmembers(L, inspect.isclass)
             if o.__module__.startswith("dramakit")]
    Client = cands[0] if cands else None

out.append("")
out.append(f"=== 用 {Client.__name__ if Client else '（没找到）'} 调用 ===")
if Client is not None:
    try:
        cli = Client(llm)
        meth = None
        for m in ("complete", "chat", "ask", "__call__"):
            if hasattr(cli, m):
                meth = m
                break
        out.append(f"  方法: {meth}")
        fn = getattr(cli, meth)
        ans = fn("你是一个测试助手。只回答四个字：一切正常", max_tokens=1024)
        out.append(f"  回答: {str(ans)[:200]!r}")
    except Exception as e:  # noqa: BLE001
        out.append(f"  失败 -> {type(e).__name__}: {str(e)[:300]}")

out.append("")
out.append("=== 结构化输出（分章那种用法）===")
try:
    meth = None
    for m in ("complete_json", "json", "chat_json"):
        if hasattr(cli, m):
            meth = m
            break
    if meth:
        ans = getattr(cli, meth)(
            "只输出JSON。", '输出 {"ok": true, "note": "正常"}')
        out.append(f"  {meth}(): {str(ans)[:200]!r}")
    else:
        out.append("  客户端没有 complete_json")
except Exception as e:  # noqa: BLE001
    out.append(f"  失败 -> {type(e).__name__}: {str(e)[:300]}")

from pathlib import Path as _P
_P(r"C:\Users\David\AppData\Local\Temp\opencode\llmclient.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
