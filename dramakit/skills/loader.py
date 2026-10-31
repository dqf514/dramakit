"""The skills: what the screenwriter and the director know.

The rules this pipeline writes with used to be in code, written by hand
and improved one round at a time.  They are now documents - the skills
that come with this repo (and the screenwriting theory beside it) - and
the stages load them at run time.

A skill is a folder under `skills/` with a SKILL.md in it.  The stage asks
for the ones named in the config; a genre can ask for more (a revenge
drama wants character conflict and a Chekhovian engine, a sweet romance
wants Ozu's staging).

Everything a skill says goes into the prompt as it is.  A SKILL.md is
written to be read by a model, which is exactly what it is being read by.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("dramakit.skills")

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"


def available() -> list[str]:
    if not SKILLS.exists():
        return []
    return sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists())


def load(name: str, *, refs: bool = False) -> str:
    """The text of a skill: its SKILL.md, and its references when asked.

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
        for ref in sorted((folder / "references").glob("*.md")):
            parts.append(f"\n\n<!-- {ref.name} -->\n"
                         + ref.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def for_stage(ctx, stage: str, *, refs: bool = False) -> str:
    """The skills a stage writes with, joined.

    The config names them per stage; a genre can add its own:
    `characters.genre` (or the project's art direction) picks the theory
    skills that suit the drama.
    """
    cfg = getattr(ctx.cfg, "skills", None)
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
    seen: set[str] = set()
    out = []
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        text = load(n, refs=refs)
        if text:
            out.append(f"\n\n=== 规矩（来自 skill：{n}）===\n{text}")
    if not out:
        log.info("skills: %s 阶段没有可用的 skill，用内置规矩", stage)
    return "".join(out)
