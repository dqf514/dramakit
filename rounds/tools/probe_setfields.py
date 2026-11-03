"""Which field each setting is written to.

The pipeline writes by semantic name and field, so the mapping has to
agree with both: a name that points at the right node but the wrong field
leaves the setting at its default, which for a prompt means the model
gets the placeholder text and renders it.
"""
import re
from pathlib import Path

u = Path(r"E:\dramakit\dramakit\providers\comfyui.py").read_text(encoding="utf-8")
out = []

out.append("=== 所有 _set / _set_any 调用 ===")
for n, line in enumerate(u.split("\n"), 1):
    if re.search(r"self\._set(_any)?\(graph|self\._set(_any)?\(trial", line):
        out.append(f"  {n}: {line.strip()[:140]}")

out.append("")
out.append("=== generate_video 里 frames/fps/尺寸的处理 ===")
i = u.index("def generate_video")
seg = u[i:i + 4600].split("\n")
for n, line in enumerate(seg, 1):
    if any(k in line for k in ("frames", "fps", "width", "height", "length")):
        out.append(f"  {n}: {line.strip()[:140]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\setfields.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
