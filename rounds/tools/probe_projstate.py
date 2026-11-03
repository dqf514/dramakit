"""Where the project stopped, and what the system says about it.

A job was terminated and the console shows it as not running. Two things
could explain that: the process died and the next boot wrote down what it
left, or nothing was ever started again because nobody asked. The first is
what the boot-time cleanup is for; the second is a missing button.

So the record is read as it stands - the stages, their statuses, and the
last progress written - to tell which of the two this is.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
root = Path(r"E:\dramakit\projects")
proj = next((d for d in root.iterdir()
             if d.is_dir() and (d / "project.json").exists()), None)
out.append(f"项目: {proj.name}")

raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))

out.append("")
out.append("=== 项目级 stage_status ===")
for k, v in (raw.get("stage_status") or {}).items():
    out.append(f"  {k:16} {v}")

out.append("")
out.append("=== meta（跑过什么、记住什么）===")
meta = raw.get("meta") or {}
if not meta:
    out.append("  （空）")
for k in sorted(meta):
    v = meta[k]
    s = json.dumps(v, ensure_ascii=False)
    out.append(f"  {k:24} {s[:160]}")

out.append("")
out.append("=== episodes ===")
eps = raw.get("episodes") or []
out.append(f"  {len(eps)} 集")
for ep in eps[:14]:
    if not isinstance(ep, dict):
        continue
    out.append(f"  ep{ep.get('index')} {str(ep.get('title'))[:18]:20} "
               f"status={ep.get('status'):12} stage={ep.get('stage_status')}")
    shots = ep.get("shots") or []
    if shots:
        done = sum(1 for s in shots if isinstance(s, dict) and s.get("status") == "done")
        out.append(f"        镜 {done}/{len(shots)} 完成")

out.append("")
out.append("=== .progress.json ===")
pg = proj / ".progress.json"
if pg.exists():
    out.append(json.dumps(json.loads(pg.read_text(encoding="utf-8")),
                          ensure_ascii=False, indent=2))
else:
    out.append("  不存在")

out.append("")
out.append("=== 各产物目录计数 ===")
for sub in ("images", "video", "audio", "episodes", "subs", "video_final", "output"):
    p = proj / sub
    if not p.exists():
        out.append(f"  {sub:12} 不存在")
        continue
    fs = [f for f in p.rglob("*") if f.is_file()]
    out.append(f"  {sub:12} {len(fs):>4} 个文件")

# --- is there a way to resume at all? ----------------------------------
out.append("")
out.append("=== 有没有恢复/续跑的入口 ===")
import re
cli = Path(r"E:\dramakit\dramakit\cli.py").read_text(encoding="utf-8")
for m in re.finditer(r'@app\.command\(name="([^"]+)"\)|@app\.command\(\)\s*\ndef ([a-z_]+)\(', cli):
    name = m.group(1) or m.group(2)
    out.append(f"  CLI: {name}")

srv = Path(r"E:\dramakit\dramakit\web\server.py").read_text(encoding="utf-8")
for m in re.finditer(r'"(/api/[a-z_/]+)"', srv):
    pass
paths = sorted(set(re.findall(r'"(/api/[a-z_/]+)"', srv)))
out.append("")
out.append("  API 端点:")
for pth in paths:
    out.append(f"      {pth}")

# resume-related words anywhere
out.append("")
out.append("  含 resume/续跑/恢复 的位置:")
for f in Path(r"E:\dramakit\dramakit").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    for n, line in enumerate(t.split("\n"), 1):
        if re.search(r'resume|续跑|恢复', line):
            out.append(f"      {f.name}:{n} {line.strip()[:110]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\projstate.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
