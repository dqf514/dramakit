"""What survived the stop, and what did not.

The run was killed mid-script: the segment stage had finished and saved,
the script stage had not. This reads the project to see exactly what is
on disk, so nothing has to be redone that does not need to be - and so
the next run can start from the right place.
"""
import json
from pathlib import Path

out = []
root = Path(r"E:\dramakit\projects\妖怪志")

d = json.loads((root / "project.json").read_text(encoding="utf-8"))
m = d.get("meta", {})

out.append("=== project.json ===")
out.append(f"  stage_status: {json.dumps(d.get('stage_status', {}), ensure_ascii=False)}")
out.append(f"  episodes: {len(d.get('episodes') or [])} 集（对象）")
out.append(f"  characters: {len(d.get('characters') or [])} 个")
out.append(f"  meta.chapters: {len(m.get('chapters') or [])} 章")
out.append(f"  meta.chosen_chapters: {m.get('chosen_chapters') or '（空）'}")
out.append(f"  meta.segmented_chapters: {m.get('segmented_chapters') or '（空）'}")

out.append("")
out.append("=== 磁盘上的源文件 ===")
src = root / "source"
vols = sorted((src / "volumes").glob("*.txt")) if (src / "volumes").exists() else []
eps = sorted(src.glob("ep_*.txt"))
out.append(f"  volumes/ 章节文件: {len(vols)} 个")
out.append(f"  ep_*.txt 集原文:   {len(eps)} 个")
if eps:
    out.append(f"    最早: {eps[0].name}  {eps[0].stat().st_size} 字节")
    out.append(f"    最新: {eps[-1].name}  {eps[-1].stat().st_size} 字节")

out.append("")
out.append("=== 已完成的资产 ===")
for sub in ("characters", "locations"):
    p = root / sub
    n = len([f for f in p.rglob("*") if f.is_file()]) if p.exists() else 0
    out.append(f"  {sub}/: {n} 个文件")
for sub in ("images", "video", "audio", "subs", "covers"):
    p = root / sub
    n = len([f for f in p.rglob("*") if f.is_file()]) if p.exists() else 0
    if n:
        out.append(f"  {sub}/: {n} 个文件")

out.append("")
out.append("=== 判断 ===")
seg_done = d.get("stage_status", {}).get("segment") == "done"
scr_done = d.get("stage_status", {}).get("script") == "done"
out.append(f"  分集已完成并落盘: {'是' if seg_done else '否'}")
out.append(f"  剧本已完成: {'是' if scr_done else '否（被中止，且未落盘）'}")
if seg_done and not d.get("episodes"):
    out.append("  -> 分集的集原文在磁盘上，但 Episode 对象没写进 project.json")
    out.append("     因为 segment.run() 只在末尾 save()，而脚本阶段已经把状态改成 running")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\after.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
