"""The genre cards are skills now, and one of them is picked for you.

The cards were there and they were dead: one folder deeper than the
loader reads, so no stage could load them.  They are skills now, named
for their genre, and the panel offers them by genre.

And when nobody has picked one by hand, the genre of the project picks
it: the card whose own words appear in the genre and the synopsis.  One
card - the main genre - because two cards in the same prompt is how
the writing stops being about anything.
"""
import pathlib

ROOT = pathlib.Path(r"E:\dramakit")


def edit(path, old, new, what):
    p = ROOT / path
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    assert old in text, "没找到：%s（%s）" % (what, path)
    text = text.replace(old, new, 1)
    if crlf:
        text = text.replace("\n", "\r\n")
    p.write_bytes(text.encode("utf-8"))


# --------------------------------------------------------------------------- #
# 1. the catalog: the genre family, and the genre's own name
# --------------------------------------------------------------------------- #
edit("dramakit/skills/catalog.py",
     """    "short-drama-develop": "开发",
    "screenwriting-theory": "编剧理论",
  }""",
     """    "short-drama-develop": "开发",
    "screenwriting-theory": "编剧理论",
    "genre": "类型",
  }""",
     "the genre family")

edit("dramakit/skills/catalog.py",
     """            "title_zh": TITLE_ZH.get(rel.as_posix(), ""),""",
     """            # the genre cards are named for their genre, in the
            # frontmatter, so the panel reads "豪门婚恋" and not
            # "genre"
            "title_zh": TITLE_ZH.get(rel.as_posix(), "")
                        or (fm.get("name") or "" if fam == "genre" else ""),""",
     "the genre's name")

# --------------------------------------------------------------------------- #
# 2. the loader: the card that fits
# --------------------------------------------------------------------------- #
edit("dramakit/skills/loader.py",
     """def for_stage(ctx, stage: str, *, refs: bool | list[str] = False) -> str:""",
     '''GENRE_INDEX = SKILLS / "genre" / "题材索引.md"


def genre_cards() -> dict[str, list[str]]:
    """The genres, and the words that mean them.

    The table is in the index - one place, so the card and the words
    that find it cannot drift apart.
    """
    out: dict[str, list[str]] = {}
    try:
        text = GENRE_INDEX.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.split("\\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        genre, words = cells[0], cells[1]
        if not re.search(r"[\\u4e00-\\u9fff]", genre) or "/" not in words:
            continue
        out[genre] = [w.strip() for w in words.split("/") if w.strip()]
    return out


def genre_for(ctx) -> str:
    """The one genre card that fits this project.

    The project's own genre and its synopsis are read for the words the
    cards answer to.  One card: the main genre.  A second one is a
    supplement, and a supplement that arrives with the main one is how
    the writing stops being about anything.
    """
    try:
        proj = ctx.project
        genre = (proj.art_direction.genre or "")
        synopsis = (proj.meta.synopsis or "")
    except Exception:  # noqa: BLE001
        return ""
    hay = "%s %s" % (genre, synopsis[:400])
    best = ""
    best_hits = 0
    for name, words in genre_cards().items():
        hits = sum(1 for w in words if w and w in hay)
        if hits > best_hits:
            best, best_hits = name, hits
    if not best:
        return ""
    path = "genre/" + best
    return path if (SKILLS / path / "SKILL.md").exists() else ""


def genre_rules(ctx) -> str:
    """The genre card that fits this project, as text."""
    name = genre_for(ctx)
    return load(name) if name else ""


def for_stage(ctx, stage: str, *, refs: bool | list[str] = False) -> str:''',
     "the genre picker")

edit("dramakit/skills/loader.py",
     """import logging
from pathlib import Path
from typing import Optional""",
     """import logging
import re
from pathlib import Path
from typing import Optional""",
     "the import")

# --------------------------------------------------------------------------- #
# 3. the stages that write with it
# --------------------------------------------------------------------------- #
edit("dramakit/pipeline/script.py",
     """    rules = SCREENWRITER_RULES + loader.for_stage(ctx, "script")""",
     """    rules = SCREENWRITER_RULES + loader.for_stage(ctx, "script")
    # the card for this project's genre: the craft of this kind of story,
    # and it is one card - the main genre
    rules += loader.genre_rules(ctx)""",
     "the script stage")

edit("dramakit/pipeline/analyze.py",
     """                    max_locations=10, max_props=8) + loader.for_stage(ctx, "analyze")""",
     """                    max_locations=10, max_props=8) + loader.for_stage(ctx, "analyze")
                    + loader.genre_rules(ctx)""",
     "the analyze stage")

print("类型卡接上了")
