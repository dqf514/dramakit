"""Stage 6 — promptgen: build the image/video generation prompt for every shot.

Character appearance is injected verbatim so the same person looks consistent
across shots. Falls back to a deterministic template if the LLM call fails.
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..models import Shot, Status
from ..prompts import templates as T
from .base import Context, build_timeline

# MiniMax H3 I2VA alignment line (official wording, first frame at 0.00s)
H3_I2VA_ALIGN = ("For the target video, at 0.00 seconds into the target video, "
                  "<Picture 1> (from [Shot 1]) is fully referenced.")


def _dialogue_by_shot(ctx: Context, ep) -> dict[str, list[tuple[str, str, float]]]:
    """Map every shot id to the dialogue lines that fall inside it.

    Uses the same timeline the compose stage builds, so the lines we hand to H3
    are exactly the lines that will be spoken over that shot.
    """
    out: dict[str, list[tuple[str, str]]] = {}
    tl = ctx.timeline(ep)
    for tsc in tl.scenes:
        for ts in tsc.shots:
            out.setdefault(ts.shot.id, [])
        for tl_line in tsc.lines:
            # a voice over is a caption card, not something the actor says:
            # it must not end up in the dialogue tags
            if tl_line.line.kind.value == "narration":
                continue
            # The line belongs to the shot that is on screen when it is
            # said: the last one that has started.
            owner = None
            for ts in tsc.shots:
                if ts.start - 0.02 <= tl_line.start < ts.start + ts.duration:
                    owner = ts
            if owner is not None:
                out.setdefault(owner.shot.id, []).append(
                    (tl_line.line.speaker, tl_line.line.text,
                     float(tl_line.line.duration or 0.0)))
    return out


_QUOTE_CHARS = "\u201c\u201d\u2018\u2019\u300c\u300d\"'"
_QUOTED = re.compile(
    "[" + re.escape(_QUOTE_CHARS) + "]"
    "[^" + re.escape(_QUOTE_CHARS) + "]{0,80}"
    "[" + re.escape(_QUOTE_CHARS) + "]")


def _action_without_words(action: str) -> str:
    """The action, with the spoken words taken out.

    The storyboard writes what the character says inside quotes, and both
    picture models draw those quotes as captions on the picture. The
    performance is what the picture needs; the words come from the voice
    track later.
    """
    text = action or ""
    # "他反问：'想清楚退婚？'" -> "他反问"
    text = re.sub(r"[:：]\s*[" + re.escape(_QUOTE_CHARS) + "]"
                  "[^" + re.escape(_QUOTE_CHARS) + "]{0,80}"
                  "[" + re.escape(_QUOTE_CHARS) + "]", "，", text)
    text = _QUOTED.sub("", text)
    text = re.sub(r"[，,]\s*[，,]+", "，", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip("，,、 ")


def _speaker_note(shot: Shot, lines) -> str:
    """Say who speaks, and who must keep their mouth shut.

    The finished episodes were played back with the woman's voice over the
    man's close-up, and the model watching it said so: the lips and the
    speech belonged to different people. The prompt has to name the
    speaker and tell the others to listen with closed mouths.
    """
    speakers: list[str] = []
    for spk, _t, _d in lines or []:
        if spk and spk not in speakers:
            speakers.append(spk)
    others = [c for c in (shot.characters or []) if c not in speakers]
    if not speakers:
        if others:
            return ("本镜没有人说话：画面里的人只是在听、在反应，"
                    "**嘴要闭着，不要张嘴、不要出声**。")
        return ""
    who = "、".join(speakers)
    txt = (f"**本镜开口说话的只有：{who}**。{who} 的嘴型要跟后期配音轨对上"
           f"（mouth shapes synchronized with the post-dub track）。")
    if others:
        txt += (f"画面里的 {'、'.join(others)} 只是听和反应："
                f"**嘴要完全闭上、不许张开、不要露出牙齿、不要说话**"
                f"（keep their mouths fully closed, lips together, "
                f"listening silently），只给眼神和表情的反应。")
    return txt


def _numbered_dialogue(lines: list[tuple]) -> tuple[str, dict[str, str]]:
    """Render dialogue with stable (Sx) speaker ids; return text + id map."""
    ids: dict[str, str] = {}
    parts = []
    for speaker, text, _d in lines:
        if not (text or "").strip():
            continue
        if speaker not in ids:
            ids[speaker] = f"S{len(ids) + 1}"
        parts.append(f"({ids[speaker]}) <d>[zh-CN]{text}</d>")
    return ("\n".join(parts) if parts else "无", ids)


def _r2v_header(plan: list[tuple[str, str, str]]) -> str:
    """The six sections of the full-reference format, with the pictures named.

    `plan` is the picture list: (path, what it is, kind). The prompt has to
    say which picture carries the identity, which is the room and which is
    the frame the shot continues from - otherwise the model spreads the
    references over the whole description and the person drifts.
    """
    subject = ""
    keep = []
    first_char = ""
    room = ""
    frame = ""
    for i, (_path, role, kind) in enumerate(plan, 1):
        if kind == "character":
            if not first_char:
                first_char = str(i)
                subject += (f"<Picture {i}> is {role}; <Subject 1> is the person "
                            f"in <Picture {i}>, and keeps this face, this hair "
                            f"and this outfit in every single shot.\n")
            else:
                subject += f"<Picture {i}> is {role}.\n"
            keep.append(f"<Picture {i}> (the person): fully_preserved - "
                        f"the face, the hair and the clothes are kept exactly.")
        elif kind == "room":
            room = str(i)
            keep.append(f"<Picture {i}> (the room): fully_preserved - the "
                        f"furniture, the light and the layout are kept.")
        elif kind == "frame":
            frame = str(i)
            keep.append(f"<Picture {i}> (the frame this shot continues from): "
                        f"fully_preserved - the framing, the blocking, the "
                        f"clothes, the faces and the light are kept.")
        else:
            keep.append(f"<Picture {i}> (the prop): fully_preserved - the "
                        f"shape, the colour and the material are kept.")
    if not subject:
        subject = "<Subject 1> is the person in <Picture 1>.\n"
    anchor = frame or room or first_char or "1"
    if frame:
        # the frame is the picture the shot goes on from: the video has to
        # be that picture, moving
        how = (f"[reference generation + audio reference] The target video is "
               f"a single shot that continues <Picture {anchor}>: the same "
               f"framing, the same people, the same clothes and the same "
               f"light, in which <Subject 1> speaks, using the voice timbre "
               f"referenced from <Audio 1>. The person is the one in the "
               f"reference sheet, not somebody who looks like them.")
    else:
        how = (f"[reference generation + audio reference] The target video is a "
               f"single shot in the style and place of <Picture {anchor}>, in "
               f"which <Subject 1> speaks, using the voice timbre referenced "
               f"from <Audio 1>. The person is the one in the reference sheet, "
               f"not somebody who looks like them.")
    return ("subject_definitions:\n"
            f"{subject}"
            "<Audio 1> is the voice-timbre reference for <Subject 1> (S1), "
            "containing a spoken Mandarin vocal layer.\n\n"
            "summary:\n"
            f"{how}\n\n"
            "retention_analysis:\n"
            "<Subject 1> (appears in [Shot 1]): fully_preserved - the same "
            "person as in the reference sheet.\n"
            + "\n".join(keep) + "\n"
            "<Audio 1>: reference - the vocal timbre of <Audio 1> guides how "
            "<Subject 1> speaks, without copying the original signal.\n\n"
            "detailed_description:\n")


def _assemble_r2v_prompt(desc: str, soundscape: str, music: str,
                         plan: list[tuple[str, str, str]]) -> str:
    """The full-reference format, for the model that speaks."""
    return "\n".join([
        _r2v_header(plan),
        desc.strip(),
        "",
        f"overall_soundscape: {soundscape or 'N/A'}",
        "",
        f"non_diegetic_music: {music or 'N/A'}",
    ])


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
    desc = (f"[Shot 1] {style}, 9:16 vertical widescreen, {anchors + ', ' if anchors else ''}"
            f"{who}, {shot.action}, {location}, {sc.time_of_day}, "
            f"{shot.shot_type.value} shot with {shot.camera_move} camera movement, "
            f"cinematic lighting, highly detailed")
    if lines and ctx.cfg.compose.h3_audio != "bed":
        # the bed mode has no dialogue: H3 must not be asked to speak, or it
        # talks gibberish over the recorded voice
        dlg, _ = _numbered_dialogue(lines)
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
    """True when the configured video workflow uses the native MiniMax H3 nodes.

    The workflow file is read straight from disk: the provider may be a
    pool of machines now, and a pool has no workflow of its own.
    """
    rel = ctx.cfg.comfyui.i2v_workflow
    if not rel:
        return False
    roots: list[Path] = []
    vis = ctx.providers.visual
    for node in (getattr(vis, "nodes", None) or []):
        root = getattr(getattr(node, "client", None), "root", None)
        if root:
            roots.append(Path(root))
    roots.append(Path("."))
    for root in roots:
        p = Path(rel) if Path(rel).is_absolute() else root / rel
        if not p.exists():
            continue
        try:
            import json as _json
            wf = _json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        return any("MiniMaxH3" in str(n.get("class_type", "")) for n in wf.values())
    return False


def _aspect(ctx: Context) -> tuple[str, str]:
    """(aspect phrase, composition phrase) for the configured output size.

    The delivery format is the truth: the picture is made for the frame it
    is going to be shown in. Getting this wrong is how a vertical drama ends
    up with its faces cut off at the sides.
    """
    w = ctx.cfg.compose.width or 1280
    h = ctx.cfg.compose.height or 720
    if w >= h:
        return "横屏(16:9)镜头", "横屏构图 horizontal composition, 16:9"
    return "竖屏(9:16)镜头", "竖屏构图 vertical composition, 9:16"


def _gen_image_prompt(ctx: Context, llm, shot: Shot, sc, visuals: str,
                      flf: bool, location_visual: str,
                      continuity: str = "") -> None:
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
                    camera_move=shot.camera_move,
                    action=_action_without_words(shot.action),
                    character_anchors=visuals, location=sc.location or "场景",
                    location_visual=location_visual or "（按剧情合理生成）",
                    scene_summary=sc.summary or "", time_of_day=sc.time_of_day,
                    style=ad.style_prompt_prefix or ad.style, era=ad.era,
                    color_palette=ad.color_palette, mood=sc.mood, end_frame=flf,
                    aspect=aspect, composition=composition,
                    continuity=continuity)
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


# The rules that stop the drift, written at the end of the prompt where the
# official guide says they work best.
H3_CONSTRAINTS = (
    "保持人物身份、脸部、发型与服装和第一帧完全一致；"
    "画面里不出现除第一帧已有文字以外的新文字，也不加字幕和水印；"
    "不出现多余人物、多余肢体或畸形的手；"
    "镜头不抖动、不跳帧、不慢动作；"
    "不要切换到别的场景或别的机位；"
    # the face is what drifts: over a long take the model slowly changes
    # the bone structure, and the last frame is not the person any more
    "全片人脸的五官比例不变：脸不变长、不变窄、不变胖，"
    "眼睛和嘴的形状保持一致；"
    "人物动作幅度小，只做细微的表情、眼神和呼吸，"
    "不要大幅转身、走动或做剧烈动作；"
    "镜头运动平缓，不要突然加速或甩动。"
)


def _shot_seconds(shot) -> float:
    """How long the shot is, for the prompt's timeline."""
    try:
        return max(1.0, float(shot.duration or 3.0))
    except (TypeError, ValueError):
        return 3.0


