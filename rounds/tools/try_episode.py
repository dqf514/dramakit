"""Run the script and the storyboard for one episode, and look.

The episode's script and storyboard are put back to pending - the
script was rewritten with the editor and the scenes came out with no
shots, because the storyboard had already said it was done - and then
the two stages are run for that episode only.

    python rounds/tools/try_episode.py [episode]
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request

ROOT = pathlib.Path(r"E:\dramakit")
sys.path.insert(0, str(ROOT))

from dramakit.models import Status  # noqa: E402
from dramakit.pipeline.script import _flatness, _parse_scenes  # noqa: E402
from dramakit.pipeline.storyboard import _beat_coverage, _cuts  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

PROJECT = "穿成亿万总裁他前妻"
BASE = "http://127.0.0.1:8080"
n = int(sys.argv[1]) if len(sys.argv) > 1 else 1


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read())


store = ProjectStore.open(ROOT / "projects" / PROJECT)
proj = store.load()
for ep in proj.episodes:
    for s in ("script", "storyboard"):
        if s in ep.stage_status:
            ep.stage_status[s] = Status.PENDING
    for sc in ep.scenes:
        sc.shots = []
store.save(proj)
print("  状态已重置")

r = post("/api/run", {"project": PROJECT, "stages": ["script", "storyboard"],
                      "episodes": [n], "overrides": {}})
jid = r.get("job")
print("  任务:", jid)
t0 = time.time()
while time.time() - t0 < 1200:
    j = get("/api/jobs?id=" + jid).get("job") or {}
    if j.get("status") in ("done", "error", "interrupted", "cancelled"):
        print("  结果:", j.get("status"), (j.get("error") or "")[:160])
        break
    time.sleep(5)

print()
print("=== 日志 ===")
for l in (get("/api/logs?n=200").get("lines") or []):
    m = l["msg"]
    if any(k in m for k in ("script", "storyboard", "打磨", "拍点", "一镜到底")):
        print("  [%s] %s" % (l["lv"], m[:190]))

print()
store = ProjectStore.open(ROOT / "projects" / PROJECT)
proj = store.load()
ep = next(e for e in proj.episodes if e.index == n)
print("=== 第%d集 ===" % n)
pairs, lines = _flatness(ep.scenes)
print("  台词 %d 句，其中 %d 处一问一答（%d%%）" % (lines, pairs, int(pairs * 100 / max(1, lines))))
beats = sum(len(sc.beats) for sc in ep.scenes)
filmed = 0
for sc in ep.scenes:
    f, b = _beat_coverage(sc)
    filmed += f
shots = [sh for sc in ep.scenes for sh in sc.shots]
cuts = [_cuts(sh.action or "") for sh in shots]
one = sum(1 for c in cuts if c <= 1)
print("  拍点 %d 个，拍到 %d 个（%d%%）" % (beats, filmed, int(filmed * 100 / max(1, beats))))
print("  %d 段，其中 %d 段是一镜到底（%d%%）；平均每段 %s 刀" % (
    len(shots), one, int(one * 100 / max(1, len(shots))),
    round(sum(cuts) / max(1, len(shots)), 1)))
for sc in ep.scenes[:1]:
    print()
    print("  【%s】%s" % (sc.location, sc.summary))
    print("   拍点:")
    for i, b in enumerate(sc.beats, 1):
        print("     %d. %s  %s" % (i, b.action, b.lines))
    print("   镜头:")
    for sh in sc.shots[:4]:
        print("     %s 景别=%s 角度=%s 时长=%s 台词=%s" % (
            sh.id[-6:], sh.shot_type, sh.angle, sh.duration, sh.line_indices))
        print("        %s" % (sh.action or "")[:260])
