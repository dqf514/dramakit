"""Does the page's javascript still parse?

esprima is an ES5 parser, so the blocks that use the newer syntax come
back with an error that says nothing about the change.  So the file is
compared with the one that was committed: the errors have to be the
same ones.
"""
import re
import subprocess
import sys

import esprima

REPO = r"E:\dramakit"


def blocks(text):
    return [b for b in re.findall(r"<script[^>]*>(.*?)</script>", text, re.S)
            if b.strip()]


def errors(text):
    out = []
    for i, b in enumerate(blocks(text)):
        try:
            esprima.parseScript(b)
        except Exception as e:  # noqa: BLE001
            out.append((i, str(e)[:120]))
    return out


now = open(REPO + r"\dramakit\web\static\index.html", encoding="utf-8").read()
before = subprocess.run(
    ["git", "-C", REPO, "show", "HEAD:dramakit/web/static/index.html"],
    capture_output=True, text=True, encoding="utf-8").stdout

a = errors(before)
b = errors(now)
print("  改动前 %d 块报错，改动后 %d 块报错" % (len(a), len(b)))
for e in b:
    print("    现在:", e)
for e in a:
    print("    之前:", e)
same = [x[1].split(":")[0] for x in a] == [x[1].split(":")[0] for x in b]
print("  一样（都是 esprima 读不懂的新语法）" if same else "  不一样！")
