"""Look at the segments that are done: first frame against last frame."""
import subprocess
import sys
from pathlib import Path

root = Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
vids = sorted((root / "video").glob("*.mp4"), key=lambda p: p.stat().st_mtime)
if len(sys.argv) > 1:
    vids = vids[-int(sys.argv[1]):]
tmp = Path(r"C:\\tmp")
for p in vids:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.3", "-i", str(p),
                    "-frames:v", "1", "-vf", "scale=300:-1",
                    str(tmp / f"chk_{p.stem}_a.png")], capture_output=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.4", "-i", str(p),
                    "-frames:v", "1", "-vf", "scale=300:-1",
                    str(tmp / f"chk_{p.stem}_b.png")], capture_output=True)
    a = tmp / f"chk_{p.stem}_a.png"
    b = tmp / f"chk_{p.stem}_b.png"
    pair = tmp / f"chk_{p.stem}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a), "-i", str(b),
                    "-filter_complex", "[0:v][1:v]hstack=inputs=2", str(pair)],
                   capture_output=True)
    print(f"{p.name} -> {pair}")
