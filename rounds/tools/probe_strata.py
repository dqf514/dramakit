"""Why does the Strata model time out?

It is asked the way the pipeline asks it - the same client, the same
address, the same model name - so the answer is the answer the pipeline
gets.
"""
import json
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config


def post(url, model, timeout=90):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "只说两个字"}],
        "max_tokens": 16,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        text = ""
        try:
            text = (data["choices"][0]["message"]["content"] or "")[:60]
        except Exception:  # noqa: BLE001
            text = json.dumps(data, ensure_ascii=False)[:200]
        return f"{time.time() - t0:.1f}s  {text}"
    except urllib.error.HTTPError as e:
        return f"{time.time() - t0:.1f}s  HTTP {e.code}  {e.read()[:200]!r}"
    except Exception as e:  # noqa: BLE001
        return f"{time.time() - t0:.1f}s  {type(e).__name__}: {str(e)[:160]}"


def main():
    cfg = Config.load(r"E:\dramakit\config\default.yaml")
    entry = None
    for e in (cfg.models.entries or []):
        if "192.168.31.8" in (e.base_url or ""):
            entry = e
    if entry is None:
        print("配置里没有 192.168.31.8 的模型")
        return 1
    print("配置里的：")
    print("  base_url:", entry.base_url)
    print("  model   :", entry.model)
    print("  key     :", (entry.api_key or "")[:12] or "（空）")
    print()
    server = "http://192.168.31.8:8080"
    print("服务器报的模型名：")
    try:
        with urllib.request.urlopen(server + "/v1/models", timeout=10) as r:
            for m in json.loads(r.read()).get("data", []):
                print("  ", m.get("id"))
    except Exception as e:  # noqa: BLE001
        print("  问不到：", e)
    print()
    for label, url, model in (
        ("照配置来", entry.base_url.rstrip("/") + "/chat/completions", entry.model),
        ("补上 /v1", server + "/v1/chat/completions", entry.model),
        ("补上 /v1 + 正确的模型名", server + "/v1/chat/completions",
         "qwen3.8-flash-next-iq3_xxs"),
    ):
        print(f"  {label}:")
        print(f"    {url}  model={model}")
        print("    ->", post(url, model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
