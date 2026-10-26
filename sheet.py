"""Pull a contact sheet of frames from the finished episodes."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\sheets")
OUT.mkdir(parents=True, exist_ok=True)
root = Path(r"E:\dramakit\projects\测试短剧\episodes")

for ep in sorted(root.glob("ep_*.mp4")):
    dur = ff.probe_duration(ep)
    n = 12
    picks = [dur * (i + 0.5) / n for i in range(n)]
    parts = []
    for i, at in enumerate(picks):
        p = OUT / f"{ep.stem}_{i:02d}.jpg"
        ff.extract_frame(ep, p, at=at, width=480)
        parts.append(p)
    # 3x4 contact sheet
    sheet = OUT / f"{ep.stem}_sheet.jpg"
    cmd = ["ffmpeg", "-y"]
    for p in parts:
        cmd += ["-i", str(p)]
    filt = "".join(f"[{i}:v]scale=480:-1[t{i}];" for i in range(len(parts)))
    xstack = "".join(f"[t{i}]" for i in range(len(parts)))
    layout = "|".join([f"0_{i%4}_{i//4}" for i in range(len(parts))])
    cmd += ["-filter_complex", filt + f"{xstack}xstack=inputs={len(parts)}:layout={layout}:fill=black[out]",
            "-map", "[out]", str(sheet)]
    subprocess.run(cmd, capture_output=True)
    print(f"{ep.name}: {dur:.1f}s -> {sheet}")
