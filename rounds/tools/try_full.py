"""One chapter, through the real pipeline, up to the shot list.

The two stages that were wrong are the two that cost the most: the
adaptation and the coverage.  This runs them on a real chapter and
prints what came out - the scenes, the lines, the shot list with its
angles, and the numbers the quality check takes.
"""
import json
import pathlib
import shutil
import sys
import time
import urllib.request

sys.path.insert(0, r"E:\dramakit")

BASE = "http://127.0.0.1:8080"
NAME = "分镜验证3"


def post(path, body):
    req = urllib.request.Request(BASE + path,
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=120) as r:
        return json.loads(r.read())


# a real chapter of a real book
src = pathlib.Path(r"E:\dramakit\projects\_trash")
files = []
for d in sorted(src.glob("*/source/volumes/*.txt")):
    if "ch001" in d.name:
        files = [d]
        break
if not files:
    for d in sorted(src.glob("*/source/volumes/*.txt")):
        files = [d]
        break
chapter = files[0]
text = chapter.read_text(encoding="utf-8", errors="replace")
print("原文:", chapter.name, len(text), "字")

up = post("/api/upload", {"name": NAME, "file": chapter.name, "text": text})
print("建工程:", up.get("slug"), up.get("ok"))
slug = up["slug"]

run = post("/api/run", {"project": slug, "chapters": [1],
                         "stages": ["ingest", "analyze", "segment", "script",
                                    "storyboard"]})
print("开跑:", run.get("ok"), run.get("job"))
job = run.get("job")

for _ in range(360):
    time.sleep(5)
    j = get("/api/jobs?id=" + job).get("job") or {}
    if j.get("status") in ("done", "error", "interrupted"):
        break
print("任务:", j.get("status"), str(j.get("error") or "")[:200])

from dramakit.pipeline.qc import _coverage_metrics  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

store = None
for r in sorted(pathlib.Path(r"E:\dramakit\projects").glob("*/project.json")):
    s = ProjectStore.open(r.parent)
    if s.load().meta.name == NAME:
        store = s
        break
if store is None:
    raise SystemExit("找不到工程")
proj = store.load()
ep = proj.episodes[0]
print(f"\n=== 第{ep.index}集《{ep.title}》 {len(ep.scenes)} 场 "
      f"{ep.total_shots} 镜 ===")
for sc in ep.scenes:
    print(f"\n【{sc.location}·{sc.time_of_day}】{sc.summary}")
    for l in sc.lines:
        print(f"   {l.speaker}（{l.emotion}）: {l.text}")
print("\n=== 分镜 ===")
for sc in ep.scenes:
    for sh in sc.shots:
        print(f"  {sh.index:2d}. {sh.shot_type.value:4} {sh.angle:4} "
              f"{sh.height:3} {sh.lens:3} 主体={sh.subject[:12]:14} "
              f"线={sh.line_indices} 人={'、'.join(sh.characters)}")
        print(f"      {sh.action[:100]}")

metrics, warnings = _coverage_metrics(ep)
print("\n=== 覆盖度体检 ===")
for k, v in metrics.items():
    print(f"  {k}: {v}")
for w in warnings:
    print("  ! " + w)