def _reference_jobs(shot) -> str:
    """Say what each reference is for - and what it is not for."""
    n = len(shot.characters or [])
    if n:
        return (f"图片1 到 图片{n} 是人物定妆参考，锁定人物的脸、发型与服装；"
                f"图片{n+1} 以后是场景与光影参考，只用它的环境与光线，"
                "不要借用里面的服装、人物或文字。")
    return ("图片1 是场景与光影参考，只用它的环境与光线，"
            "不要借用里面的文字或人物。")


def _line_windows(shot, lines) -> list[tuple[float, float, str, str]]:
    """When each line is spoken inside the segment: (start, end, who, what).

    The lines follow the length of their own recording, not an even split:
    a gesture has to happen while its own sentence is being said.
    """
    dur = _shot_seconds(shot)
    out: list[tuple[float, float, str, str]] = []
    at = 0.0
    for spk, txt, d in (lines or [])[:4]:
        length = float(d) if d and d > 0 else 0.0
        if length <= 0:
            length = dur / max(1, len(lines))
        # the model speaks slower than the recording, so the line gets a
        # little more room than it needs, and it is told to finish in it
        window = length * 1.15 + 0.15
        out.append((round(at, 2), round(at + window, 2), spk, txt))
        at += window
    return out


def _bare(text: str) -> str:
    """The words of a line, without the punctuation and the spacing."""
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text or "")


