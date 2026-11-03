"""A filmstrip of one clip, so a problem in the motion can be seen.

A single frame says whether the picture is right. It does not say
whether the picture holds still, whether the light flickers, or whether
the face drifts - and those are what make a clip feel wrong rather than
merely different. So one clip is laid out as a strip of frames, evenly
spaced across its length, side by side.
"""
import json
import subprocess
import sys
from pathlib import Path

PROJ = Path(r"E:\dramakit\projects\星际骷髅兵")
OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\quality")
OUT.mkdir(parents=True, exist_ok=True)


def duration(vid: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=nb_frames",
                        "-of", "json", str(vid)], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        return float(d.get("format", {}).get("duration", 0))
    except Exception:  # noqa: BLE001
        return 0.0


def strip(vid: Path, n: int = 6) -> Path:
    """n frames, evenly spaced, in a row."""
    dur = duration(vid)
    dest = OUT / ("strip_" + vid.stem + ".jpg")
    # pick the frames by their number: evenly spaced across the clip
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v",
                        "-count_frames", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0",
                        str(vid)], capture_output=True, text=True)
    try:
        total = int((r.stdout or "0").strip().split("\n")[0])
    except Exception:  # noqa: BLE001
        total = 0
    if not total:
        total = int(dur * 24)
    picks = sorted({int(total * (i + 0.5) / n) for i in range(n)})
    expr = "+".join(f"eq(n\\,{p})" for p in picks)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(vid),
           "-vf", f"select='{expr}',scale=420:-1,tile={n}x1",
           "-frames:v", "1", str(dest)]
    subprocess.run(cmd, capture_output=True, timeout=180)
    print(f"  {vid.name}  {total} 帧  取帧 {picks}")
    print("   ->", dest, dest.exists())
    return dest


if __name__ == "__main__":
    for name in (sys.argv[1:] or ["shot_sh-0e55cce5.mp4", "shot_sh-ea3c284b.mp4"]):
        vid = PROJ / "video" / name
        if not vid.exists():
            hits = list((PROJ / "video").rglob(name))
            vid = hits[0] if hits else None
        if vid:
            strip(vid)
