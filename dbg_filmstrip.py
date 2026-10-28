"""A contact sheet of the finished episode - what the viewer actually sees."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")

name = sys.argv[1]
out = Path(sys.argv[2] if len(sys.argv) > 2 else
           r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\filmstrip.jpg")
video = Path(r"E:\\dramakit\\projects") / name / "episodes" / "ep_001.mp4"
if not video.exists():
    print(f"没有成片: {video}")
    raise SystemExit(1)

dur = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip())

cols, rows = 4, 3
n = cols * rows
step = dur / n
tmp = out.parent / f"strip_{name}"
tmp.mkdir(parents=True, exist_ok=True)
frames = []
for i in range(n):
    at = step * (i + 0.5)
    p = tmp / f"f{i:02d}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i",
                    str(video), "-frames:v", "1", "-vf", "scale=480:-1",
                    str(p)], capture_output=True)
    if p.exists():
        frames.append(p)
print(f"抽了 {len(frames)} 帧 → {out}")

# tile them
if frames:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1",
                    "-i", str(tmp / "f%02d.jpg"),
                    "-vf", f"tile={cols}x{rows}:margin=6:padding=6:color=0x202020",
                    "-frames:v", "1", str(out)], capture_output=True)
print(f"拼图: {out} ({out.stat().st_size if out.exists() else 0} 字节)")
