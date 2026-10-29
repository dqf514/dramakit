"""Is there any voice in this clip?"""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

video = Path(sys.argv[1])
wav = video.with_suffix(".wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn",
                "-ac", "1", "-ar", "16000", str(wav)], capture_output=True)
with wave.open(str(wav), "rb") as w:
    n = w.getnframes()
    data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
print(f"采样 {len(data)} ({len(data)/16000:.2f}s)  峰值 {np.abs(data).max():.4f}  "
      f"RMS {np.sqrt((data**2).mean()):.4f}")
# where is the energy?
win = 1600
for i in range(0, len(data) - win, win):
    seg = data[i:i + win]
    r = float(np.sqrt((seg ** 2).mean()))
    bar = "#" * int(r * 60)
    print(f"  {i/16000:5.2f}s rms={r:.4f} {bar}")
