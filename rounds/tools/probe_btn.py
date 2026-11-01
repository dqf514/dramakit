"""One full rail button, to copy its shape for a new one."""
import re
from pathlib import Path

s = Path(r"E:\dramakit\dramakit\web\static\index.html").read_text(encoding="utf-8")
out = []
for name in ("assets", "settings"):
    m = re.search(rf'<button class="railbtn" data-page="{name}".*?</button>', s, re.S)
    if m:
        out.append(f"=== {name} ===")
        out.append(m.group(0))
        out.append("")
# and one page section, to copy its wrapper
m = re.search(r'<section id="page-assets".*?</section>', s, re.S)
out.append("=== page-assets 的开头 ===")
out.append(m.group(0)[:400] if m else "?")
# where the assets render function starts
i = s.find("function renderAssetsPage")
out.append("")
out.append("=== renderAssetsPage 开头 ===")
out.append(s[i:i + 500])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\btn.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
