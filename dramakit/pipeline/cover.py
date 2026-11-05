"""Stage — cover: the picture of the drama.

The cover decides whether anybody clicks, and it is the one picture that
has to work on its own: a person, a world, a feeling, and room at the
bottom for the title.

The analysis has already said what the drama is about and who is in it,
so the cover can be made as soon as that is done - before a line of
dialogue exists.  The model is asked for the picture in words, the
picture is made by the same model that makes the shots, and the title is
put on afterwards: image models cannot write Chinese, and a title the
model invented is worse than no title.
"""
from __future__ import annotations

from ..media import ffmpeg as ff
from ..models import Status
from ..prompts import templates as T
from .base import Context
from . import frame as _frame


def _character_lines(ctx: Context) -> str:
    """The cast, as the cover wants to know them: who they are, what
    they look like."""
    out = []
    for c in (ctx.project.characters or [])[:6]:
        bits = [c.name]
        if c.role:
            bits.append(c.role)
        if c.gender and c.gender != "未知":
            bits.append(c.gender)
        if c.age:
            bits.append(c.age)
        line = "（".join(bits) + "）"
        if c.appearance:
            line += "：" + c.appearance[:60]
        out.append("  - " + line)
    return "\n".join(out) or "  （还没有角色，只画气氛）"


def run(ctx: Context) -> dict:
    """Make the cover of the drama."""
    proj = ctx.project
    ad = proj.art_direction
    title = (proj.meta.title or proj.meta.name or "").strip()
    if not title:
        ctx.log.warning("cover: 还没有剧名，跳过")
        return {"skipped": True}

    out = ctx.store.project_cover_path()
    if out.exists() and out.stat().st_size > 1024:
        ctx.log.info("cover: 已经有封面了，跳过")
        return {"skipped": True, "path": ctx.store.rel(out)}

    vis = ctx.providers.visual
    if vis is None:
        ctx.log.warning("cover: 没有出图服务，跳过")
        return {"skipped": True}

    # the synopsis is on the season - the analysis writes it there
    synopsis = ""
    for s in (proj.seasons or []):
        if s.synopsis:
            synopsis = s.synopsis
            break
    synopsis = synopsis or proj.meta.synopsis or ""

    frame = _frame.prompt_frame(ctx)
    llm = ctx.providers.llm_for("cover")
    user = T.render(
        T.COVER_USER, title=title, genre=ad.genre or "", era=ad.era or "",
        synopsis=synopsis or "（还没有剧情梗概）",
        style=ad.style_prompt_prefix or ad.style or "",
        color_palette=ad.color_palette or "",
        aspect=_frame.describe(ad), frame_size=frame.get("frame_size", ""),
        orientation=frame.get("aspect_orientation", ""),
        characters=_character_lines(ctx))
    try:
        data = llm.complete_json(T.COVER_SYSTEM, user)
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("cover: 封面提示词失败(%s)，用兜底", str(e)[:120])
        data = {}
    if isinstance(data, list):
        data = data[0] if data else {}
    prompt = (data.get("prompt") or "").strip()
    negative = (data.get("negative_prompt") or "").strip()
    if not prompt:
        prompt = (f"{ad.style_prompt_prefix or ad.style or 'cinematic photograph'}, "
                  f"{title}, a dramatic key visual, vertical composition, "
                  f"cinematic lighting, no text")
    negative = negative or ad.global_negative_prompt

    c = ctx.cfg.comfyui
    from .frame import project_frame, snap_size
    w, h = snap_size(*project_frame(ad, ctx.cfg))
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_name(out.stem + "_raw" + out.suffix)
    # the same seed rule the shots use: a fixed seed is a fixed cover
    seed = c.fixed_seed if c.seed_mode == "fixed" else -1
    try:
        from .visual import _extra, _render
        _render(ctx, "封面", "cover", lambda: vis.generate_image(
            prompt=prompt, negative=negative,
            width=w, height=h, seed=seed,
            steps=c.steps, cfg=c.cfg, out_path=str(raw), extra=_extra(ctx)))
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("cover: 出图失败(%s)", str(e)[:160])
        raw.unlink(missing_ok=True)
        return {"failed": True, "error": str(e)[:200]}

    # the title goes on afterwards: the model cannot write it, and a title
    # it made up is worse than no title at all
    try:
        ff.draw_title(raw, out, title, width=w, height=h)
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("cover: 烧剧名失败(%s)，用原图", str(e)[:120])
        raw.replace(out)
    raw.unlink(missing_ok=True)

    proj.meta.cover_path = ctx.store.rel(out)
    ctx.save()
    ctx.log.info("cover: 封面做好了 %s", out.name)
    return {"cover": ctx.store.rel(out), "title": title}