def _said(desc: str, text: str) -> bool:
    """Is this line already in the description?"""
    if not text:
        return True
    if text in desc:
        return True
    return bool(_bare(text)) and _bare(text) in _bare(desc)


def _shot_timeline(shot, lines) -> str:
    """The beat by beat timeline, matching the length of the clip."""
    dur = _shot_seconds(shot)
    if not lines:
        return (f"0-{dur:.1f}秒：{shot.action[:40]}，角色不说话，"
                "只用表情、眼神和动作推进")
    out = []
    at = 0.0
    for spk, _txt, d in lines[:4]:
        length = float(d) if d and d > 0 else 0.0
        if length <= 0:
            length = dur / len(lines)
        # the model speaks slower than the recording, so the line gets a
        # little more room than it needs, and it is told to finish in it
        window = length * 1.15 + 0.15
        out.append(f"{at:.1f}-{at + window:.1f}秒：{spk} 开口说这句台词"
                   f"（**在这段时间里说完，不要拖到后面**）")
        at += window
    if at < dur - 0.05:
        out.append(f"{at:.1f}-{dur:.1f}秒：说完后保持情绪与姿态，"
                   f"给对方一点反应的时间")
    return "；".join(out)



def _gen_h3_prompt(ctx: Context, llm, shot: Shot, sc, visuals: str,
                   location_visual: str, lines: list[tuple[str, str]],
                   continuity: str = "") -> None:
    """Fill the official MiniMax H3 three-field prompt for one shot.

    Separate call on purpose: the image prompt and the H3 prompt are different
    schemas, asking for both at once degrades both.
    """
    ad = ctx.project.art_direction
    try:
        spk_note = _speaker_note(shot, lines)
        if ctx.cfg.comfyui.native_audio:
            # the model says the line itself: the words go in the prompt and
            # the voice comes from the reference recording
            dlg_text, _ids = _numbered_dialogue(lines)
            note = ("本镜的台词**由 H3 自己在这一镜里说出来**：台词原样用 "
                    "<d>[zh-CN]...</d> 包住，放在描述里角色说话的那一句后面。"
                    "声音参考 <Audio 1>：角色的音色、用词习惯和情绪照着它，"
                    "但不要把录音里的原话重复进 <d>。"
                    "说话的人要开口，嘴型跟声音对上；其他人闭嘴只听。"
                    "**画面里能看见的动作不要用画外音念出来**"
                    "（no narration, no voice over）：只有 <d> 里的那句是人话，"
                    "其余全是画面和声音，不要念动作、不要念环境。"
                    "overall_soundscape 写环境声和动作声，不要写人声。"
                    "**这一段里可以有好几个镜头**：用 [Shot 1]、[Shot 2] 写，"
                    "后面的镜头用 `At 00:0X.000, the camera cuts to ...` 标出切点；"
                    "每个镜头要有自己的景别和机位，不要整段一个景别。")
        elif ctx.cfg.compose.h3_audio == "bed":
            # The dialogue is recorded separately, so the shot only has to
            # show the performance - that is what gives the lip movement. The
            # clip's own sound is thrown away: the score comes from a separate
            # music-only clip, so H3's gibberish voice never reaches the mix.
            dlg_text = "无"
            note = ("本镜台词由后期配音轨提供，**不要写出台词内容，也不要写 <d> 标签**。"
                    "但要写清楚角色说话时的表演（开口、语气、情绪），用英文写，"
                    "例如 the man speaks to the woman with a stern, restrained tone。"
                    + (f"\n{spk_note}" if spk_note else "") +
                    "\noverall_soundscape 只写环境声与动作声（脚步、风、车辆、器物），"
                    "不要重复对白；non_diegetic_music 写配乐。")
        else:
            dlg_text, _ids = _numbered_dialogue(lines)
            note = ("台词必须原样用 <d>[zh-CN]...</d> 包住，不要改写。"
                    + (f"\n{spk_note}" if spk_note else ""))
        h3_user = T.render(
            T.H3_VIDEO_USER,
            shot_type=shot.shot_type.value, camera_move=shot.camera_move,
            action=_action_without_words(shot.action), character_anchors=visuals,
            location=sc.location or "场景",
            location_visual=location_visual or "（按剧情合理生成）",
            scene_summary=sc.summary or "", time_of_day=sc.time_of_day,
            style=ad.style_prompt_prefix or ad.style, era=ad.era,
            color_palette=ad.color_palette, mood=sc.mood,
            dialogue=dlg_text, dialogue_note=note, continuity=continuity,
            duration=_shot_seconds(shot),
            references=_reference_jobs(shot),
            timeline=_shot_timeline(shot, lines),
            constraints=H3_CONSTRAINTS)
        h3 = llm.complete_json(T.H3_VIDEO_SYSTEM, h3_user)
        if isinstance(h3, list):
            h3 = h3[0] if h3 else {}
        desc = str(h3.get("integrated_multimodal_description") or "").strip()
        soundscape = str(h3.get("overall_soundscape") or "").strip()
        music = str(h3.get("non_diegetic_music") or "").strip()
        # A line that is not in the prompt is a line nobody says.  The model
        # that writes the description drops one now and then, so the ones it
        # left out are written back in with the moment they belong to.
        if desc and ctx.cfg.comfyui.native_audio and lines:
            windows = _line_windows(shot, lines)
            add = []
            for (start, end, spk, txt) in windows:
                if _said(desc, txt):
                    continue
                add.append(f"From {start:.1f} to {end:.1f} seconds, {spk} opens "
                           f"their mouth and speaks, the lips moving with every "
                           f"syllable: <d>[zh-CN]{txt}</d>")
            if add:
                desc = desc.rstrip() + "\n" + "\n".join(add)
        if desc:
            if ctx.cfg.comfyui.native_audio:
                # the score has its own music-only clip; the shot clip
                # carries the voice and the room
                from .refs import picture_plan
                plan = picture_plan(ctx, shot, sc)
                shot.video_prompt = _assemble_r2v_prompt(
                    desc, soundscape or "N/A", "N/A", plan)
            else:
                shot.video_prompt = _assemble_h3_prompt(
                    desc, soundscape or "N/A", music or "N/A")
        else:
            shot.video_prompt = _fallback_h3_prompt(ctx, shot, sc, lines)
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("promptgen: 镜 %s H3提示词失败(%s)，用模板兜底",
                        shot.id, str(e)[:120])
        shot.video_prompt = _fallback_h3_prompt(ctx, shot, sc, lines)


