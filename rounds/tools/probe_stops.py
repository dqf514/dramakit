"""The four things a submitted run cannot do.

Reads the pieces each fix touches: the job registry that has no way to be
stopped, the pipeline loop that never asks whether anyone still wants it,
the stages that cannot resume at a chosen episode, and the state left
lying after a crash.
"""
import re
from pathlib import Path

out = []

s = Path(r"E:\dramakit\dramakit\web\server.py").read_text(encoding="utf-8")
out.append("=== server.py: State 与 start_job ===")
i = s.find("class State")
out.append(s[i:i + 1900])

out.append("")
out.append("=== server.py: 路由里 /api/jobs ===")
for n, l in enumerate(s.split("\n"), 1):
    if "/api/jobs" in l:
        out.append(f"  {n}: {l.strip()[:120]}")

out.append("")
out.append("=== runner.py: 阶段循环 ===")
r = Path(r"E:\dramakit\dramakit\pipeline\runner.py").read_text(encoding="utf-8")
j = r.find("def run_pipeline")
out.append(r[j:j + 2000])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\pieces.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
