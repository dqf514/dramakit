"""Frames and words for a set of tutorial parts."""
import subprocess
import sys
from pathlib import Path

folder = Path(r"C:\tmp\bili3")
for src in sorted(folder.glob("p*.mp4")):
    name = src.stem
    frames = folder / f"{name}_frames"
    frames.mkdir(parents=True, exist_ok=True)
    for f in frames.glob("*.jpg"):
        f.unlink()
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(src)],
        capture_output=True, text=True).stdout.strip())
    t = 0.0
    while t < dur:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.1f}", "-i", str(src),
                        "-frames:v", "1", "-vf", "scale=900:-1",
                        str(frames / f"f{int(t):04d}.jpg")], capture_output=True)
        t += 10.0
    wav = folder / f"{name}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn",
                    "-ac", "1", "-ar", "16000", str(wav)], capture_output=True)
    txt = folder / f"{name}.txt"
    subprocess.run([r"E:\dramakit\venv\Scripts\python.exe",
                    r"E:\dramakit\rounds\tools\transcribe_chunks.py",
                    str(wav), str(txt), "25"], capture_output=True)
    print(f"{name}: {dur:.0f}s, {len(list(frames.glob('*.jpg')))} 帧, 转写 -> {txt}")
