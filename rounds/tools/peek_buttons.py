"""What the buttons on the workbench say now.

There were four ways to start the work and one of them did not start
anything.  This lists what is left.
"""
import pathlib
import re

t = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html").read_text(
    encoding="utf-8")

for pat in ["跑完整流程", "开始运行", 'data-chap="season"', 'data-chap="script"',
            "run-all", "runGo", "chapScope", "开始新的一季",
            "只做所选章"]:
    print("  %-20s 出现 %d 次" % (pat, t.count(pat)))

print()
print("工作台上的按钮：")
for m in re.finditer(
        r'<button[^>]*(id="runGo"|data-act="[a-z-]+"|data-chap="[a-z]+")[^>]*>'
        r'([^<]{0,30})', t):
    line = m.group(0).strip()
    line = re.sub(r"\$\{mark\(\"(.)\"\)\}", r"\1", line)
    print("  ", re.sub(r"\s+", " ", line)[:100])
