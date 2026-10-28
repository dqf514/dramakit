"""How many tokens does the review need? The model thinks before it answers."""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
import httpx
from dramakit.config import Config
from dramakit.review import SYSTEM, _facts, _frames
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
root = Path(r"E:\dramakit\projects\轮次09_09")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.target_episodes()[0]
tmp = root / "tmp" / "review"
frames = _frames(ctx, ep, tmp, limit=8)

content = [{"type": "text", "text": _facts(ctx, ep)}]
for p in frames:
    b64 = base64.b64encode(Path(p).read_bytes()).decode("ascii")
    content.append({"type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

url = cfg.llm.base_url.rstrip("/") + "/chat/completions"
headers = {"Content-Type": "application/json",
           "Authorization": f"Bearer {cfg.llm.api_key}"}
for mt in (4000, 16000, 32000):
    payload = {"model": cfg.llm.model,
               "messages": [{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": content}],
               "max_tokens": mt, "stream": False,
               "temperature": 0.2}
    r = httpx.post(url, json=payload, headers=headers, timeout=600.0,
                   trust_env=False)
    d = r.json()
    m = (d.get("choices") or [{}])[0]
    msg = m.get("message", {})
    usage = d.get("usage", {})
    print(f"max_tokens={mt}: finish={m.get('finish_reason')} "
          f"内容长度={len(msg.get('content') or '')} "
          f"思考长度={len(msg.get('reasoning_content') or '')} "
          f"tokens={usage.get('completion_tokens')}")
    if msg.get("content"):
        print("   内容前 200:", msg["content"][:200].replace("\n", " "))
