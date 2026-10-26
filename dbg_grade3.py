import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import grade as gr

proj = Path(r"E:\dramakit\projects") / sys.argv[1]
tmp = proj / "tmp" / "ep_001"
clips = sorted(tmp.glob("shot_*.mp4"))
measured = [gr.analyze(c) for c in clips]
target = gr.median_stats(measured)
print(f"目标: luma={target.luma:.1f} sat={target.sat:.1f} tint={target.tint:+.1f} "
      f"contrast={target.contrast:.1f}")
for i, (c, m) in enumerate(zip(clips, measured)):
    f = gr.grade_filter(m, target, strength=0.85)
    if f:
        print(f"  {c.name}: luma {m.luma:6.1f} sat {m.sat:5.1f} "
              f"contrast {m.contrast:6.1f} tint {m.tint:+6.1f}")
        print(f"      {f}")
        if i > 3:
            break
