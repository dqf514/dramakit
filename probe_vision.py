"""Does the endpoint take pictures? Try the shapes an OpenAI-compatible API does."""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
import httpx
from dramakit.config import Config

cfg = Config.load(r"E:\dramakit\config\default.yaml")
img = Path(sys.argv[1] if len(sys.argv) > 1 else
           r"E:\dramakit\projects\轮次09_09\tmp\review\review_00.jpg")
b64 = base64.b64encode(img.read_bytes()).decode("ascii")
url = cfg.llm.base_url.rstrip("/") + "/chat/completions"
headers = {"Content-Type": "application/json"}
if cfg.llm.api_key:
    headers["Authorization"] = f"Bearer {cfg.llm.api_key}"

models = [cfg.llm.model, "MiniMax-M3", "MiniMax-M2.5", "MiniMax-VL-01",
          "MiniMax-Text-01"]
for model in models:
    for style in ("datauri", "url"):
        content = [{"type": "text", "text": "这张图里有什么？一句话。"}]
        if style == "datauri":
            content.append({"type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        else:
            content.append({"type": "image_url", "image_url": {"url": img.as_uri()}})
        payload = {"model": model,
                   "messages": [{"role": "user", "content": content}],
                   "max_tokens": 300, "stream": False}
        try:
            r = httpx.post(url, json=payload, headers=headers, timeout=120.0,
                           trust_env=False)
            body = r.text[:220]
            ok = r.status_code == 200
            print(f"[{r.status_code}] {model} / {style}: {body}")
            if ok:
                try:
                    data = r.json()
                    txt = (data.get("choices") or [{}])[0].get("message", {}).get("content")
                    print(f"      -> 内容: {str(txt)[:160]}")
                except Exception as e:  # noqa: BLE001
                    print("      解析失败", e)
        except Exception as e:  # noqa: BLE001
            print(f"异常 {model}/{style}: {type(e).__name__} {str(e)[:100]}")
