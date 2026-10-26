"""Re-grade a project's shot clips with the current filter and compare."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import grade as gr

proj = Path(r"E:\dramakit\projects") / sys.argv[1]
tmp = proj / "tmp" / "ep_001"
clips = sorted(tmp.glob("shot_*.mp4"))
measured = [gr.analyze(c) for c in clips]
target = gr.median_stats(measured)
print(f"目标 luma={target.luma:.1f} sat={target.sat:.1f}")

pre, post = [], []
for c, m in zip(clips, measured):
    f = gr.grade_filter(m, target, strength=0.85)
    dst = tmp / f"new_{c.name}"
    if not f:
        post.append(m.luma)
        pre.append(m.luma)
        continue
    gr.grade_shot(c, dst, target, strength=0.85, measured=m, crf=20, preset="medium", fps=30)
    a = gr.analyze(dst).luma
    pre.append(m.luma)
    post.append(a)
    print(f"  {c.name}: {m.luma:6.1f} -> {a:6.1f}   {f[:70]}")

print(f"\n亮度差 前 {max(pre)-min(pre):.1f}  后 {max(post)-min(post):.1f}")
