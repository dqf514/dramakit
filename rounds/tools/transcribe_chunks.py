"""Transcribe a long audio, chunk by chunk, so nothing is cut off."""
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1])
out = Path(sys.argv[2] if len(sys.argv) > 2 else src.with_suffix(".txt"))
chunk = float(sys.argv[3]) if len(sys.argv) > 3 else 25.0
tmp = src.parent / (src.stem + "_chunks")
tmp.mkdir(parents=True, exist_ok=True)
for f in tmp.glob("*.wav"):
    f.unlink()

dur = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", str(src)],
    capture_output=True, text=True).stdout.strip())

parts = []
t = 0.0
i = 0
while t < dur:
    f = tmp / f"c{i:03d}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(src),
                    "-t", f"{chunk}", "-ac", "1", "-ar", "16000", str(f)],
                   capture_output=True)
    r = subprocess.run([r"E:\ComfyUI\venv\Scripts\python.exe",
                        r"E:\dramakit\rounds\tools\transcribe3.py", str(f)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    txt = ""
    for ln in (r.stdout or "").splitlines():
        if ln.startswith("原样:"):
            txt = ln.split(":", 1)[1].strip()
    if txt:
        parts.append(f"[{int(t)//60:02d}:{int(t)%60:02d}] {txt}")
    t += chunk
    i += 1
out.write_text("\n".join(parts), encoding="utf-8")
print(f"{dur:.0f} 秒 → {len(parts)} 段 → {out}")
