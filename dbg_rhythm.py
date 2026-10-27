"""Measure the rhythm of the finished episodes - the reference for each other."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.ref_rhythm import analyse

names = sys.argv[1:] or [f"轮次{n:02d}_{n:02d}" for n in range(1, 11)]
for name in names:
    ep = Path(r"E:\dramakit\projects") / name / "episodes" / "ep_001.mp4"
    if not ep.exists():
        print(f"{name}: 没有成片")
        continue
    p = analyse(ep)
    if not p.get("shots"):
        print(f"{name}: 分析失败")
        continue
    print(f"{name}: {p['duration']:5.1f}s  {p['shots']:3d} 镜  "
          f"平均 {p['avg_shot']:4.2f}s  中位 {p['median_shot']:4.2f}s  "
          f"最短 {p['min_shot']:4.2f}s  最长 {p['max_shot']:5.2f}s  "
          f"开场 {p['opening_shot']:4.2f}s  前3秒 {p['cuts_first_3s']} 刀  "
          f"{p['cuts_per_min']:5.1f} 刀/分")