def _gen_score_prompt(ctx: Context, llm, sc) -> None:
    """The prompt for the scene's music-only clip.

    The score has to come from somewhere that does not also speak: H3 would
    read the dialogue out loud in gibberish if it were asked for it, and that
    ends up under the recorded voice. So every scene gets one extra clip of
    the empty location, and its sound is the music bed.
    """
    ad = ctx.project.art_direction
    loc = next((l for l in ctx.project.locations if l.name == sc.location), None)
    location_visual = (loc.visual_prompt or loc.description) if loc else ""
    # the sounds of what happens in the scene: a short drama lives on its
    # sound - the door, the phone, the rain - not only on the music
    actions = []
    for shot in sc.shots:
        a = (shot.action or "").strip()
        if a and a not in actions:
            actions.append(a[:60])
        if len(actions) >= 3:
            break
    user = T.render(T.H3_SCORE_USER, location=sc.location or "场景",
                    time_of_day=sc.time_of_day,
                    location_visual=location_visual or "（按剧情合理生成）",
                    mood=sc.mood, scene_summary=sc.summary or "",
                    scene_actions="；".join(actions) or "（无特别动作）",
                    style=ad.style_prompt_prefix or ad.style)
    for attempt in range(3):
        try:
            data = llm.complete_json(T.H3_SCORE_SYSTEM, user)
            if isinstance(data, list):
                data = data[0] if data else {}
            desc = str(data.get("integrated_multimodal_description") or "").strip()
            soundscape = str(data.get("overall_soundscape") or "").strip()
            music = str(data.get("non_diegetic_music") or "").strip()
            if desc:
                sc.score_prompt = _assemble_h3_prompt(desc, soundscape or "N/A",
                                                      music or "N/A")
                return
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("promptgen: 场%d 配乐提示词失败(%s)，重试",
                            sc.index, str(e)[:120])
        time.sleep(2.0 * (attempt + 1))
    # the model will not answer: write the prompt from the scene itself, the
    # episode still gets its music
    sc.score_prompt = _assemble_h3_prompt(
        f"[Shot 1] An empty {sc.location} at {sc.time_of_day}, "
        f"{location_visual or 'an ordinary interior'}. The camera drifts "
        "slowly through the empty space. No people, no characters, no voices.",
        f"Ambient sound of {sc.location} at {sc.time_of_day}"
        + (f", with the sounds of {actions[0]}" if actions else ""),
        f"Emotional underscore for {sc.mood}: restrained, slow build.")
    ctx.log.warning("promptgen: 场%d 配乐提示词用兜底模板", sc.index)


