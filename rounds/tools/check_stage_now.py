"""What is running now, and why each part takes as long as it does.

The stage says promptgen, but a file named sheet.jpg has been trickling
out every five minutes since the stage began - written by something that
is not the stage the console names. This reads the episode count, the
current stage's work, and who owns those files, so the wait is explained
rather than guessed at.
"""
import json
import time
from pathlib import Path

out = []
root = Path(r"E:\dramakit\projects\魔兽世界")
pj = root / "project.json"
d = json.loads(pj.read_text(encoding="utf-8"))
m = d.get("meta", {})

out.append("=== 阶段 ===")
out.append("  " + json.dumps(d.get("stage_status", {}), ensure_ascii=False))
out.append(f"  project.json 改于 {time.strftime('%H:%M:%S', time.localtime(pj.stat().st_mtime))}"
           f"   现在 {time.strftime('%H:%M:%S')}")

out.append("")
out.append("=== 分了几集（选了 3 章）===")
eps = d.get("episodes") or []
out.append(f"  集数: {len(eps)}")
for e in eps[:12]:
    ss = e.get("stage_status", {})
    done = [k for k, v in ss.items() if str(v).endswith("done")]
    out.append(f"    第{e.get('index')}集  {e.get('status')}  已完成 {done}  "
               f"{len(e.get('scenes') or [])} 场")
out.append(f"  chosen={m.get('chosen_chapters')}  segmented={m.get('segmented_chapters')}")
out.append(f"  季: {[(s.get('index'), s.get('chapters'), s.get('episode_range')) for s in (d.get('seasons') or [])]}")

# what has changed on disk in the last 40 minutes
out.append("")
out.append("=== 最近 40 分钟内改动的文件（按时间）===")
recent = []
for f in root.rglob("*"):
    if not f.is_file():
        continue
    age = time.time() - f.stat().st_mtime
    if age < 40 * 60:
        recent.append((f.stat().st_mtime, f, f.stat().st_size))
recent.sort()
for t, f, sz in recent[-25:]:
    out.append(f"  {time.strftime('%H:%M:%S', time.localtime(t))}  "
               f"{str(f.relative_to(root))[:70]:<70} {sz // 1024} KB")
if not recent:
    out.append("  （没有）")

out.append("")
out.append("=== sheet.jpg 是谁的 ===")
for f in sorted(root.rglob("sheet.*"), key=lambda x: x.stat().st_mtime)[-8:]:
    out.append(f"  {time.strftime('%H:%M:%S', time.localtime(f.stat().st_mtime))}  {f.relative_to(root)}")

# any log the run is writing
out.append("")
logs = sorted(root.rglob("*.log"), key=lambda x: x.stat().st_mtime)
out.append(f"=== 项目里的日志 {len(logs)} 个 ===")
for f in logs[-4:]:
    txt = f.read_text(encoding="utf-8", errors="replace")
    out.append(f"  {f.name}  {f.stat().st_size} B  末尾:")
    for line in txt.splitlines()[-8:]:
        out.append("    " + line[:170])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\now.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
