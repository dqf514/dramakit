"""Did the run take the three chapters, or the whole book?

The stage is at character, segment has not run, so the cut cannot be
watched yet - but the analysis can: analyze reads the season's chapters,
and whether it read three or four hundred and eighty-five is written in
what it was given. This reads the project's real layout (seasons live on
the project, not in meta) and the evidence on disk.
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
    out.append(f"  集数         : {len(data.get('episodes') or [])}")
    out.append(f"  chapters     : {len(m.get('chapters') or [])}")
    out.append(f"  chosen       : {m.get('chosen_chapters')}")
    out.append(f"  segmented    : {m.get('segmented_chapters')}")
    out.append(f"  chapter_season 映射: {m.get('chapter_season')}")

    seasons = data.get("seasons") or []
    out.append(f"  seasons (根上): {len(seasons)} 个")
    for s in seasons:
        out.append(f"    第{s.get('index')}季 status={s.get('status')} "
                   f"chapters={s.get('chapters')} ep={s.get('episode_range')} "
                   f"stages={json.dumps(s.get('stage_status', {}), ensure_ascii=False)}")

    canon = data.get("canon") or {}
    out.append(f"  canon.done_chapters: {canon.get('done_chapters')}")
    out.append(f"  canon.characters   : {list((canon.get('characters') or {}).keys())}")

    src = d / "source"
    if src.exists():
        eps = sorted(src.glob("ep_*.txt"))
        out.append(f"  ep_*.txt     : {len(eps)}")
        out.append(f"  cleaned.txt  : {src.joinpath('cleaned.txt').stat().st_size if (src/'cleaned.txt').exists() else '无'} 字节")

    chars = data.get("characters") or []
    out.append(f"  角色         : {len(chars)}")
    cdir = d / "characters"
    if cdir.exists():
        imgs = [f for f in cdir.rglob("*.png")] + [f for f in cdir.rglob("*.jpg")]
        out.append(f"  角色参考图   : {len(imgs)} 张")

    out.append(f"  project.json 改于 "
               f"{time.strftime('%H:%M:%S', time.localtime(pj.stat().st_mtime))}")
    out.append("")

out.append("现在 " + time.strftime("%H:%M:%S"))

# what the run has logged, if the tail is up
try:
    import urllib.request
    with urllib.request.urlopen("http://127.0.0.1:8080/api/logs?n=30", timeout=10) as r:
        lines = json.loads(r.read()).get("lines", [])
    out.append("")
    out.append(f"=== 运行日志（{len(lines)} 行）===")
    for ln in lines:
        ts = time.strftime("%H:%M:%S", time.localtime(ln["t"]))
        out.append(f"  {ts} [{ln['lv']}] {ln['msg'][:160]}")
except Exception as e:  # noqa: BLE001
    out.append(f"日志接口: {type(e).__name__} {e}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\scope.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
