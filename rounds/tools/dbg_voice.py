"""Build the scene voice from the clips and measure it."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.media import ffmpeg as ff
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(Path(r"E:\\dramakit\\projects") / name))
ep = ctx.target_episodes()[0]
tl = ctx.timeline(ep)
tmp = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\mixdbg")
tmp.mkdir(parents=True, exist_ok=True)

for tsc in tl.scenes:
    items = []
    for ts in tsc.shots:
        if not ts.shot.video_path:
            continue
        clip = ctx.store.abs(ts.shot.video_path)
        if not clip.exists():
            continue
        items.append((str(clip), ts.start - tsc.start, ts.duration))
    print(f"场景 {tsc.scene.index}: {len(items)} 段，场景时长 {tsc.duration:.2f}")
    out = tmp / "voice_test.mp3"
    res = ff.mix_shot_audio(items, out, duration=tsc.duration)
    print("  合成结果:", res, "时长", round(ff.probe_duration(out), 2))
    # what the parts look like
    for path, st, ln in items[:3]:
        print(f"    起点 {st:5.2f} 长度 {ln:5.2f}  片段 {ff.probe_duration(path):5.2f}")
