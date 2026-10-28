import re
import subprocess
import sys
from pathlib import Path

p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"E:\dramakit\projects\轮次09_09\episodes\ep_001.mp4")
for th in ("0.25", "0.35", "0.45", "0.55"):
    vf = "select='gt(scene,%s)',showinfo" % th
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(p), "-vf", vf,
                        "-f", "null", "-"], capture_output=True, text=True,
                       errors="replace")
    ts = [float(m.group(1)) for m in re.finditer(r"pts_time:([\d.]+)", r.stderr)]
    print("阈值", th, "检出", len(ts), "个切点:", [round(x, 2) for x in ts][:14])
