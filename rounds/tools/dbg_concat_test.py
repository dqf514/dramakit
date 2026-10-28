"""Which way of joining the clips keeps the length?"""
import subprocess
import sys
from pathlib import Path

d = Path(r"E:\dramakit\projects\轮次09_09\tmp\ep_001")
clips = sorted(d.glob("grade_*.mp4"))
out = Path(r"C:\Users\David\AppData\Local\Temp\opencode\cat2.mp4")


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


total = sum(dur(c) for c in clips)
print(f"{len(clips)} 段，合计 {total:.2f}s")

# the filter way
args = ["ffmpeg", "-v", "error", "-y"]
for c in clips:
    args += ["-i", str(c)]
fc = "".join(f"[{i}:v]" for i in range(len(clips)))
fc += f"concat=n={len(clips)}:v=1:a=0[v]"
args += ["-filter_complex", fc, "-map", "[v]", "-c:v", "libx264",
         "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", str(out)]
r = subprocess.run(args, capture_output=True, text=True)
print("滤镜拼接:", dur(out), r.stderr[:200])

# the demuxer way with the timestamps reset
lst = out.with_suffix(".txt")
lst.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips),
               encoding="utf-8")
out2 = out.with_name("cat3.mp4")
r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(out2)],
                   capture_output=True, text=True)
print("复用器拼接:", dur(out2), r.stderr[:200])
