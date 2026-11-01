"""A project is made one season at a time, and each season is a full run.

A long novel cannot be made in one pass: the render farm would run for
months and the result would be a single undifferentiated block with no
place to fix anything.  Real shows are made in seasons - a batch of
episodes, finished, reviewed, corrected, then the next batch made with
what was learned.  This file gives the project that shape.

A season owns the chapters it was made from and the episodes it produced,
and it carries its own copy of the character/prop *looks*.  That last part
is the point: a character can change across a long story - grow up, change
sides, be scarred, gain power - so the look is per-season, while the
person (name, voice, who they are) is carried across in the canon.  Looks
are locked by default so a rerun cannot silently drift a face; changing a
look is a deliberate act, not a side effect.

The canon is what makes season 2 continuous with season 1: a digest of
every character, how each look has evolved, and where the story left off.
analyze reads it, so the new season knows who these people were and what
has already happened, and can decide what has changed since.
"""
from __future__ import annotations

from typing import Optional

from .models import ArtDirection, Character, Season, Status


# the fields a character carries that are about *who they are*, not how
# they look this season.  These travel through the canon unchanged.
IDENTITY_FIELDS = ("name", "aliases", "role", "gender", "voice_id",
                   "voice_pitch", "voice_rate")

# the fields that describe how they look.  These are per-season.
LOOK_FIELDS = ("appearance", "visual_prompt", "outfit", "hair",
               "anchor_prompt", "negative_prompt", "consistency",
               "ref_images", "ref_sheet", "ref_image", "lora", "age",
               "personality", "locked")


def snapshot_look(c: Character) -> dict:
    """How a character looks, as it will be remembered between seasons."""
    return {k: getattr(c, k) for k in LOOK_FIELDS}


def apply_look(c: Character, look: dict) -> None:
    """Put a remembered look back onto a character."""
    for k in LOOK_FIELDS:
        if k in look:
            setattr(c, k, look[k])


def complete_season(season: Season, chapters: list[int],
                    done_chapters: list[int], synopsis: str = "",
                    canon: Optional["Canon"] = None) -> None:
    """Close a season off: what it was made from, and what it left behind.

    A season is a batch of chapters turned into finished episodes, and the
    next one has to start where this one stopped. So the season records the
    chapters it consumed, and the canon carries a digest of the story so
    far - that digest is what analyze reads to know who these people are
    and what has already happened to them, without being handed the whole
    book again.

    The canon is written here rather than by a stage inside the season.
    Segmentation is one step of many, and a season that stops early - at
    analysis, at the storyboard, wherever the user decides they have
    enough - still has to hand the next season a story to continue. The
    handover belongs to the closing of the season, not to a step in it.

    The chapters recorded are the ones that season actually turned into
    episodes, which is not always the ones it was seeded with: a run that
    found nothing new to cut still owns what it already had.
    """
    if chapters:
        season.chapters = sorted(set(season.chapters or []) | set(chapters))
    if done_chapters:
        season.done_chapters = sorted(set(season.done_chapters or [])
                                      | set(done_chapters))
    if synopsis:
        season.synopsis = synopsis
    season.status = Status.DONE
    if canon is None:
        return
    # how far the story has got, across every season closed so far
    canon.done_chapters = sorted(set(canon.done_chapters or [])
                                 | set(season.done_chapters or []))
    prior = [p for p in (canon.progress or "").split("；") if p]
    line = canon_progress([season])
    if line and line not in prior:
        canon.progress = "；".join(prior + [line])


def canon_progress(seasons: list[Season]) -> str:
    """One line per season, oldest first: where the story has got to.

    This is the digest analyze reads. It is deliberately short - a season
    is summarised by the chapters it covered and what it was about, not by
    the episodes it produced, because the episodes are the thing being
    made and the story is the thing being continued.
    """
    lines = []
    for s in sorted(seasons, key=lambda x: x.index):
        if s.status != Status.DONE:
            continue
        ch = sorted(set(s.chapters or []))
        span = f"第{ch[0]}~{ch[-1]}章" if len(ch) > 1 else (f"第{ch[0]}章" if ch else "")
        bits = [b for b in (span, s.synopsis) if b]
        if bits:
            lines.append(f"第{s.index}季（{'，'.join(bits)}）")
    return "；".join(lines)


def character_digest(chars: list[Character]) -> str:
    """A short, readable account of the cast, for analyze to read.

    This is what lets season 2 know that余飞 was already a tree by the end
    of season 1, without handing the model the whole book again.
    """
    if not chars:
        return ""
    out = []
    for c in chars:
        line = f"- {c.name}"
        if c.role:
            line += f"（{c.role}）"
        if c.appearance:
            line += f"：{c.appearance}"
        if c.personality:
            line += f"；性格{c.personality}"
        out.append(line)
    return "\n".join(out)


def record_season_looks(canon: "Canon", season_index: int,
                        chars: list[Character]) -> None:
    """Write this season's cast into the canon, so the next season inherits.

    Identity and voice are stored once and never touched again - that is
    what makes 余飞 the same person in season 3 as he was in season 1. The
    look is appended, one entry per season that used the character, so the
    evolution is legible rather than lost: season 2 can see that he was a
    scholar and is now a tree, and can decide what the story has done to
    him since. A character absent this season keeps their history; their
    look is simply not extended.
    """
    for c in chars:
        canon.characters.setdefault(c.name, {
            "role": c.role, "gender": c.gender, "personality": c.personality,
        })
        # a role corrected by a later season is the story's to correct
        if c.role:
            canon.characters[c.name]["role"] = c.role
        if c.voice_id:
            canon.voices.setdefault(c.name, c.voice_id)
        looks = canon.character_looks.setdefault(c.name, [])
        # pad with the last known look so the list indexes by season
        while len(looks) < season_index - 1:
            looks.append(dict(looks[-1]) if looks else {})
        snap = snapshot_look(c)
        if len(looks) == season_index - 1:
            looks.append(snap)
        else:
            looks[season_index - 1] = snap
