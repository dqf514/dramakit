"""Does every shot clip last as long as the timeline wants it to?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff
from dramakit.pipeline.base import build_timeline
from dramakit.project import ProjectStore

for name in ("轮次01_01", "轮次02_02", "轮次03_03"):
    proj = Path(r"E:\dramakit\projects") / name
    store = ProjectStore(proj)
    p = store.load()
    ep = p.episodes[0]
    tl = build_timeline(ep)
    tmp = proj / "tmp" / "ep_001"
    clip_dur = {}
    for c in sorted(tmp.glob("shot_*.mp4")):
        clip_dur[c.stem.replace("shot_", "")] = ff.probe_duration(c)
    total_real = sum(clip_dur.values())
    print(f"=== {name} ===")
    print(f"  时间线总长 {tl.duration:.2f}s   片段实际总长 {total_real:.2f}s   "
          f"成片 {ff.probe_duration(proj/'episodes'/'ep_001.mp4'):.2f}s")
    bad = 0
    for ts in tl.shots:
        key = ts.shot.id.replace("sh-", "")
        real = clip_dur.get(key)
        if real is None:
            continue
        if real < ts.duration - 0.15:
            bad += 1
            print(f"    {ts.shot.id}  要 {ts.duration:5.2f}s  实际 {real:5.2f}s  "
                  f"缺 {ts.duration-real:.2f}s")
    if not bad:
        print("    所有片段都够长")
