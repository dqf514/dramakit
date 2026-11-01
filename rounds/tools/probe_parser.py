"""Can the command box say 'these chapters', and what will the run cost?

The user asked for the first ten chapters; the segment stage is cutting
every chapter. The action accepts episodes but not chapters, so the
request could not be expressed - and segment limits itself only by the
chosen chapters, which nobody chose. Two things to establish before
touching anything: whether the parser could even understand '前十章', and
what the run in flight will do next, since that is what decides whether
it needs stopping.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

out = []

# ---- could the parser have understood "chapters"? ---------------------
p = Path(r"E:\dramakit\dramakit\ai")
for f in sorted(p.glob("*.py")):
    t = f.read_text(encoding="utf-8", errors="replace")
    if "run_pipeline" in t and ("prompt" in t or "PARSE" in t or "SYSTEM" in t):
        out.append(f"=== {f.name} ===")
        for n, l in enumerate(t.split("\n"), 1):
            low = l.lower()
            if any(k in low for k in ("episode", "chapter", "集", "章", "stage", "阶段")):
                out.append(f"  {n}: {l.strip()[:140]}")
        out.append("")

# ---- does the parser even have a chapters field to fill? --------------
out.append("=== 动作参数白名单 ===")
a = Path(r"E:\dramakit\dramakit\ai\actions.py").read_text(encoding="utf-8")
m = a.find("ACTION_SPEC")
out.append(a[m:m + 1500])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\parser.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
