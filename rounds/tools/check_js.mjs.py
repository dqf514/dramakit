"""Does the page's javascript still parse?

esprima is an ES5 parser, so the blocks that use the newer syntax come
back with an error that says nothing about the change.  Node is here
and node reads modern javascript, so node does the checking.

    node rounds/tools/check_js.mjs
"""
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(r"E:\dramakit")
HTML = REPO / "dramakit" / "web" / "static" / "index.html"

text = HTML.read_text(encoding="utf-8")
blocks = [b for b in re.findall(r"<script[^>]*>(.*?)</script>", text, re.S)
          if b.strip()]
print("  页面里有 %d 块脚本" % len(blocks))

tmp = REPO / "rounds" / "tools" / "_js_check_tmp"
tmp.mkdir(parents=True, exist_ok=True)
bad = 0
for i, b in enumerate(blocks):
    f = tmp / ("block%d.js" % i)
    f.write_text(b, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(f)],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode == 0:
        print("    块 %d ok" % i)
    else:
        bad += 1
        out = (r.stderr or "").strip().split("\n")
        print("    块 %d 报错：" % i)
        for line in out[:6]:
            print("      " + line)
print("  %d 块有问题" % bad if bad else "  全部通过")
sys.exit(1 if bad else 0)
