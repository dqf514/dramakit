"""Transcribe a file and write the words to a text file (no shell in between)."""
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1])
out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".txt")
r = subprocess.run([r"E:\ComfyUI\venv\Scripts\python.exe",
                    r"E:\dramakit\rounds\tools\transcribe3.py", str(src)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [ln for ln in (r.stdout or "").splitlines()
         if "原样" in ln or "人声" in ln]
out.write_text("\n".join(lines), encoding="utf-8")
print(out)
