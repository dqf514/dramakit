import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

p = Path(r"E:\dramakit\projects\测试短剧\video\shot_sh-6db4be00.mp4")
st = ff.probe_streams(p)
v = st.get("video") or {}
a = st.get("audio") or {}
print(f"{v.get('width')}x{v.get('height')} {v.get('avg_frame_rate')} dur={v.get('duration')}")
print(f"音轨 {a.get('codec_name')} {a.get('sample_rate')} {a.get('channels')}ch dur={a.get('duration')}")
out = Path(r"C:\Users\David\AppData\Local\Temp\opencode\h3check.png")
ff.extract_frame(p, out, at=2.5)
print("抽帧 ->", out)
