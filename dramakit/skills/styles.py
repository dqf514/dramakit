"""The styles, and the library they draw on.

The styles used to carry different documents of film theory: a
Republican-era drama got the Chinese series practice and the story
structure, a sweet romance got Ozu's staging.  It is all gone.  The
theory was about how films are made by people, and it was in every
prompt - and the model wrote like it was making one: long paragraphs
of stage direction, a lot of dialogue, and no pictures.

What the styles differ in is what they look like - the frame, the
palette, the era - and that is what the look itself says.  The writing
is the same craft for all of them, and the craft is the same for
everybody: the outline, the script, the storyboard.

So every look carries the same set, and the person can still take
anything off it and add anything back.
"""
from __future__ import annotations

# what every drama writes with, whatever it looks like
_CORE = {
    "analyze": ["novel-outline", "novel-characters", "novel-art"],
    "script": ["novel-script"],
    "storyboard": ["novel-storyboard", "novel-staging"],
    "promptgen": ["novel-storyboard"],
}

# the looks differ in how they look, not in how they are written, so
# there is nothing to add per group or per style
_BY_GROUP: dict[str, dict[str, list[str]]] = {}
_BY_STYLE: dict[str, dict[str, list[str]]] = {}


def _merge(*parts: dict) -> dict:
    out: dict[str, list[str]] = {}
    for part in parts:
        for stage, names in (part or {}).items():
            row = out.setdefault(stage, [])
            for n in names or []:
                if n not in row:
                    row.append(n)
    return out


def skills_for_style(style_id: str, group: str = "") -> dict:
    """The skills that go with a look, by stage."""
    return _merge(_CORE, _BY_GROUP.get(group or "", {}),
                  _BY_STYLE.get(style_id or "", {}))


def by_style() -> dict:
    """Every look and the skills that go with it.

    The console shows this when the look changes: the skills that fit it
    are offered, and the person can take anything off and add anything
    back.
    """
    from ..ai.looks import STYLES
    out: dict[str, dict] = {}
    for s in STYLES:
        out[s["id"]] = {
            "name": s.get("name", s["id"]),
            "group": s.get("group", ""),
            "skills": skills_for_style(s["id"], s.get("group", "")),
        }
    return out
