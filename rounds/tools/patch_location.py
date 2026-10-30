"""Four fixes the first episode taught us.

1. The scene names and the asset names did not line up.  The script wrote
   '酒店宴会厅·主舞台' while the asset library holds '五星级酒店婚礼宴会厅',
   so the reference gate could not find the room, refused to spend a card on
   every single shot, and the episode turned into a slideshow of stills -
   with the stage still reporting "33 shots ok".  The room is now resolved by
   name instead of by literal equality.

2. A shot that has a picture but no video is a broken episode, not a note.
   Precheck says so now instead of letting the episode through.

3. The stage counted a picture as a shot.  The numbers now say how many
   pictures and how many videos came out.

4. The script is told which rooms exist, so the names line up in the first
   place.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")


def patch(path: str, pairs: list[tuple[str, str]]) -> None:
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s and old not in s:
            print(f"  {path}: 已经打过补丁了")
            continue
        assert old in s, f"{path}: 锚点没找到\n{old[:160]}"
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"  {path}: 改好了")


# --------------------------------------------------------------------------- #
# 1. the room resolver
# --------------------------------------------------------------------------- #
RESOLVER = '''
# --------------------------------------------------------------------------- #
# finding the room a scene happens in
# --------------------------------------------------------------------------- #
def _norm(s: str) -> str:
    """The name without the punctuation people add to the same room."""
    return re.sub(r"[\\s\\u3000·・\\-—_/\\\\（）()【】\\[\\]，,、。:：]+", "", (s or "")).lower()


def _base(s: str) -> str:
    """'酒店宴会厅·主舞台' -> '酒店宴会厅': the room, not the spot in it."""
    return re.split(r"[·・\\-|—/]", s or "", maxsplit=1)[0].strip()


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

'''

patch("dramakit/pipeline/refs.py", [
    ("""from __future__ import annotations

from pathlib import Path
""",
     """from __future__ import annotations

import re
from pathlib import Path
"""),
    ("""def picture_plan(ctx: Context, shot, sc, *, with_frame: bool = True""",
     RESOLVER + """
def picture_plan(ctx: Context, shot, sc, *, with_frame: bool = True"""),
    # picture_plan: use the resolver
    ("""    if sc is not None:
        for loc in ctx.project.locations:
            if loc.name != sc.location:
                continue
            for rel in (loc.ref_images or [])[:1]:
                p = ctx.store.abs(rel)
                if p.exists() and str(p) not in seen:
                    seen.add(str(p))
                    out.append((str(p), f"the room: {loc.name}", "room"))""",
     """    if sc is not None:
        loc = find_location(ctx, sc.location)
        if loc is not None:
            for rel in (loc.ref_images or [])[:1]:
                p = ctx.store.abs(rel)
                if p.exists() and str(p) not in seen:
                    seen.add(str(p))
                    out.append((str(p), f"the room: {loc.name}", "room"))"""),
    # missing_references: use the resolver
    ("""    if sc is not None:
        loc = next((l for l in ctx.project.locations
                    if l.name == sc.location), None)
        if loc is None:
            out.append(f"场景 {sc.location} 没有参考图")
        elif not any(ctx.store.abs(r).exists() for r in (loc.ref_images or [])):
            out.append(f"场景 {sc.location} 没有参考图")""",
     """    if sc is not None:
        loc = find_location(ctx, sc.location)
        if loc is None:
            out.append(f"场景 {sc.location} 没有找到对应的房间资产")
        elif not any(ctx.store.abs(r).exists() for r in (loc.ref_images or [])):
            out.append(f"场景 {sc.location}（房间资产 {loc.name}）没有参考图")"""),
])


# --------------------------------------------------------------------------- #
# 2. a picture without a video is an error, not a warning
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/precheck.py", [
    ("""def _check_episode(ctx: Context, ep: Episode, h3: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []""",
     """def _check_episode(ctx: Context, ep: Episode, h3: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    # when the pipeline is set to make video, a shot that only has a picture
    # is a slideshow waiting to be shipped - that is an error, not a note
    want_video = ctx.cfg.comfyui.mode in ("video", "image_then_video")"""),
    ("""            if shot.image_path and (not img or not img.exists()):
                errors.append(f"镜 {shot.id} 首帧图片缺失: {shot.image_path}")
                continue""",
     """            if shot.image_path and (not img or not img.exists()):
                errors.append(f"镜 {shot.id} 首帧图片缺失: {shot.image_path}")
                continue
            if want_video and not shot.video_path:
                errors.append(f"镜 {shot.id} 只有静帧没有视频"
                              f"（参考图不齐或视频没生成）")
                continue"""),
])


# --------------------------------------------------------------------------- #
# 3. the stage counts pictures and videos apart
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/visual.py", [
    ("""    def _run_phase(label: str, fn, total: int, offset: int,
                   workers: int = 0) -> int:
        nonlocal ok_count
        done = 0""",
     """    def _run_phase(label: str, fn, total: int, offset: int,
                   workers: int = 0) -> int:
        nonlocal ok_count, phase_ok
        done = 0"""),
    ("""                _sid, ok, _msg = fut.result()
                ok_count += int(ok)
                done = i""",
     """                _sid, ok, _msg = fut.result()
                ok_count += int(ok)
                phase_ok += int(ok)
                done = i"""),
    ("""    ok_count = 0
""",
     """    ok_count = 0
    phase_ok = 0
    images_ok = 0
    videos_ok = 0
"""),
    ("""        offset += _run_phase("出图", _gen_image, total, offset)
        ctx.save()""",
     """        offset += _run_phase("出图", _gen_image, total, offset)
        images_ok = phase_ok
        phase_ok = 0
        ctx.save()"""),
    ("""        offset += _run_phase("出视频", _gen_video, total, offset, workers=workers)
        ctx.save()""",
     """        offset += _run_phase("出视频", _gen_video, total, offset, workers=workers)
        videos_ok = phase_ok
        phase_ok = 0
        ctx.save()"""),
    ("""    return {"shots_ok": ok_count, "shots_total": len(jobs)}""",
     """    return {"shots_ok": videos_ok if do_video else images_ok,
            "shots_total": len(jobs),
            "images_ok": images_ok, "videos_ok": videos_ok,
            "failed": len(jobs) - (videos_ok if do_video else images_ok)}"""),
])


# --------------------------------------------------------------------------- #
# 4. the script is told which rooms exist
# --------------------------------------------------------------------------- #
patch("dramakit/prompts/templates.py", [
    ("""- 只使用这些已确定角色（不要凭空新增主要角色）：{{character_names}}""",
     """- 只使用这些已确定角色（不要凭空新增主要角色）：{{character_names}}
- **location 只能用下面这些已有的场景**（要再细分就在后面加"·子区域"，
  比如"五星级酒店婚礼宴会厅·主舞台"，但前半截必须一字不差）：
  {{location_names}}
  场景没有对应的参考图，这一集的镜头就生成不出来"""),
])

patch("dramakit/pipeline/script.py", [
    ("""    char_names = ", ".join(c.name for c in ctx.project.characters) or "（自行判断）\"""",
     """    char_names = ", ".join(c.name for c in ctx.project.characters) or "（自行判断）"
    loc_names = ", ".join(l.name for l in ctx.project.locations) or "（自行判断）\""""),
    ("""                        character_names=char_names, text=block[:12000],""",
     """                        character_names=char_names, location_names=loc_names,
                        text=block[:12000],"""),
])

print("补丁打完")
