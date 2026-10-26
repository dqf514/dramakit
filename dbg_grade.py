import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff
from dramakit.media import grade as gr

proj = Path(r"E:\dramakit\projects\轮次03_03")
ep = proj / "episodes" / "ep_001.mp4"
d = ff.probe_duration(ep)
print("=== 成片帧 ===")
vals = []
for i in range(16):
    at = d * (i + 0.5) / 16
    p = Path(rf"C:\Users\David\AppData\Local\Temp\opencode\r3_{i}.png")
    ff.extract_frame(ep, p, at=at, width=480)
    st = gr.analyze(p)
    vals.append(st.luma)
    print(f"  t={at:5.1f}s luma={st.luma:6.1f} sat={st.sat:5.1f}")

print("=== 调色前的 shot 片段 (t=0.2) ===")
for clip in sorted((proj / "tmp" / "ep_001").glob("shot_*.mp4")):
    p = Path(r"C:\Users\David\AppData\Local\Temp\opencode\r3g.png")
    ff.extract_frame(clip, p, at=0.2, width=480)
    st = gr.analyze(p)
    print(f"  {clip.name} luma={st.luma:6.1f} sat={st.sat:5.1f}")
