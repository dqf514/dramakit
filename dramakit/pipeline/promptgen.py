"""Stage 6 — promptgen: build the image/video generation prompt for every shot.

Character appearance is injected verbatim so the same person looks consistent
across shots. Falls back to a deterministic template if the LLM call fails.
"""
from __future__ import annotations

from ..models import Shot, Status
from ..prompts import templates as T
from .base import Context


def _picked_characters(ctx: Context, shot: Shot) -> list:
    picked = []
    for name in shot.characters or []:
        c = ctx.project.character(name)
        if c and c not in picked:
            picked.append(c)
    if not picked:
        picked = list(ctx.project.characters[:3])
    return picked


def _char_visuals(ctx: Context, shot: Shot) -> str:
    picked = _picked_characters(ctx, shot)
    if not picked:
        return "（无固定角色，按剧情合理生成人物）"
    out = []
    for c in picked:
        anchor = c.anchor() or "（未设定外貌，按剧情合理生成）"
        out.append(f"- {c.name}（{c.role}）: {anchor}")
    return "\n".join(out)


def _char_negative(ctx: Context, shot: Shot) -> str:
    negs = [c.negative_prompt for c in _picked_characters(ctx, shot) if c.negative_prompt]
    return ", ".join(dict.fromkeys(negs))


def _flf_enabled(ctx: Context, shot: Shot) -> bool:
    if shot.flf is False:
        return False
    c = ctx.cfg.comfyui
    return bool(c.first_last_frame and c.flf_workflow and c.i2v_nodes.get("last_image"))


def _fallback_prompt(ctx: Context, shot: Shot, scene) -> str:
    ad = ctx.project.art_direction
    who = ", ".join(shot.characters) or "a person"
    style = ad.style_prompt_prefix or ad.style
    anchors = ", ".join(c.anchor() for c in _picked_characters(ctx, shot) if c.anchor())
    return (f"vertical composition 9:16, {anchors + ', ' if anchors else ''}"
            f"{shot.shot_type.value} shot, {who}, "
            f"{shot.action}, {scene.location}, {scene.time_of_day}, "
            f"{style}, cinematic lighting, highly detailed")


def run(ctx: Context) -> dict:
    cfg = ctx.cfg
    ad = ctx.project.art_direction
    llm = ctx.providers.llm_for("promptgen")
    count = 0
    for ep in ctx.target_episodes():
        if ctx.stage_done(ep, "promptgen"):
            continue
        for sc in ep.scenes:
            for shot in sc.shots:
                if shot.prompt:
                    continue
                visuals = _char_visuals(ctx, shot)
                flf = _flf_enabled(ctx, shot)
                user = T.render(T.PROMPT_USER, shot_type=shot.shot_type.value,
                                camera_move=shot.camera_move, action=shot.action,
                                character_anchors=visuals, location=sc.location or "场景",
                                time_of_day=sc.time_of_day,
                                style=ad.style_prompt_prefix or ad.style, era=ad.era,
                                color_palette=ad.color_palette, mood=sc.mood,
                                end_frame=flf)
                try:
                    data = llm.complete_json(T.PROMPT_SYSTEM, user)
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    shot.prompt = (data.get("prompt") or "").strip() or \
                        _fallback_prompt(ctx, shot, sc)
                    shot.negative_prompt = (data.get("negative_prompt") or "").strip()
                    if flf:
                        shot.end_prompt = (data.get("end_prompt") or "").strip()
                except Exception as e:  # noqa: BLE001
                    ctx.log.warning("promptgen: 镜 %s 失败(%s)，用模板兜底", shot.id, e)
                    shot.prompt = _fallback_prompt(ctx, shot, sc)
                    shot.negative_prompt = ""
                    if flf:
                        shot.end_prompt = shot.prompt
                # 角色专属负面词 + 全局负面词
                char_neg = _char_negative(ctx, shot)
                if char_neg:
                    shot.negative_prompt = (shot.negative_prompt + ", " + char_neg).strip(", ")
                if ad.global_negative_prompt:
                    shot.negative_prompt = (shot.negative_prompt + ", " +
                                            ad.global_negative_prompt).strip(", ")
                # seed strategy
                if shot.seed < 0 and cfg.comfyui.seed_mode == "fixed":
                    shot.seed = cfg.comfyui.fixed_seed
                count += 1
        ctx.mark(ep, "promptgen", Status.DONE)
        ctx.save()
    ctx.log.info("promptgen: 生成 %d 个镜头提示词", count)
    return {"prompts": count}
