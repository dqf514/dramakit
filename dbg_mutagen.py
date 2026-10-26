"""mutagen vs ffprobe on the same files - which one is lying?"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff
from dramakit.providers.tts import probe_duration

for name in ("轮次01_01", "轮次02_02", "轮次03_03"):
    adir = Path(r"E:\dramakit\projects") / name / "audio"
    if not adir.exists():
        continue
    print(f"=== {name} ===")
    for f in sorted(adir.glob("*.mp3")):
        m = probe_duration(f)
        p = ff.probe_duration(f)
        flag = "  <-- 不一致" if abs(m - p) > 0.15 else ""
        print(f"  {f.name[:22]:24s} mutagen {m:6.2f}s   ffprobe {p:6.2f}s"
              f"   差 {m-p:+6.2f}{flag}")
