"""Is the dialogue actually audible over the music bed in the final mix?"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

root = Path(r"E:\dramakit\projects\测试短剧")
ep = root / "episodes" / "ep_001.mp4"

# the voice track and the bed, separately
tmp = root / "tmp" / "ep_001"
voice = tmp / "voice.mp3"
bed = tmp / "h3_bed.mp3"
mix = tmp / "mix.mp3"


def lufs(p):
    if not Path(p).exists():
        return None
    r = ff._run([ff.ffmpeg_bin(), "-i", str(p), "-af", "ebur128=peak=true",
                 "-f", "null", "-"], quiet=True)
    seg = r.stderr[r.stderr.rfind("Summary:"):]
    g = lambda pat: (re.search(pat, seg).group(1) if re.search(pat, seg) else None)
    return {"I": g(r"I:\s*(-?[\d.]+)\s*LUFS"), "PK": g(r"Peak:\s*(-?[\d.]+)\s*dBFS")}


print("对白轨 :", lufs(voice))
print("音乐垫底:", lufs(bed))
print("混音后 :", lufs(mix))

# in the final episode, how loud is the speech vs the gaps between lines?
print("\n=== 成片里逐秒的响度（看对白段和空隙段的差）===")
r = ff._run([ff.ffmpeg_bin(), "-i", str(ep), "-af",
             "ebur128=metadata=1:framelog=verbose", "-f", "null", "-"], quiet=True)
vals = [float(x) for x in re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", r.stderr)]
if vals:
    # the ebur128 per-frame log repeats the running value; take the max per second
    print(f"  采样 {len(vals)} 点  最低 {min(vals):.1f}  中位 {sorted(vals)[len(vals)//2]:.1f}  最高 {max(vals):.1f} LUFS")
    loud = [v for v in vals if v > -40]
    quiet = [v for v in vals if v <= -40]
    print(f"  有声段 {len(loud)} 点，中位 {sorted(loud)[len(loud)//2]:.1f} LUFS")
    print(f"  安静段 {len(quiet)} 点")
    if loud and quiet:
        gap = sorted(loud)[len(loud) // 2] - sorted(quiet)[len(quiet) // 2]
        print(f"  对白段 vs 安静段 差 {gap:.1f} LU  （>10 LU 说明音乐垫底没有盖住对白）")
