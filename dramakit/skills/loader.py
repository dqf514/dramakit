"""The skills: what the screenwriter and the director know.

The rules this pipeline writes with used to be in code, written by hand
and improved one round at a time.  They are now documents - the skills
that come with this repo - and the stages load them at run time.

A skill is a folder under `skills/` with a SKILL.md in it.  The stage asks
for the ones named in the config; a genre can ask for more.

What is in the library is the craft of making films by people.  The
library also holds what is different about making them by machine:
`short-drama-ai-film` - the beats, the one-take segment, the depth of
field, the first frame that has to hold the person in the shot.

Everything a skill says goes into the prompt as it is.  A SKILL.md is
written to be read by a model, which is exactly what it is being read by.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

log = logging.getLogger("dramakit.skills")

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"


def available() -> list[str]:
    if not SKILLS.exists():
        return []
    return sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists())


def _reference_files(folder: Path) -> list[Path]:
    """The documents that go with a skill.

    Two shapes are in use: a `references/` folder, and a `reference.md`
    beside the SKILL.md itself.  Both are read when the whole skill is
    asked for.
    """
    out: list[Path] = []
    refs = folder / "references"
    if refs.is_dir():
        out += sorted(refs.glob("*.md"))
    out += sorted(folder.glob("reference*.md"))
    return out


def load(name: str, *, refs: bool | list[str] = False) -> str:
    """The text of a skill: its SKILL.md, and its references when asked.

    `refs` is either False (the skill alone), True (every document that
    comes with it), or a list of the documents wanted by name.

    Returns an empty string when the skill is not there - a missing skill
    must not stop a run, it just means the stage writes with its own rules.
    """
    folder = SKILLS / name
    md = folder / "SKILL.md"
    if not md.exists():
        log.warning("skills: 找不到 %s（%s）", name, md)
        return ""
    parts = [md.read_text(encoding="utf-8", errors="replace")]
    if refs:
        wanted = None
        if isinstance(refs, (list, tuple, set)):
            wanted = {str(r).strip() for r in refs}
        for ref in _reference_files(folder):
            if wanted is not None and ref.name not in wanted:
                continue
            parts.append(f"\n\n<!-- {ref.name} -->\n"
                         + ref.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def load_refs(name: str, refs: list[str]) -> str:
    """Just the named documents of a skill, without its SKILL.md.

    A stage sometimes wants one document out of a skill without the
    skill's own rules - the adaptation craft, say, without the whole
    development process that goes with it.
    """
    folder = SKILLS / name
    if not folder.is_dir():
        return ""
    wanted = {str(r).strip() for r in refs or []}
    parts: list[str] = []
    for ref in _reference_files(folder):
        if ref.name not in wanted:
            continue
        parts.append(f"\n\n<!-- {ref.name} -->\n"
                     + ref.read_text(encoding="utf-8", errors="replace"))
    if not parts:
        log.warning("skills: %s 里没有这些参考文档：%s", name, ", ".join(sorted(wanted)))
    return "".join(parts)


GENRE_INDEX = SKILLS / "genre" / "题材索引.md"


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
    for line in text.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        genre, words = cells[0], cells[1]
        if not re.search(r"[\u4e00-\u9fff]", genre) or "/" not in words:
            continue
        out[genre] = [w.strip() for w in words.split("/") if w.strip()]
    return out


def _genre_choice(ctx) -> tuple[str, bool]:
    """What the person chose, and whether they chose at all.

    An empty list is an answer too: the person looked at the fifteen
    cards and left them all unticked, and that is not the same as
    never having been asked.
    """
    try:
        chosen = ctx.project.meta.skills or {}
    except Exception:  # noqa: BLE001
        return "", False
    if "genre" in chosen:
        for n in (chosen.get("genre") or []):
            if str(n).startswith("genre/"):
                return str(n), True
        return "", True
    # a card ticked inside a stage counts too
    for stage_sel in chosen.values():
        for n in (stage_sel or []):
            if str(n).startswith("genre/"):
                return str(n), True
    return "", False


def genre_for(ctx) -> str:
    """The one genre card that fits this project.

    A card the person ticked by hand comes first - they looked at the
    list and chose.  Otherwise the project's own genre and its synopsis
    are read for the words the cards answer to.  One card: the main
    genre.  A second one is a supplement, and a supplement that arrives
    with the main one is how the writing stops being about anything.
    """
    picked, decided = _genre_choice(ctx)
    if decided:
        return picked if picked and (SKILLS / picked / "SKILL.md").exists() else ""
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


def genre_rules(ctx, stage: str | None = None) -> str:
    """The genre card that fits this project, as text.

    `stage` is the stage that is asking: if that stage already loads
    the card by name - because the person ticked it - the card is not
    written in twice.
    """
    name = genre_for(ctx)
    if not name:
        return ""
    if stage:
        try:
            sel = ctx.project.meta.skills or {}
        except Exception:  # noqa: BLE001
            sel = {}
        if name in (sel.get(stage) or []):
            return ""
    return load(name)


def for_stage(ctx, stage: str, *, refs: bool | list[str] = False) -> str:
    """The skills a stage writes with, joined.

    The config names them per stage; a project can say its own: two
    dramas that share a genre word need not share their rules.

    `skills.refs` names the documents that go with the craft: a skill is
    a folder of knowledge and only its SKILL.md is the short version.
    The heavy part - how an adaptation is actually made, how the shots
    are covered - lives in the references.  Those documents belong to
    the stage, so they come whether or not the project ticked the skill
    they sit in: ticking one skill must not quietly take the rest of
    the stage's craft away.
    """
    cfg = getattr(ctx.cfg, "skills", None)
    # The project's own choice first: two dramas that share a genre word
    # need not share their rules, and a project that decided against a
    # skill for this stage means none - which is why the check is for a
    # key that exists rather than for a list that is full.
    project_sel = {}
    try:
        project_sel = ctx.project.meta.skills or {}
    except Exception:  # noqa: BLE001
        project_sel = {}
    # a project that chose its own skills for this stage has said what it
    # wants for the skill rules
    if stage in project_sel:
        names = list(project_sel.get(stage) or [])
    else:
        names = list(getattr(cfg, stage, None) or [])
    genre = ""
    try:
        genre = (ctx.project.art_direction.genre or "").strip()
    except Exception:  # noqa: BLE001
        pass
    if genre and getattr(cfg, "by_genre", None):
        for key, extra in (cfg.by_genre or {}).items():
            if key and key in genre and extra:
                names += list(extra)
    # the documents each of those skills brings with it
    wanted_refs: dict[str, list[str]] = {}
    try:
        wanted_refs = dict((getattr(cfg, "refs", None) or {}).get(stage) or {})
    except Exception:  # noqa: BLE001
        wanted_refs = {}
    seen: set[str] = set()
    out = []
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        ask = wanted_refs.get(n)
        text = load(n, refs=ask if ask else refs)
        if text:
            out.append(f"\n\n=== 规矩（来自 skill：{n}）===\n{text}")
    # The documents that belong to this stage's craft, whether or not the
    # project ticked the skill they live in.  A skill is the packaging;
    # the documents are the craft - the adaptation contract, how the
    # shots are covered, what a segment is.  Ticking one skill in the
    # panel must not quietly take the rest of the stage's craft away.
    for n, docs in wanted_refs.items():
        if n in seen:
            continue
        text = load_refs(n, docs)
        if text:
            out.append(f"\n\n=== 规矩（来自 skill：{n} 的参考文档）===\n{text}")
    if not out:
        log.info("skills: %s 阶段没有可用的 skill，用内置规矩", stage)
    return "".join(out)
