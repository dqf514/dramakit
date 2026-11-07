"""What the clip looks like through its ten seconds.

The clip is one take: one camera, from the first frame to the last.
So the face has to be the same face in every frame of it, and the
camera has to stay where it was.
"""
import pathlib
import subprocess
import sys

clip = pathlib.Path(sys.argv[1])
out = pathlib.Path(r"C:\Users\David\AppData\Local\Temp\opencode\frames")
out.mkdir(parents=True, exist_ok=True)
for f in out.glob("f*.png"):
    f.unlink()

probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1",
                        str(clip)], capture_output=True, text=True,
                       encoding="utf-8")
dur = float(probe.stdout.strip() or 0)
print("  时长 %.2f 秒" % dur)
for i in range(4):
    t = dur * i / 4.0
    p = out / ("f%d.png" % i)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % t, "-i",
                    str(clip), "-frames:v", "1", str(p)], capture_output=True)
    print("   %.2f 秒 → %s" % (t, p.name))
