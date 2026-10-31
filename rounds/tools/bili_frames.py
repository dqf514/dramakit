"""Watch the tutorial: the frames on the screen and what is said over them."""
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\tmp\bili2\p1.mp4")
out = Path(r"C:\tmp\bili2")
frames = out / "frames"
frames.mkdir(parents=True, exist_ok=True)
for f in frames.glob("*.jpg"):
    f.unlink()

# one frame every 5 seconds
dur = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", str(src)],
    capture_output=True, text=True).stdout.strip())
step = 5.0
t = 0.0
while t < dur:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.1f}", "-i", str(src),
                    "-frames:v", "1", "-vf", "scale=768:-1",
                    str(frames / f"f{int(t):04d}.jpg")], capture_output=True)
    t += step
print(f"{dur:.0f} 秒，每 {step:.0f} 秒一帧，共 {len(list(frames.glob('*.jpg')))} 帧 -> {frames}")

# and the audio, for the words
wav = out / "p1.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn",
                "-ac", "1", "-ar", "16000", str(wav)], capture_output=True)
print("音频:", wav, wav.stat().st_size // 1024, "KB")
