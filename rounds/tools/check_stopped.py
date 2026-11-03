"""Is the run actually stopped, and what did it spend on the wrong season?

The console reports character running while the job registry says nothing
is running, which means either the stage is between writes or the state on
disk was left behind. The pictures it drew into a season-two folder are
the cost of the re-analysis picking the wrong season, so they are counted
here - they are duplicates of pictures that already exist in season one.
"""
import json
import time
from pathlib import Path

root = Path(r"E:\dramakit\projects\魔兽世界")
out = []

d = json.loads((root / "project.json").read_text(encoding="utf-8"))
out.append("stage: " + json.dumps(d.get("stage_status", {}), ensure_ascii=False))
out.append("季: " + json.dumps(
    [{"i": s.get("index"), "ch": s.get("chapters"),
      "st": {k: str(v.value if hasattr(v, "value") else v)
             for k, v in (s.get("stage_status") or {}).items()}}
     for s in d.get("seasons", [])], ensure_ascii=False))

cdir = root / "characters"
by_season: dict[str, list[str]] = {}
if cdir.exists():
    for f in cdir.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in (".png", ".jpg"):
            continue
        rel = f.relative_to(cdir)
        # characters/<who>/s2/x.png is a season-two copy
        key = str(rel.parent).replace("\\", "/")
        if "/s" in key.split("/")[-1]:
            by_season.setdefault(key, []).append(f.name)

out.append("")
out.append("=== 往第 2 季重复生成的图 ===")
if by_season:
    for k, v in sorted(by_season.items()):
        out.append(f"  {k}: {sorted(v)}")
    out.append(f"  合计 {sum(len(v) for v in by_season.values())} 张")
else:
    out.append("  （没有）")

# does anything still move?
out.append("")
pj = root / "project.json"
m0 = pj.stat().st_mtime
time.sleep(15)
m1 = pj.stat().st_mtime
out.append(f"15 秒内 project.json {'有变化' if m1 != m0 else '没变化'}")
recent = [f for f in root.rglob("*") if f.is_file()
          and time.time() - f.stat().st_mtime < 20]
out.append(f"最近 20 秒改动的文件: {len(recent)}")
for f in recent[:8]:
    out.append(f"  {time.strftime('%H:%M:%S', time.localtime(f.stat().st_mtime))} "
               f"{f.relative_to(root)}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\stopped2.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
