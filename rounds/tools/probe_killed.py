"""Whether a job was running when the service was restarted.

The check that said there was no job was wrong: /api/jobs looks a job up
by id, and with no id given it looks up an empty one, which is never
there. So the answer it gave proves nothing, and the restart that followed
may have killed work in progress.

The file times settle it. A running job writes as it goes, and the stage
record is written by the runner when it starts - so whatever was written
between the last known moment and the restart is what was alive, and what
was not written afterwards is what died with the process.
"""
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []


def ts(t: float) -> str:
    return datetime.datetime.fromtimestamp(t).strftime("%H:%M:%S")


proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
out.append(f"项目 {proj.name}")
out.append("")
out.append("=== 关键文件的最后修改时间 ===")
for name in ("project.json", ".progress.json"):
    p = proj / name
    if p.exists():
        out.append(f"  {name:20} {ts(p.stat().st_mtime)}")

out.append("")
out.append("=== 产物文件（按时间排序，最后 15 个）===")
files = [f for f in proj.rglob("*")
         if f.is_file() and f.suffix.lower() in
         (".png", ".jpg", ".mp4", ".mp3", ".json", ".txt", ".srt")]
files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
for f in files[:15]:
    out.append(f"  {ts(f.stat().st_mtime)}  {f.stat().st_size/1024:8.0f} KB  "
               f"{f.relative_to(proj)}")

out.append("")
out.append("=== 视频文件 ===")
for f in sorted((proj / "video").glob("*.mp4"), key=lambda x: x.stat().st_mtime):
    out.append(f"  {ts(f.stat().st_mtime)}  {f.stat().st_size/1024:.0f} KB  {f.name}")

out.append("")
out.append("=== 图片（最早 5 个 / 最新 5 个）===")
imgs = sorted((proj / "images").glob("*"), key=lambda x: x.stat().st_mtime)
for f in imgs[:5]:
    out.append(f"  最早 {ts(f.stat().st_mtime)}  {f.name}")
out.append("  ...")
for f in imgs[-5:]:
    out.append(f"  最新 {ts(f.stat().st_mtime)}  {f.name}")

# --- the stage record, and what a boot cleanup would have done ----------
out.append("")
out.append("=== 阶段状态（谁停在 running 就会被启动清理改写）===")
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
for k, v in (raw.get("stage_status") or {}).items():
    out.append(f"  {k:14} {v}")
out.append(f"  （没有 visual 这一项 = visual 阶段从未以阶段身份启动）")

# --- the two moments the question turns on ----------------------------
out.append("")
out.append("=== 时间线 ===")
out.append("  01:08:46  我第一次读 project.json 的 updated_at")
out.append(f"  {ts((proj/'.progress.json').stat().st_mtime)}  .progress.json 最后写入")
out.append(f"  {ts((proj/'project.json').stat().st_mtime)}  project.json 最后写入")
out.append("  01:48:04  当前服务进程启动（我第二次重启）")
out.append(f"  {datetime.datetime.now().strftime('%H:%M:%S')}  现在")

out.append("")
out.append("=== 结论所依赖的判据 ===")
pg = json.loads((proj / ".progress.json").read_text(encoding="utf-8"))
out.append(f"  .progress.json = {json.dumps(pg, ensure_ascii=False)}")
out.append("  若 visual 阶段在跑，stage_status 里会有 visual=running，"
           "启动清理会把它改成 interrupted")
vs = (raw.get("stage_status") or {})
out.append(f"  实际 stage_status 有 visual 吗: {'visual' in vs}")
out.append(f"  promptgen 状态: {vs.get('promptgen')}")
ep_vis = [k for e in raw.get("episodes", []) if isinstance(e, dict)
          for k in (e.get("stage_status") or {}) if "vis" in k]
out.append(f"  episodes 里有 visual 相关吗: {ep_vis[:5]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\killed.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
