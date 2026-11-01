"""A short chapter is still a chapter: the filter must not lose the book.

_split drops bodies under 200 characters, which is meant to throw away a
line that only looked like a heading. But when every chapter is short - a
short story collection, a script, a book with terse chapters - the filter
empties the list, the catalog returns no chapters at all, and the whole
book vanishes with nothing said.

So the filter is a preference, not a verdict: if honouring it would leave
nothing, the chapters are kept as they are. Losing a book is worse than
keeping a chapter that turned out to be a heading.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\catalog.py")
s = p.read_text(encoding="utf-8", errors="replace")

old = """    out = []
    for n, (v, i, title) in enumerate(cuts):
        end = cuts[n + 1][1] if n + 1 < len(cuts) else len(lines)
        body = "\\n".join(lines[i:end]).strip()
        if len(body) < 200:
            continue
        out.append({"volume": v, "index": len(out) + 1, "title": title,
                    "body": body})
    return out"""

new = """    bodies = []
    for n, (v, i, title) in enumerate(cuts):
        end = cuts[n + 1][1] if n + 1 < len(cuts) else len(lines)
        bodies.append((v, title, "\\n".join(lines[i:end]).strip()))

    # A body under 200 characters is usually a line that merely looked like
    # a heading, so it is dropped. That is a preference, not a verdict: if
    # honouring it would leave nothing, the chapters are kept as they are.
    # A book that vanishes because every chapter was terse is a far worse
    # outcome than a stray heading that stayed in.
    long_enough = [(v, t, b) for v, t, b in bodies if len(b) >= 200]
    use = long_enough if long_enough else bodies

    return [{"volume": v, "index": n + 1, "title": t, "body": b}
            for n, (v, t, b) in enumerate(use) if b]"""

assert old in s, "_split 的过滤锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("catalog.py: 章节过滤只在滤完仍有内容时生效，不再丢掉整本书")
