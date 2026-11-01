"""Is the new season making three chapters, or the whole book again?

The user picked three chapters and started a season. The question is
whether the run honoured that: segment reads chosen_chapters and cuts
nothing else, so the file counts and the timestamps say which happened.
"""
import json
import time
from pathlib import Path

out = []
root = Path(r"E:\dramakit\projects")

for d in sorted(root.iterdir()):
    pj = d / "project.json"
    if not (d.is_dir() and pj.exists()):
        continue
    data = json.loads(pj.read_text(encoding="utf-8"))
    m = data.get("meta", {})
    out.append(f"=== {d.name} ===")
    out.append("  stage_status : " + json.dumps(data.get("stage_status", {}), ensure_ascii=False))
    out.append(f"  集数(对象)   : {len(data.get('episodes') or [])}")
    out.append(f"  chapters 总数: {len(m.get('chapters') or [])}")
    out.append(f"  chosen       : {m.get('chosen_chapters')}")
    out.append(f"  segmented    : {m.get('segmented_chapters')}")
    seasons = m.get("seasons") or []
    out.append(f"  季记录       : {len(seasons)} 个")
    for s in seasons:
        out.append(f"    第{s.get('index')}季 status={s.get('status')} "
                   f"chapters={s.get('chapters')} ep_range={s.get('episode_range')}")
    src = d / "source"
    if src.exists():
        eps = sorted(src.glob("ep_*.txt"))
        vols = sorted((src / "volumes").glob("*.txt")) if (src / "volumes").exists() else []
        out.append(f"  volumes/     : {len(vols)} 个章节文件")
        out.append(f"  ep_*.txt     : {len(eps)} 个集原文")
        if eps:
            newest = max(eps, key=lambda f: f.stat().st_mtime)
            out.append(f"    最新 {newest.name}  "
                       f"{time.strftime('%H:%M:%S', time.localtime(newest.stat().st_mtime))}")
    out.append(f"  project.json 改于 "
               f"{time.strftime('%H:%M:%S', time.localtime(pj.stat().st_mtime))}")
    out.append("")

out.append("现在 " + time.strftime("%H:%M:%S"))
out.append("")
out.append("=== 服务器进程 ===")
import subprocess
r = subprocess.run(
    ["powershell", "-Command",
     "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
     "Where-Object { $_.CommandLine -match 'dj.exe' } | "
     "Select-Object ProcessId,CreationDate | Format-Table -AutoSize | Out-String"],
    capture_output=True, text=True)
out.append(r.stdout)

Path(r"C:\Users\David\AppData\Local\Temp\opencode\wherenow.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
