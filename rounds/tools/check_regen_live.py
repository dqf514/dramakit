"""Press the button for real, and see the clip come out.

The code path is checked; this is the whole thing: the console's
endpoint, the job, the card, and the file at the end. The shot used
already has a clip, and the seed is the same, so the render replaces
the clip with the same clip - nothing is lost if it goes wrong.
"""
import json
import pathlib
import time
import urllib.error
import urllib.request

PROJ = pathlib.Path(r"E:\dramakit\projects\星际骷髅兵")
CONSOLE = "http://127.0.0.1:8080"


def post(path, body, timeout=90):
    req = urllib.request.Request(
        CONSOLE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def get(path, timeout=60):
    with urllib.request.urlopen(CONSOLE + path, timeout=timeout) as r:
        return json.loads(r.read())


raw = json.loads((PROJ / "project.json").read_text(encoding="utf-8"))
target = None
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            if sh.get("image_path") and sh.get("video_path"):
                target = (ep["index"], sh["id"], sh["video_path"])
                break
        if target:
            break
    if target:
        break

if not target:
    print("  没有既有片子的镜头可试")
    raise SystemExit(1)

ep_index, shot_id, vid = target
old = PROJ / vid
old_mtime = old.stat().st_mtime
print(f"  镜头：第 {ep_index} 集 / {shot_id}")
print(f"  原来的片子：{old.name}（{old.stat().st_size/1048576:.1f} MB）")

st, r = post("/api/shot/regen", {"project": "星际骷髅兵", "episode": ep_index,
                                "shot_id": shot_id, "mode": "video"})
print("  提交:", st, json.dumps(r, ensure_ascii=False)[:120])
jid = r.get("job")
if not jid:
    raise SystemExit(1)

t0 = time.time()
while time.time() - t0 < 2400:
    time.sleep(10)
    job = get(f"/api/jobs?id={jid}").get("job") or {}
    if job.get("status") not in ("queued", "running"):
        print(f"  任务结束：{job.get('status')}  用时 {time.time()-t0:.0f} 秒")
        print("  结果:", json.dumps(job.get("result"), ensure_ascii=False)[:300])
        print("  错误:", str(job.get("error"))[:300])
        break
else:
    print("  超时")

print()
print("  文件有没有变：", old.stat().st_mtime != old_mtime,
      "大小 %.1f MB" % (old.stat().st_size / 1048576))
