"""Does the stored line duration match the audio that was actually written?"""
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
    print(f"=== {name} ===")
    for ep in p.episodes:
        tl = build_timeline(ep)
        for t in tl.lines:
            l = t.line
            if not l.audio_path:
                continue
            ap = store.abs(l.audio_path)
            real = ff.probe_duration(ap) if ap.exists() else 0.0
            stored = l.duration or 0.0
            if abs(real - stored) > 0.25:
                print(f"  {l.id} {l.speaker[:6]:6s} 存储 {stored:6.2f}s  "
                      f"实际 {real:6.2f}s  差 {real-stored:+.2f}  「{l.text[:18]}」")
