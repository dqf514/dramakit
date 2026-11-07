"""Which files have broken characters in them?

A file that was written by the wrong tool can come back with half a
character in it, and the text that goes into the prompt is that text.
The sign of it is the replacement character: utf-8 that does not decode
is shown as one, and Python's strict decode raises instead.
"""
import pathlib

ROOT = pathlib.Path(r"E:\dramakit")
SKIP = {".git", "venv", "node_modules", "__pycache__", ".pytest_cache"}
TEXT = {".py", ".md", ".yaml", ".yml", ".html", ".json", ".txt", ".ps1", ".js"}

bad = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    if any(s in p.parts for s in SKIP):
        continue
    if p.suffix.lower() not in TEXT:
        continue
    raw = p.read_bytes()
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as e:
        bad.append((p, "解码不过：%s" % e))
        continue
    text = raw.decode("utf-8")
    n = text.count("�")
    if n:
        # where
        first = text.find("�")
        line = text[:first].count("\n") + 1
        ctx = text[max(0, first - 30):first + 30].replace("\n", " ")
        bad.append((p, "%d 个坏字符，第一个在第 %d 行：…%s…" % (n, line, ctx)))

for p, why in bad:
    rel = p.relative_to(ROOT)
    print("  %-52s %s" % (str(rel), why))
print("  %d 个文件有坏字符" % len(bad) if bad else "  都干净")