def run(ctx: Context) -> dict:
    cfg = ctx.cfg
    ad = ctx.project.art_direction
    llm = ctx.providers.llm_for("promptgen")
    h3_needed = _h3_needed(ctx)
    count = 0
    # the two prompts of a shot are independent, and so are different shots:
    # the LLM round trips are the slowest part of this stage
    workers = max(1, int(ctx.cfg.llm.concurrency or 1))
    for ep in ctx.target_episodes():
        dlg_map = _dialogue_by_shot(ctx, ep)
        jobs = []
        for sc in ep.scenes:
            prev_action = ""
            for shot in sc.shots:
                # per shot, not per episode: a cleared or edited prompt has to
                # come back even when the stage is already marked done
                need_img = not shot.prompt
                need_h3 = h3_needed and not shot.video_prompt
                if not need_img and not need_h3:
                    prev_action = shot.action or prev_action
                    continue
                visuals = _char_visuals(ctx, shot)
                flf = _flf_enabled(ctx, shot)
                from .refs import find_location
                loc = find_location(ctx, sc.location)
                location_visual = (loc.visual_prompt or loc.description) if loc else ""
                # the shot before it decides where the people are standing:
                # without it the same conversation keeps re-posing itself
                continuity = prev_action[:180] if prev_action else ""
                jobs.append((shot, sc, visuals, flf, location_visual,
                            need_img, need_h3, continuity))
                prev_action = shot.action or prev_action

        def _one(job):
            shot, sc, visuals, flf, location_visual, need_img, need_h3, cont = job
            if need_img:
                _gen_image_prompt(ctx, llm, shot, sc, visuals, flf, location_visual,
                                  continuity=cont)
            if need_h3:
                _gen_h3_prompt(ctx, llm, shot, sc, visuals, location_visual,
                               dlg_map.get(shot.id, []), continuity=cont)

        if workers > 1 and len(jobs) > 1:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                list(ex.map(_one, jobs))
        else:
            for job in jobs:
                _one(job)
        count += len(jobs)
        # the music bed: one music-only clip per scene
        if h3_needed:
            for sc in ep.scenes:
                if sc.score_prompt:
                    continue
                _gen_score_prompt(ctx, llm, sc)
                count += 1
        ctx.mark(ep, "promptgen", Status.DONE)
        ctx.save()
    ctx.log.info("promptgen: 生成 %d 个镜头提示词", count)
    return {"prompts": count}
