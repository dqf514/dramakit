"""Does the face detector find the face without the pose model?"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\musetalk")
import numpy as np

video = Path(sys.argv[1])
tmp = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\mtframes")
tmp.mkdir(parents=True, exist_ok=True)
for i in range(3):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{0.2 + i * 0.5:.2f}",
                    "-i", str(video), "-frames:v", "1", str(tmp / f"f{i}.png")],
                   capture_output=True)
imgs = sorted(tmp.glob("f*.png"))
print("帧:", [p.name for p in imgs])

from musetalk.utils.preprocessing import get_landmark_and_bbox, HAS_MMPOSE
print("mmpose:", HAS_MMPOSE)
coords, frames = get_landmark_and_bbox([str(p) for p in imgs])
print("框:", coords)
