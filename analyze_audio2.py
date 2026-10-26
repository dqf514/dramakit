"""Dig into the sound: voice vs bed levels, and how the TTS is built."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

root = Path(r"E:\dramakit\projects\测试短剧")


def stat(path, label):
    r = ff._run([ff.ffmpeg_bin(), "-i", str(path), "-af",
                 "ebur128=peak=true", "-f", "null", "-"], quiet=True)
    seg = r.stderr[r.stderr.rfind("Summary:"):]
    g = lambda p: (re.search(p, seg).group(1) if re.search(p, seg) else "?")
    print(f"  {label:34s} {g(r'I:\s*(-?[\d.]+)\s*LUFS'):>7s} LUFS  "
          f"峰值 {g(r'Peak:\s*(-?[\d.]+)\s*dBFS'):>6s} dBFS")


print("=== tmp 中间轨（如果还在）===")
tmp = root / "tmp"
for p in sorted(tmp.rglob("*")):
    if p.is_file() and p.suffix in (".mp3", ".mp4") and p.stat().st_size > 1000:
        print(f"  {p.relative_to(root)}  {p.stat().st_size/1024:.0f}KB")

print("\n=== 关键轨的电平 ===")
for name in ("voice.mp3", "music.mp3", "mix.mp3", "h3_bed.mp3"):
    hits = list(tmp.rglob(name))
    for p in hits[:1]:
        stat(p, p.name)

print("\n=== 成片里对白段的瞬时响度分布 ===")
ep = root / "episodes" / "ep_001.mp4"
r = ff._run([ff.ffmpeg_bin(), "-i", str(ep), "-af",
             "ebur128=metadata=1:framelog=verbose", "-f", "null", "-"], quiet=True)
vals = [float(x) for x in re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", r.stderr)]
if vals:
    vals_sorted = sorted(vals)
    n = len(vals_sorted)
    print(f"  逐帧响度 {n} 个样本：最低 {vals_sorted[0]:.1f} / 10% {vals_sorted[n//10]:.1f} "
          f"/ 中位 {vals_sorted[n//2]:.1f} / 90% {vals_sorted[n*9//10]:.1f} / 最高 {vals_sorted[-1]:.1f}")
    print(f"  动态范围（最高-最低）= {vals_sorted[-1]-vals_sorted[0]:.1f} LU")
