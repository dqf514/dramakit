"""Reproduce the scene voice assembly for round 2."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.media import ffmpeg as ff
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
proj = Path(r"E:\dramakit\projects") / "轮次02_02"
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
tl = build_timeline(ep)

for si, tscene in enumerate(tl.scenes):
    print(f"--- 场景 {si} 时长 {tscene.duration:.2f}s，{len(tscene.lines)} 句")
    total = 0.0
    for i, tl_line in enumerate(tscene.lines):
        l = tl_line.line
        if tl_line.is_narration:
            print(f"    {i} 旁白(跳过) 「{l.text[:16]}」")
            continue
        d = max(l.duration, 0.05)
        ap = ctx.store.abs(l.audio_path) if l.audio_path else None
        real = ff.probe_duration(ap) if ap and ap.exists() else 0.0
        print(f"    {i} {l.speaker[:6]:6s} dur={d:5.2f} 音频={real:5.2f} "
              f"存在={bool(ap and ap.exists())} 「{l.text[:14]}」")
        total += real if real else d
    print(f"    => 拼起来的真实总长应为 {total:.2f}s")
