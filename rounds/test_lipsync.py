"""Try the mouth-sync on one shot of the finished episode.

    python rounds/test_lipsync.py 轮次09_09
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.lipsync import _musetalk, _scene_wav, ff_duration
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(Path(r"E:\\dramakit\\projects") / name))
ep = ctx.target_episodes()[0]
tl = ctx.timeline(ep)

for tsc in tl.scenes:
    for ts in tsc.shots:
        shot = ts.shot
        if not shot.video_path:
            continue
        video = ctx.store.abs(shot.video_path)
        if not video.exists():
            continue
        placed = []
        for t in tsc.lines:
            if t.line.kind.value != "dialogue":
                continue
            if not (ts.start - 0.02 <= t.start < ts.start + ts.duration):
                continue
            if not t.line.audio_path:
                continue
            placed.append((t.start - tsc.start, ctx.store.abs(t.line.audio_path)))
        if not placed:
            continue
        dur = ff_duration(video) or ts.duration
        wav = video.parent / f"{shot.id}_line.wav"
        if not _scene_wav(placed, ts.start - tsc.start, dur, wav):
            continue
        out = video.parent.parent / "lipsync" / f"{shot.id}.mp4"
        print(f"镜头 {shot.id}  {dur:.2f}s  {len(placed)} 句  -> {out.name}")
        ok = _musetalk(ctx, [(video, wav, out)]).get(out, False)
        print("口型对齐:", "成功" if ok else "失败")
        if ok:
            # side by side: before and after, a few frames
            tmp = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode")
            for tag, src in (("before", video), ("after", out)):
                d = tmp / f"ls_{tag}"
                d.mkdir(parents=True, exist_ok=True)
                for i in range(4):
                    at = dur * (i + 0.5) / 4
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}",
                                    "-i", str(src), "-frames:v", "1", "-vf",
                                    "crop=iw*0.5:ih*0.7:iw*0.25:ih*0.15,scale=420:-1",
                                    str(d / f"{i}.jpg")], capture_output=True)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1",
                                "-i", str(d / "%d.jpg"), "-vf",
                                "tile=4x1:margin=4:padding=4:color=0x202020",
                                "-frames:v", "1", str(tmp / f"ls_{tag}.jpg")],
                               capture_output=True)
                print(f"  对比图: {tmp / f'ls_{tag}.jpg'}")
        wav.unlink(missing_ok=True)
        raise SystemExit(0)
print("没有可用的镜头")
