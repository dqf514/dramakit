"""Wait for the running job and show what it made."""
import json
import pathlib
import sys
import time
import urllib.request

sys.path.insert(0, r"E:\dramakit")

BASE = "http://127.0.0.1:8080"
NAME = "分镜验证3"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=120) as r:
        return json.loads(r.read())


jobs = get("/api/jobs?limit=12").get("jobs") or []
run = next((j for j in jobs if j.get("kind") == "run_pipeline"
            and j.get("status") == "running"), None)
if not run:
    print("没有在跑的任务")
    raise SystemExit(1)
jid = run["id"]
print("等任务", jid)
for _ in range(600):
    time.sleep(5)
    j = get("/api/jobs?id=" + jid).get("job") or {}
    if j.get("status") in ("done", "error", "interrupted"):
        break
print("任务:", j.get("status"), str(j.get("error") or "")[:200])

from dramakit.pipeline.qc import _coverage_metrics  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402

store = None
for r in sorted(pathlib.Path(r"E:\dramakit\projects").glob("*/project.json")):
    s = ProjectStore.open(r.parent)
    p = s.load()
    if p.episodes and p.episodes[0].scenes and p.episodes[0].scenes[0].shots:
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
        print(f"      职责：{sh.purpose}")
        print(f"      {sh.action[:110]}")
metrics, warnings = _coverage_metrics(ep)
print("\n=== 覆盖度体检 ===")
for k, v in metrics.items():
    print(f"  {k}: {v}")
for w in warnings:
    print("  ! " + w)
