"""The pictures a shot gets, and what each one is for.

Consistency is not a prompt word, it is a set of pictures that travels with
every job. The same person has to look the same in every shot of the
scene, and the same room has to look the same - so the video is given:

  1. one sheet per character on screen (front, profile and three-quarter
     view side by side, so the model sees the whole person, not one angle)
  2. the location's own picture, so the room does not change between shots
  3. the frame the shot is made from, so the composition is kept

The stills and the videos have to agree on the order, so the list is built
here and both ask for it.

And a video job is not started when the list is short: drawing a clip
without the references wastes the card and produces a face that has
nothing to do with the rest of the episode.
"""
from __future__ import annotations

from pathlib import Path

from .base import Context

# the slots the reference workflow exposes
MAX_PICTURES = 5


def _sheet(ctx: Context, name: str, paths: list[Path]) -> str:
    """One picture with the three views side by side.

    The official guide says a reference sheet can hold several panels and
    should get its own picture number - so the model is pointed at a panel
    rather than at three loose photographs.
    """
    from ..media import ffmpeg as ff
    if len(paths) == 1:
        return str(paths[0])
    out_dir = ctx.store.root / "characters" / name
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "sheet.jpg"
    if out.exists() and out.stat().st_mtime > max(p.stat().st_mtime for p in paths):
        return str(out)
    try:
        ff.contact_sheet(paths, out, width=1536)
        return str(out)
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("三视图合成失败(%s): %s", name, str(e)[:120])
        return str(paths[0])


def picture_plan(ctx: Context, shot, sc, *, with_frame: bool = True
                 ) -> list[tuple[str, str, str]]:
    """The pictures for one shot: (path, what it is, kind).

    Order matters: the character sheets come first (they carry the
    identity), then the location, then the frame the shot continues from.
    The frame is listed even before it exists, so the numbering the prompt
    uses is the numbering the video job uses.
    """
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    for name in shot.characters or []:
        c = ctx.project.character(name)
        if c is None:
            continue
        refs = []
        for rel in c.refs():
            p = ctx.store.abs(rel)
            if p.exists():
                refs.append(p)
        if not refs:
            continue
        sheet = _sheet(ctx, name, refs)
        if sheet in seen:
            continue
        seen.add(sheet)
        out.append((sheet,
                    f"the views of {name} "
                    f"(front, profile, three-quarter and back, left to right)",
                    "character"))

    if sc is not None:
        for loc in ctx.project.locations:
            if loc.name != sc.location:
                continue
            for rel in (loc.ref_images or [])[:1]:
                p = ctx.store.abs(rel)
                if p.exists() and str(p) not in seen:
                    seen.add(str(p))
                    out.append((str(p), f"the room: {loc.name}", "room"))

    if with_frame and shot.image_path:
        p = ctx.store.abs(shot.image_path)
        if str(p) not in seen:
            out.append((str(p), "the frame this shot continues from", "frame"))
    return out


def missing_references(ctx: Context, shot, sc) -> list[str]:
    """What is missing before a video for this shot makes sense."""
    out: list[str] = []
    if not shot.image_path or not ctx.store.abs(shot.image_path).exists():
        out.append("这一镜的首帧还没出")
    for name in shot.characters or []:
        c = ctx.project.character(name)
        if c is None:
            out.append(f"角色 {name} 没有定妆")
            continue
        refs = [ctx.store.abs(r) for r in c.refs()]
        if not any(p.exists() for p in refs):
            out.append(f"角色 {name} 没有三视图")
    if sc is not None:
        loc = next((l for l in ctx.project.locations
                    if l.name == sc.location), None)
        if loc is None:
            out.append(f"场景 {sc.location} 没有参考图")
        elif not any(ctx.store.abs(r).exists() for r in (loc.ref_images or [])):
            out.append(f"场景 {sc.location} 没有参考图")
    return out
