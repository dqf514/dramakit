"""Try the music graph on the local card and report what came out.

One track, so the cost of a wrong setting is one track. What is measured
is the thing that decides whether this is usable at all: how long a
track takes, and how big the file is - a music model that is fast but
writes silence is worse than no music at all.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, r"E:\dramakit\rounds\tools")
from build_music_wf import build  # noqa: E402

BASE = "http://127.0.0.1:8188"
OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\music_test")


def post(path, body, timeout=120):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(path, timeout=120):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


TAGS = ("cinematic underscore, instrumental, no vocals, tense suspense, "
        "strings and low piano, slow pulse, dark")

seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
OUT.mkdir(parents=True, exist_ok=True)

g = build(TAGS, seconds=seconds, seed=1234, bpm=90, key="C minor")
g["10"]["inputs"]["filename_prefix"] = "music/test"

t0 = time.time()
try:
    r = post("/prompt", {"prompt": g, "client_id": "musictest"})
except urllib.error.HTTPError as e:
    print("提交失败 %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:900]))
    raise SystemExit(1)
pid = r["prompt_id"]
print("已提交 pid=%s，%s 秒的曲子" % (pid, seconds))

while time.time() - t0 < 1800:
    time.sleep(5)
    hist = json.loads(get("/history/" + pid))
    rec = hist.get(pid)
    if not rec:
        continue
    st = rec.get("status") or {}
    if st.get("status_str") in ("success", "error"):
        break

dt = time.time() - t0
print("用时 %.1f 秒" % dt)
if st.get("status_str") != "success":
    for m in (st.get("messages") or []):
        if isinstance(m, list) and m[0] == "execution_error":
            e = m[1] if isinstance(m[1], dict) else {}
            print("错误:", json.dumps(e, ensure_ascii=False)[:900])
    raise SystemExit(1)

name = None
for out in (rec.get("outputs") or {}).values():
    for a in (out.get("audio") or []) + (out.get("gifs") or []):
        name = a.get("filename")
        sub = a.get("subfolder") or ""
        typ = a.get("type") or "output"
if not name:
    print("没有音频输出:", json.dumps(rec.get("outputs"), ensure_ascii=False)[:500])
    raise SystemExit(1)

data = get("/view?filename=%s&subfolder=%s&type=%s" % (name, sub, typ))
dest = OUT / name
dest.write_bytes(data)
print("产物:", dest, "%.0f KB" % (len(data) / 1024))

r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                    "format=duration,bit_rate", "-of", "json", str(dest)],
                   capture_output=True, text=True, timeout=60)
print("ffprobe:", (r.stdout or "").strip()[:300])
