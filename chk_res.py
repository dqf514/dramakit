import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

root = Path(r"E:\dramakit\projects\测试短剧")
for p in sorted((root / "video").glob("*.mp4"))[:4]:
    s = ff.probe_streams(p)
    v = s.get("video") or {}
    a = s.get("audio") or {}
    print(f"{p.name}  {v.get('width')}x{v.get('height')}  "
          f"{v.get('avg_frame_rate')}  dur={v.get('duration')}  "
          f"audio={a.get('codec_name')} {a.get('sample_rate')}")

for p in sorted((root / "episodes").glob("*.mp4")):
    s = ff.probe_streams(p)
    v = s.get("video") or {}
    print(f"[成片] {p.name}  {v.get('width')}x{v.get('height')}  dur={v.get('duration')}")
