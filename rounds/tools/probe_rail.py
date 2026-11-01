"""How the console's rail and pages are built, so a new one matches."""
import re
from pathlib import Path

s = Path(r"E:\dramakit\dramakit\web\static\index.html").read_text(encoding="utf-8")
out = []

i = s.find('<nav id="rail">')
out.append("=== rail（前 1600 字）===")
out.append(s[i:i + 1600])

out.append("")
out.append("=== 所有 page section ===")
for m in re.finditer(r'<section id="page-\w+"[^>]*>', s):
    ln = s[:m.start()].count("\n") + 1
    out.append(f"  {ln}: {m.group(0)}")

out.append("")
out.append("=== railbtn 定义 ===")
for m in re.finditer(r'<button class="railbtn[^>]*>', s):
    out.append("  " + m.group(0))

out.append("")
out.append("=== switchPage 里的渲染分支 ===")
j = s.find("function switchPage")
out.append(s[j:j + 900])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\rail.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
