"""A long answer from the strata engine - the shape the pipeline needs.

The pipeline asks for a whole scene of a screenplay as JSON, with a
budget of 128k tokens.  That is a long generation, and a long
generation is where a server can fall over.
"""
import json
import time
import urllib.error
import urllib.request

URL = "http://192.168.31.8:8080/v1/chat/completions"
MODEL = "qwen3.8-flash-next-iq3_xxs"

PROMPT = ("写一集都市短剧的剧本，只要 JSON，格式 "
          '{"scenes":[{"summary":"一句话","lines":[{"speaker":"","text":"","emotion":""}]}]}，'
          "要 4 场，每场 8 句台词，对话要冲突。")


def ask(mt, label):
    body = {"model": MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": mt, "stream": False,
            "response_format": {"type": "json_object"}}
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read())
        m = d["choices"][0]["message"]
        content = m.get("content") or ""
        print("  %-14s %6.1fs  content %5d 字  finish=%-8s 用了 %6d token"
              % (label, time.time() - t0, len(content),
                 d["choices"][0].get("finish_reason"),
                 d["usage"]["completion_tokens"]))
        try:
            obj = json.loads(content)
            print("     解析出来: %d 场" % len(obj.get("scenes", [])))
        except Exception as e:  # noqa: BLE001
            print("     解析失败:", str(e)[:80])
    except urllib.error.HTTPError as e:
        print("  %-14s %6.1fs  HTTP %s  %s"
              % (label, time.time() - t0, e.code, e.read()[:160]))
    except Exception as e:  # noqa: BLE001
        print("  %-14s %6.1fs  %s: %s"
              % (label, time.time() - t0, type(e).__name__, str(e)[:120]))


print("流水线那种长度：")
ask(4000, "max=4000")
ask(12000, "max=12000")
ask(30000, "max=30000")
