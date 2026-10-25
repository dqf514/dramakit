"""Stage 6 — promptgen: build the image/video generation prompt for every shot.

Character appearance is injected verbatim so the same person looks consistent
across shots. Falls back to a deterministic template if the LLM call fails.
"""
from __future__ import annotations

from ..models import Shot, Status
from ..prompts import templates as T
from .base import Context, build_timeline

# MiniMax H3 I2VA alignment line (official wording, first frame at 0.00s)
H3_I2VA_ALIGN = ("For the target video, at 0.00 seconds into the target video, "
                  "<Picture 1> (from [Shot 1]) is fully referenced.")


def _dialogue_by_shot(ctx: Context, ep) -> dict[str, list[tuple[str, str]]]:
    """Map every shot id to the dialogue lines that fall inside it.

    Uses the same timeline the compose stage builds, so the lines we hand to H3
    are exactly the lines that will be spoken over that shot.
    """
    out: dict[str, list[tuple[str, str]]] = {}
    tl = build_timeline(ep)
    for tsc in tl.scenes:
        for ts in tsc.shots:
            out.setdefault(ts.shot.id, [])
        for tl_line in tsc.lines:
            for ts in tsc.shots:
                if ts.start <= tl_line.start < ts.start + ts.duration:
                    out.setdefault(ts.shot.id, []).append(
                        (tl_line.line.speaker, tl_line.line.text))
                    break
    return out


def _numbered_dialogue(lines: list[tuple[str, str]]) -> tuple[str, dict[str, str]]:
    """Render dialogue with stable (Sx) speaker ids; return text + id map."""
    ids: dict[str, str] = {}
    parts = []
    for speaker, text in lines:
        if not (text or "").strip():
            continue
        if speaker not in ids:
            ids[speaker] = f"S{len(ids) + 1}"
        parts.append(f"({ids[speaker]}) <d>[zh-CN]{text}</d>")
    return ("\n".join(parts) if parts else "无", ids)


def _assemble_h3_prompt(desc: str, soundscape: str, music: str) -> str:
    """Official H3 three-field prompt: alignment line + three core fields."""
    return "\n".join([
        H3_I2VA_ALIGN,
        "",
        f"integrated_multimodal_description: {desc}",
        "",
        f"overall_soundscape: {soundscape}",
        "",
        f"non_diegetic_music: {music}",
    ])


def _fallback_h3_prompt(ctx: Context, shot: Shot, sc, lines) -> str:
    """Deterministic H3 prompt when the LLM call fails."""
    ad = ctx.project.art_direction
    who = ", ".join(shot.characters) or "a person"
    anchors = ", ".join(c.anchor() for c in _picked_characters(ctx, shot) if c.anchor())
    loc = next((l for l in ctx.project.locations if l.name == sc.location), None)
    location = (loc.visual_prompt or loc.description) if loc else sc.location
    style = ad.style_prompt_prefix or ad.style
    desc = (f"[Shot 1] {style}, 16:9 widescreen, {anchors + ', ' if anchors else ''}"
            f"{who}, {shot.action}, {location}, {sc.time_of_day}, "
            f"{shot.shot_type.value} shot with {shot.camera_move} camera movement, "
            f"cinematic lighting, highly detailed")
    dlg, _ = _numbered_dialogue(lines)
    if lines:
        desc += f". {dlg}"
    return _assemble_h3_prompt(desc,
                               f"Ambient scene sound of {sc.location} at {sc.time_of_day}.",
                               "N/A")


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
    loc = next((l for l in ctx.project.locations if l.name == scene.location), None)
    location = (loc.visual_prompt or loc.description) if loc else scene.location
    return (f"vertical composition 9:16, {anchors + ', ' if anchors else ''}"
            f"{shot.shot_type.value} shot, {who}, "
            f"{shot.action}, {location}, {scene.time_of_day}, "
            f"{style}, cinematic lighting, highly detailed")


def _h3_needed(ctx: Context) -> bool:
    """True when the configured video workflow uses the native MiniMax H3 nodes."""
    try:
        wf = ctx.providers.visual._load_workflow(  # noqa: SLF001
            ctx.cfg.comfyui.i2v_workflow)
    except Exception:  # noqa: BLE001
        return False
    return any("MiniMaxH3" in str(n.get("class_type", "")) for n in wf.values())


def _episode_missing_h3(ctx: Context, ep, h3_needed: bool) -> bool:
    if not h3_needed:
        return False
    return any(not sh.video_prompt for sc in ep.scenes for sh in sc.shots)


def _aspect(ctx: Context) -> tuple[str, str]:
    """(aspect phrase, composition phrase) for the configured output size."""
    w = ctx.cfg.comfyui.width or 1280
    h = ctx.cfg.comfyui.height or 720
    if w >= h:
        return "横屏(16:9)镜头", "横屏构图 horizontal composition, 16:9"
    return "竖屏(9:16)镜头", "竖屏构图 vertical composition, 9:16"


