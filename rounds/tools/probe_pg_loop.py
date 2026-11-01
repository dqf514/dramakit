"""How many model calls does the prompt stage make, and how many at once?

The stage has run forty minutes and written nothing, so the only way to
say how much is left is to count the work and the rate. This reads the
stage's own loop: what one job asks for, and how many run together.
"""
from pathlib import Path

pg = Path(r"E:\dramakit\dramakit\pipeline\promptgen.py").read_text(encoding="utf-8")

out = []
i = pg.find("def run(")
j = pg.find("\ndef ", i + 10)
out.append("=== run() ===")
out.append(pg[i:j if j > 0 else i + 2200][:2200])

out.append("")
out.append("=== _one() 里调了几次模型 ===")
k = pg.find("def _one(")
if k > 0:
    m = pg.find("\ndef ", k + 10)
    body = pg[k:m if m > 0 else k + 1500]
    out.append(body[:1500])
    out.append("")
    out.append(f"  llm 调用次数: {body.count('llm.complete')}")

out.append("")
out.append("=== 并发怎么用的 ===")
for n, line in enumerate(pg.split("\n"), 1):
    if any(t in line for t in ("ThreadPool", "workers", "concurrency", "Pool")):
        out.append(f"  {n}: {line.strip()[:130]}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\pgloop.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
