"""What the run was doing when it stopped, and when.

The progress file was written at 01:18 and the project record changed at
01:20, and nothing has run since. Whether the stop was a request or a
crash is written in the log, and the difference matters: a crash has a
traceback at the end, a stop has a message saying it was asked to stop.
"""
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
root = Path(r"E:\dramakit")
proj = next(d for d in (root / "projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())

out.append("=== 时间线 ===")
for label, ts in (("progress.json 写入", 1793553523),):
    out.append(f"  {label}: "
               f"{datetime.datetime.fromtimestamp(ts).isoformat()}")
out.append(f"  project.json updated_at: "
           f"{json.loads((proj/'project.json').read_text(encoding='utf-8'))['meta'].get('updated_at')}")
out.append(f"  现在: {datetime.datetime.now().isoformat()}")

# --- find every log file, wherever it is kept --------------------------
out.append("")
out.append("=== 日志文件 ===")
cands = []
for base in (proj / "logs", root / "logs", root / "var" / "logs",
             root / "dramakit" / "logs"):
    if base.exists():
        cands.extend([f for f in base.rglob("*") if f.is_file()])
for f in cands:
    out.append(f"  {f}  {f.stat().st_size/1024:.0f} KB  "
               f"{datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()}")
if not cands:
    out.append("  没找到日志目录")

# --- the last lines of the largest / newest ---------------------------
for f in sorted(cands, key=lambda x: x.stat().st_mtime, reverse=True)[:2]:
    out.append("")
    out.append(f"=== {f.name} 末尾 ===")
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        out.append(f"  读不了: {e}")
        continue
    lines = text.split("\n")
    for line in lines[-45:]:
        if line.strip():
            out.append("  " + line[:190])

    # what kind of ending was it
    out.append("")
    out.append("=== 结尾性质 ===")
    tail = "\n".join(lines[-40:])
    for kw in ("stop", "停止", "中断", "interrupt", "Traceback",
               "Error", "Exception", "KeyboardInterrupt", "Killed",
               "done", "完成"):
        n = tail.count(kw)
        if n:
            out.append(f"  尾部出现 {kw!r}: {n} 次")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\projlog.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
