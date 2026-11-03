"""Check every script the page loads, and find the one that will not parse.

The page came up blank with a syntax error, and the balance walk over the
block I added found nothing wrong - so the fault is somewhere else, or the
walk is being fooled by the markup inside a template literal. A real parser
is the answer: node checks a file without running it, and the browser
already told us which one it is.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HTML = Path(r"E:\dramakit\dramakit\web\static\index.html")
text = HTML.read_text(encoding="utf-8")

node = shutil.which("node")
out = []
out.append(f"node: {node}")

blocks = list(re.finditer(r"<script([^>]*)>(.*?)</script>", text, re.S))
out.append(f"script 标签 {len(blocks)} 个")

tmpdir = Path(tempfile.mkdtemp())
for i, m in enumerate(blocks):
    attrs = (m.group(1) or "").strip()
    code = m.group(2)
    out.append("")
    out.append(f"--- script #{i} attrs={attrs!r} 长度 {len(code)} ---")
    f = tmpdir / f"s{i}.js"
    f.write_text(code, encoding="utf-8")
    if not node:
        out.append("  没有 node，跳过")
        continue
    r = subprocess.run([node, "--check", str(f)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0:
        out.append("  ✓ 语法通过")
    else:
        err = (r.stderr or "").strip().split("\n")
        for line in err[:12]:
            out.append("  " + line)
        # show the offending line with context
        m2 = re.search(r":(\d+)\s*$", err[0]) if err else None
        if m2:
            ln = int(m2.group(1))
            lines = code.split("\n")
            for k in range(max(0, ln - 4), min(len(lines), ln + 3)):
                mark = ">>" if k == ln - 1 else "  "
                out.append(f"  {mark} {k+1}| {lines[k][:150]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\jscheck.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
