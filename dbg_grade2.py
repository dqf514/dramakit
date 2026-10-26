import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import grade as gr

proj = Path(r"E:\dramakit\projects") / sys.argv[1]
tmp = proj / "tmp" / "ep_001"
pre, post = [], []
for clip in sorted(tmp.glob("shot_*.mp4")):
    a = gr.analyze(clip).luma
    twin = tmp / clip.name.replace("shot_", "grade_")
    b = gr.analyze(twin).luma if twin.exists() else a
    pre.append(a)
    post.append(b)
    print(f"  {clip.name}: 前 {a:6.1f}  后 {b:6.1f}  {'(未调色)' if not twin.exists() else ''}")

print(f"\n前: 中位 {sorted(pre)[len(pre)//2]:.1f}  范围 {min(pre):.1f}~{max(pre):.1f}")
print(f"后: 中位 {sorted(post)[len(post)//2]:.1f}  范围 {min(post):.1f}~{max(post):.1f}")
print(f"亮度差 前 {max(pre)-min(pre):.1f}  后 {max(post)-min(post):.1f}")
