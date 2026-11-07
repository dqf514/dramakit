"""The descriptions say when to use each card.

The keyword table is the index's, and the index is the one place it
lives: a card that says "this one is for 甜宠 / 霸总 / 契约婚姻" can be
matched against a project's genre, and a person reading the panel can
see what it is for.
"""
import pathlib
import re

ROOT = pathlib.Path(r"E:\dramakit")
DST = ROOT / "skills" / "genre"
index = (DST / "题材索引.md").read_text(encoding="utf-8")

table = {}
for line in index.split("\n"):
    if not line.startswith("|"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 2:
        continue
    genre, words = cells[0], cells[1]
    if not re.search(r"[一-鿿]", genre):
        continue
    if "/" not in words:
        continue
    table[genre] = [w.strip() for w in words.split("/") if w.strip()]
print("  索引里读到 %d 个类型" % len(table))

for folder in sorted(p for p in DST.iterdir() if p.is_dir()):
    genre = folder.name
    words = table.get(genre, [])
    md = folder / "SKILL.md"
    text = md.read_text(encoding="utf-8")
    desc = ("%s 类型的改编手艺：这一类小说的压力从哪里来、人物怎么应对、"
            "观众每集拿到什么回报、这一集落在哪。适合题材写着「%s」的小说。"
            % (genre, "、".join(words[:8]) if words else genre))
    head, _, body = text.partition("\n---\n")
    head = re.sub(r"description: .*", "description: " + desc, head)
    md.write_text(head + "\n---\n" + body, encoding="utf-8")
    print("    %-8s %s" % (genre, "、".join(words[:6])))
