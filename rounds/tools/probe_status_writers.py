"""Who wrote the word "Status.DONE" instead of the value?

An episode's stage_status held the string "Status.DONE" - the repr of the
enum, not its value - so every check against Status.DONE read false and a
finished script would be written again. The writer is not obvious from
one field, so this finds every place a stage status is stored.
"""
import re
from pathlib import Path

out = []
for f in sorted(Path(r"E:\dramakit\dramakit").rglob("*.py")):
    t = f.read_text(encoding="utf-8", errors="replace")
    for n, l in enumerate(t.split("\n"), 1):
        if re.search(r"stage_status\[[^\]]+\]\s*=", l):
            out.append(f"{f.name}:{n}  {l.strip()[:120]}")
        elif re.search(r"\.status\s*=\s*(str\(|f[\"'])", l):
            out.append(f"{f.name}:{n}  [可疑] {l.strip()[:120]}")

out.append("")
out.append("=== 模型里的定义 ===")
from pathlib import Path as _P
m = _P(r"E:\dramakit\dramakit\models.py").read_text(encoding="utf-8")
i = m.find("stage_status")
out.append(m[i - 200:i + 200])

_P(r"C:\Users\David\AppData\Local\Temp\opencode\writers.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote", len(out), "行")
