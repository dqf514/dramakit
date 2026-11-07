"""The genre cards become skills, so a person can pick one.

The cards were there and they were dead: `genre-cards/<题材>.md` sat one
folder deeper than the loader reads, so no stage could ever load them
and the model's idea of a 豪门婚恋 was whatever it had in it.

A skill is a folder under `skills/` with a SKILL.md in it, and the
folder is the name.  So each card becomes one skill, named for its
genre, and the panel offers them by genre instead of hiding fifteen
documents inside somebody else's reference folder.

The index stays as the index - it is the table of which genre is
which, and the loader reads that table to pick the one card that fits
the project when nobody has picked one by hand.
"""
import pathlib
import re
import shutil

ROOT = pathlib.Path(r"E:\dramakit")
SRC = ROOT / "skills" / "short-drama-develop" / "references" / "genre-cards"
DST = ROOT / "skills" / "genre"

# the aliases from the index, so the frontmatter can say when to use it
index = (ROOT / "skills" / "short-drama-develop" / "references" / "genre-cards.md").read_text(
    encoding="utf-8")
table = {}
for line in index.split("\n"):
    m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
    if not m:
        continue
    genre, words = m.group(1), m.group(2)
    if genre in ("题材", "---") or "/" not in genre:
        continue
    if not re.search(r"[一-鿿]", genre):
        continue
    table[genre] = [w.strip() for w in words.split("/") if w.strip()]
print("  从索引里读到 %d 个类型" % len(table))

DST.mkdir(parents=True, exist_ok=True)
for card in sorted(SRC.glob("*.md")):
    genre = card.stem
    body = card.read_text(encoding="utf-8")
    words = table.get(genre, [])
    desc = ("%s 类型的改编手艺：这一类小说的压力从哪里来、人物怎么应对、"
            "观众每集拿到什么回报、这一集落在哪。适合题材写着「%s」的小说。"
            % (genre, "、".join(words[:8])))
    text = ("---\nname: %s\ndescription: %s\nlicense: MIT\n---\n\n%s"
            % (genre, desc, body))
    folder = DST / genre
    folder.mkdir(exist_ok=True)
    (folder / "SKILL.md").write_text(text, encoding="utf-8")
    print("    %-8s -> skills/genre/%s/SKILL.md" % (genre, genre))

# the index moves with them
shutil.move(str(ROOT / "skills" / "short-drama-develop" / "references" / "genre-cards.md"),
            str(DST / "题材索引.md"))
# and the old folder goes
shutil.rmtree(str(SRC), ignore_errors=True)
print("  索引也搬过去了")
