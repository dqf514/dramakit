"""Why is the prompt stage drawing pictures?

promptgen should be writing prompt text - a model call per shot - yet six
character sheets have come out during it, each taking five to ten minutes.
Either the stage does image work it should not, or something it calls
does. This reads the stage and the code that makes a sheet, so the wait is
attributed to the right place.
"""
import re
from pathlib import Path

out = []

pg = Path(r"E:\dramakit\dramakit\pipeline\promptgen.py").read_text(encoding="utf-8")
out.append("=== promptgen.run 的调用 ===")
i = pg.find("def run(")
body = pg[i:i + 3000]
for n, line in enumerate(body.split("\n"), 1):
    if re.search(r"sheet|ref_sheet|generate|visual|comfy|image|refs\.", line):
        out.append(f"  {n}: {line.strip()[:140]}")
out.append("  --- run() 里的关键行 ---")
for n, line in enumerate(body.split("\n")[:40], 1):
    if re.search(r"for ep|for sc|for shot|llm\.|def ", line):
        out.append(f"  {n}: {line.strip()[:140]}")

out.append("")
out.append("=== 谁生成 sheet.jpg ===")
for f in Path(r"E:\dramakit\dramakit").rglob("*.py"):
    t = f.read_text(encoding="utf-8", errors="replace")
    if "sheet" in t and ("jpg" in t or "sheet.jpg" in t):
        for n, line in enumerate(t.split("\n"), 1):
            if "sheet" in line and ("jpg" in line or "sheet.jpg" in line or "ref_sheet" in line):
                out.append(f"  {f.name}:{n}  {line.strip()[:140]}")

out.append("")
out.append("=== promptgen 里的图片相关调用 ===")
for f in [Path(r"E:\dramakit\dramakit\pipeline\promptgen.py"),
          Path(r"E:\dramakit\dramakit\pipeline\refs.py")]:
    if not f.exists():
        continue
    t = f.read_text(encoding="utf-8")
    for n, line in enumerate(t.split("\n"), 1):
        if re.search(r"generate_image|vis\.|visual\.|sheet", line):
            out.append(f"  {f.name}:{n}  {line.strip()[:140]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\pg.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
