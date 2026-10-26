import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

root = Path(r"E:\dramakit\projects\轮次01_01\tmp\ep_001")
for name in ("voice.mp3", "h3_bed.mp3", "music.mp3"):
    p = root / name
    if not p.exists():
        print(name, "不存在")
        continue
    vals = sorted(ff.momentary_lufs(p))
    n = len(vals)
    print(f"{name:12s} 样本 {n}  "
          f"p10={vals[n//10]:.1f} p50={vals[n//2]:.1f} p90={vals[n*9//10]:.1f} "
          f"max={vals[-1]:.1f}")
    top = vals[int(n * 0.6):]
    print(f"             _speech_level={top[len(top)//2]:.1f}  "
          f"_bed_peak={vals[int(n*0.9)]:.1f}")
