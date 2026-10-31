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

import re
from pathlib import Path

from .base import Context

# the slots the reference workflow exposes
MAX_PICTURES = 5


def _sheet(ctx: Context, name: str, paths: list[Path]) -> str:
    """One picture with the views of the person side by side.

    A character is given to the video with two pictures: the face, and the
    views of the person arranged horizontally.  The face is on its own
    because the face is what has to stay the same, and a face shared with
    three full bodies is a small face.
    """
    from ..media import sheet
    if len(paths) == 1:
        return str(paths[0])
    out_dir = ctx.store.root / "characters" / name
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "sheet.jpg"
    if out.exists() and out.stat().st_mtime > max(p.stat().st_mtime for p in paths):
        return str(out)
    bodies = [p for p in paths if "face" not in p.name.lower()]
    try:
        sheet.contact_sheet(bodies or paths, out, width=1536)
        return str(out)
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("三视图合成失败(%s): %s", name, str(e)[:120])
        return str(paths[0])



# --------------------------------------------------------------------------- #
# finding the room a scene happens in
# --------------------------------------------------------------------------- #
def _norm(s: str) -> str:
    """The name without the punctuation people add to the same room."""
    return re.sub(r"[\s\u3000·・\-—_/\\（）()【】\[\]，,、。:：]+", "", (s or "")).lower()


def _base(s: str) -> str:
    """'酒店宴会厅·主舞台' -> '酒店宴会厅': the room, not the spot in it."""
    return re.split(r"[·・\-|—/]", s or "", maxsplit=1)[0].strip()


def _run(a: str, b: str) -> int:
    """The longest common run of characters ('宴会厅' inside two names)."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def find_location(ctx: Context, name: str):
    """Which room does this scene happen in?

    The script names the spots inside a room ('酒店宴会厅·主舞台') while the
    asset library holds the rooms ('五星级酒店婚礼宴会厅').  Taken literally
    the two never meet, the shot has no room reference, and the gate refuses
    to spend a card - so the name is resolved instead.
    """
    locs = list(ctx.project.locations or [])
    if not locs or not name:
        return None
    for loc in locs:
        if loc.name == name:
            return loc
    n = _norm(name)
    for loc in locs:
        if _norm(loc.name) == n:
            return loc
    base = _norm(_base(name))
    for loc in locs:
        ln = _norm(loc.name)
        if ln and base and (base in ln or ln in base):
            return loc
    # last resort: the closest room, if it is close enough
    best, best_score = None, 0.0
    for loc in locs:
        ln = _norm(loc.name)
        if not ln:
            continue
        score = _run(base or n, ln) / max(1, min(len(base or n), len(ln)))
        if score > best_score:
            best, best_score = loc, score
    if best is not None and best_score >= 0.6:
        ctx.log.info("refs: 场景 '%s' 对应到房间资产 '%s'", name, best.name)
        return best
    return None


def _previous_shot(ctx: Context, sc, shot):
    """The shot before this one in the scene, if there is one."""
    try:
        i = [x.id for x in sc.shots].index(shot.id)
        return sc.shots[i - 1] if i > 0 else None
    except ValueError:
        return None


def _face_picture(ctx: Context, name: str, refs: list[Path]) -> str | None:
    """The picture of the face filling the frame, if there is one."""
    for rel in ctx.project.character(name).refs():
        if "face" not in rel.lower():
            continue
        p = ctx.store.abs(rel)
        if p.exists():
            return str(p)
    return None


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

    # The frame comes first: it is the picture the shot continues from, and
    # the model takes the first picture as the one it follows.
    if with_frame:
        rel = shot.image_path or ctx.store.rel(ctx.store.image_path(shot.id))
        p = ctx.store.abs(rel)
        if str(p) not in seen:
            seen.add(str(p))
            out.append((str(p), "the frame this shot continues from", "frame"))
        # the handoff: where the shot before this one ended.  The slot is
        # reserved whether or not there is such a frame yet - the prompt is
        # written before the clip exists, and the numbers have to match.
        prev = _previous_shot(ctx, sc, shot)
        if prev is not None:
            prev_rel = prev.video_path or ctx.store.rel(
                ctx.store.video_path(prev.id))
            q = ctx.store.abs(prev_rel)
            if str(q) not in seen:
                seen.add(str(q))
                out.append((str(q),
                            "the last frame of the shot before this one: the "
                            "people and the props are exactly where that shot "
                            "left them",
                            "handoff"))

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
        # Two pictures per person: the face, then the views side by side.
        # The face is on its own because a face shared with three full
        # bodies is a small face, and the face is what has to stay the same.
        face = _face_picture(ctx, name, refs)
        if face is not None and face not in seen:
            seen.add(face)
            out.append((face,
                        f"the face of {name}, filling the frame - this is who "
                        f"{name} is, and it must not change",
                        "character"))
        views = _sheet(ctx, name, refs)
        if views not in seen:
            seen.add(views)
            out.append((views,
                        f"the views of {name} side by side: from the front, "
                        f"from the side, three-quarters and from behind - the "
                        f"same person as the face picture",
                        "character"))

    if sc is not None:
        loc = find_location(ctx, sc.location)
        if loc is not None:
            for rel in (loc.ref_images or [])[:1]:
                p = ctx.store.abs(rel)
                if p.exists() and str(p) not in seen:
                    seen.add(str(p))
                    out.append((str(p), f"the room: {loc.name}", "room"))

    # the props this shot shows: they are assets too
    for prop in (getattr(ctx.project, "props", None) or []):
        if not prop.ref_images:
            continue
        if prop.name not in (shot.action or "") and \
                prop.name not in " ".join(shot.characters or []):
            continue
        for rel in prop.ref_images[:1]:
            pp = ctx.store.abs(rel)
            if pp.exists() and str(pp) not in seen:
                seen.add(str(pp))
                out.append((str(pp), f"the prop: {prop.name}", "prop"))

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
        loc = find_location(ctx, sc.location)
        if loc is None:
            out.append(f"场景 {sc.location} 没有找到对应的房间资产")
        elif not any(ctx.store.abs(r).exists() for r in (loc.ref_images or [])):
            out.append(f"场景 {sc.location}（房间资产 {loc.name}）没有参考图")
    return out