def _gen_image_prompt(ctx: Context, llm, shot: Shot, sc, visuals: str,
                      flf: bool, location_visual: str) -> None:
    """Fill the still-image prompt for one shot.

    FLUX 3 and SDXL want completely different prompts, so the template is
    chosen by config: FLUX 3 needs one continuous scene caption, SDXL wants
    keyword structure.
    """
    ad = ctx.project.art_direction
    flux3 = ctx.cfg.comfyui.prompt_format == "flux3"
    system = T.FLUX3_IMAGE_SYSTEM if flux3 else T.PROMPT_SYSTEM
    template = T.FLUX3_IMAGE_USER if flux3 else T.PROMPT_USER
    aspect, composition = _aspect(ctx)
    user = T.render(template, shot_type=shot.shot_type.value,
                    camera_move=shot.camera_move, action=shot.action,
                    character_anchors=visuals, location=sc.location or "场景",
                    location_visual=location_visual or "（按剧情合理生成）",
                    scene_summary=sc.summary or "", time_of_day=sc.time_of_day,
                    style=ad.style_prompt_prefix or ad.style, era=ad.era,
                    color_palette=ad.color_palette, mood=sc.mood, end_frame=flf,
                    aspect=aspect, composition=composition)
    try:
        data = llm.complete_json(system, user)
        if isinstance(data, list):
            data = data[0] if not data else {}
        shot.prompt = (data.get("prompt") or "").strip() or _fallback_prompt(ctx, shot, sc)
        shot.negative_prompt = (data.get("negative_prompt") or "").strip()
        if flf:
            shot.end_prompt = (data.get("end_prompt") or "").strip()
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("promptgen: 镜 %s 失败(%s)，用模板兜底", shot.id, e)
        shot.prompt = _fallback_prompt(ctx, shot, sc)
        shot.negative_prompt = ""
        if flf:
            shot.end_prompt = shot.prompt
    if flux3:
        # FLUX 3 does not use negative prompts (cfg = 1, distilled)
        shot.negative_prompt = ""
        return
    char_neg = _char_negative(ctx, shot)
    if char_neg:
        shot.negative_prompt = (shot.negative_prompt + ", " + char_neg).strip(", ")
    if ad.global_negative_prompt:
        shot.negative_prompt = (shot.negative_prompt + ", " +
                                ad.global_negative_prompt).strip(", ")
    if shot.seed < 0 and ctx.cfg.comfyui.seed_mode == "fixed":
        shot.seed = ctx.cfg.comfyui.fixed_seed


def _gen_h3_prompt(ctx: Context, llm, shot: Shot, sc, visuals: str,
                   location_visual: str, lines: list[tuple[str, str]]) -> None:
    """Fill the official MiniMax H3 three-field prompt for one shot.

    Separate call on purpose: the image prompt and the H3 prompt are different
    schemas, asking for both at once degrades both.
    """
    ad = ctx.project.art_direction
    try:
        if ctx.cfg.compose.h3_audio == "bed":
            # H3 only renders the music/ambience bed; every spoken line comes
            # from the TTS track, so H3 must not voice anything
            dlg_text = "无"
            note = ("注意：本镜台词由后期配音轨提供，H3 不要生成任何人声。"
                    "请在描述里用英文写清角色说话的动作与情绪"
                    "（例如 he speaks with a stern, restrained tone），"
                    "但不要写出台词内容。")
        else:
            dlg_text, _ids = _numbered_dialogue(lines)
            note = "台词必须原样用 <d>[zh-CN]...</d> 包住，不要改写。"
        h3_user = T.render(
            T.H3_VIDEO_USER,
            shot_type=shot.shot_type.value, camera_move=shot.camera_move,
            action=shot.action, character_anchors=visuals,
            location=sc.location or "场景",
            location_visual=location_visual or "（按剧情合理生成）",
            scene_summary=sc.summary or "", time_of_day=sc.time_of_day,
            style=ad.style_prompt_prefix or ad.style, era=ad.era,
            color_palette=ad.color_palette, mood=sc.mood,
            dialogue=dlg_text, dialogue_note=note)
        h3 = llm.complete_json(T.H3_VIDEO_SYSTEM, h3_user)
        if isinstance(h3, list):
            h3 = h3[0] if h3 else {}
        desc = str(h3.get("integrated_multimodal_description") or "").strip()
        soundscape = str(h3.get("overall_soundscape") or "").strip()
        music = str(h3.get("non_diegetic_music") or "").strip()
        shot.video_prompt = (_assemble_h3_prompt(desc, soundscape or "N/A", music or "N/A")
                             if desc else _fallback_h3_prompt(ctx, shot, sc, lines))
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("promptgen: 镜 %s H3提示词失败(%s)，用模板兜底",
                        shot.id, str(e)[:120])
        shot.video_prompt = _fallback_h3_prompt(ctx, shot, sc, lines)


def run(ctx: Context) -> dict:
    cfg = ctx.cfg
    ad = ctx.project.art_direction
    llm = ctx.providers.llm_for("promptgen")
    h3_needed = _h3_needed(ctx)
    count = 0
    for ep in ctx.target_episodes():
        if ctx.stage_done(ep, "promptgen") and not _episode_missing_h3(ctx, ep, h3_needed):
            continue
        dlg_map = _dialogue_by_shot(ctx, ep)
        for sc in ep.scenes:
            for shot in sc.shots:
                need_img = not shot.prompt
                need_h3 = h3_needed and not shot.video_prompt
                if not need_img and not need_h3:
                    continue
                visuals = _char_visuals(ctx, shot)
                flf = _flf_enabled(ctx, shot)
                loc = next((l for l in ctx.project.locations
                            if l.name == sc.location), None)
                location_visual = (loc.visual_prompt or loc.description) if loc else ""
                if need_img:
                    _gen_image_prompt(ctx, llm, shot, sc, visuals, flf, location_visual)
                if need_h3:
                    _gen_h3_prompt(ctx, llm, shot, sc, visuals, location_visual,
                                   dlg_map.get(shot.id, []))
                count += 1
        ctx.mark(ep, "promptgen", Status.DONE)
        ctx.save()
    ctx.log.info("promptgen: 生成 %d 个镜头提示词", count)
    return {"prompts": count}
