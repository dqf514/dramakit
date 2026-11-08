"""Stage 11.5 — precheck: validate assets and prompts before compose.

Compose is the last and most expensive step, so everything that could make it
produce a broken file is checked first:

  * every shot has a picture or a video, and that file exists on disk
  * shot videos decode and report a real duration
  * every spoken line has an audio file (narration lines are text-only by
    design, so they are exempt)
  * MiniMax H3 three-field prompts are complete when the video model needs them
  * the episode has a subtitle file

Blocking problems stop that episode from being composed; softer ones are
reported as warnings so the run can continue.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..media import ffmpeg as ff
from ..models import Episode, Status, is_narration
from .base import Context

# the three core fields an H3 prompt must carry
H3_FIELDS = ("integrated_multimodal_description", "overall_soundscape",
             "non_diegetic_music")


def _workflow_graph(ctx: Context, rel: str) -> dict:
    """The workflow, as the API format: node id -> node.

    The pool holds the cards, and each card's client can read the
    workflow; when there is no card to ask, the file itself is read.
    """
    if not rel:
        return {}
    for n in list(getattr(ctx.providers.visual, "nodes", None) or []):
        client = getattr(n, "client", None)
        if client is None:
            continue
        try:
            graph = client._load_workflow(rel)  # noqa: SLF001
        except Exception:  # noqa: BLE001
            continue
        if isinstance(graph, dict) and graph:
            return graph
    path = Path(rel)
    cands = [path]
    if not path.is_absolute():
        cands = [Path.cwd() / path,
                  Path(__file__).resolve().parents[2] / path]
    for c in cands:
        try:
            if c.exists():
                d = json.loads(c.read_text(encoding="utf-8"))
                return d if isinstance(d, dict) else {}
        except Exception:  # noqa: BLE001
            continue
    return {}


def _uses_h3(ctx: Context) -> bool:
    """True when the configured video workflow uses the native H3 nodes."""
    graph = _workflow_graph(ctx, ctx.cfg.comfyui.i2v_workflow)
    if not graph:
        return False
    return any("MiniMaxH3" in str(n.get("class_type", "")) for n in graph.values())


def _voice_is_in_the_picture(ctx: Context, h3: bool) -> bool:
    """True when the sound comes with the picture.

    H3 makes the voice, the room and the music in one go, and the
    compose mixes nothing else in when it does - so a line that has no
    audio file of its own is not a broken line: its voice is in the clip.
    A precheck that asks for a file the film does not use blocks every
    episode of a drama that is made this way.
    """
    if not h3:
        return False
    return bool(ctx.cfg.comfyui.native_audio) and \
        bool(ctx.cfg.compose.native_audio_exclusive)


def _h3_missing(prompt: str) -> list[str]:
    """The fields the prompt should carry and does not.

    Two shapes are in use: the three-field one, where the description is
    labelled, and the full-reference one - the shape the video model is
    given when the sound comes with the picture - where the description
    is the body and the pictures are named above it.  Asking for the
    label in the second shape blocks every shot of a drama made that
    way, and the shots it blocked were perfectly good ones.
    """
    if not prompt:
        return list(H3_FIELDS)
    if "subject_definitions:" in prompt or "<Picture" in prompt:
        want = ("overall_soundscape", "non_diegetic_music")
    else:
        want = H3_FIELDS
    return [f for f in want if f + ":" not in prompt]


def _check_episode(ctx: Context, ep: Episode, h3: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    voice_in_picture = _voice_is_in_the_picture(ctx, h3)
    # when the pipeline is set to make video, a shot that only has a picture
    # is a slideshow waiting to be shipped - that is an error, not a note
    want_video = ctx.cfg.comfyui.mode in ("video", "image_then_video")
    for sc in ep.scenes:
        for shot in sc.shots:
            vid = ctx.store.abs(shot.video_path) if shot.video_path else None
            img = ctx.store.abs(shot.image_path) if shot.image_path else None
            if not shot.prompt and not shot.video_prompt:
                errors.append(f"镜 {shot.id} 没有出图提示词")
            if not shot.prompt:
                warnings.append(f"镜 {shot.id} 没有出图提示词（只有视频提示词）")
            if not shot.video_path and not shot.image_path:
                errors.append(f"镜 {shot.id} 既没有画面也没有视频")
                continue
            if shot.video_path and (not vid or not vid.exists()):
                errors.append(f"镜 {shot.id} 视频文件缺失: {shot.video_path}")
                continue
            if shot.image_path and (not img or not img.exists()):
                errors.append(f"镜 {shot.id} 首帧图片缺失: {shot.image_path}")
                continue
            if want_video and not shot.video_path:
                errors.append(f"镜 {shot.id} 只有静帧没有视频"
                              f"（参考图不齐或视频没生成）")
                continue
            if vid and vid.exists():
                dur = ff.probe_duration(vid) or 0.0
                if dur <= 0:
                    errors.append(f"镜 {shot.id} 视频无法解析/时长为 0")
            if h3 and shot.video_path:
                missing = _h3_missing(shot.video_prompt or "")
                if missing:
                    errors.append(f"镜 {shot.id} H3 提示词缺少字段: {', '.join(missing)}")
        for line in sc.lines:
            if is_narration(line):
                continue
            if not line.audio_path:
                # a spoken line with no audio is a broken episode, not a note
                # - unless the voice is in the picture already
                if voice_in_picture:
                    continue
                errors.append(f"台词 {line.id}({line.speaker}) 没有配音")
                continue
            ap = ctx.store.abs(line.audio_path)
            if not ap.exists():
                errors.append(f"台词 {line.id}({line.speaker}) 音频文件缺失")
    if ep.subtitle_path:
        sp = ctx.store.abs(ep.subtitle_path)
        if not sp.exists():
            warnings.append(f"第{ep.index}集 字幕文件缺失: {ep.subtitle_path}")
    return errors, warnings


def run(ctx: Context) -> dict:
    h3 = _uses_h3(ctx)
    total_errors = 0
    total_warnings = 0
    blocked = 0
    for ep in ctx.target_episodes():
        errors, warnings = _check_episode(ctx, ep, h3)
        if errors:
            ep.compose_blocked = "；".join(errors[:6])
            blocked += 1
            ctx.log.error("precheck: 第%d集 未通过校验（%d 项问题）", ep.index, len(errors))
            for e in errors[:8]:
                ctx.log.error("    ✗ %s", e)
        else:
            ep.compose_blocked = ""
        for w in warnings[:8]:
            ctx.log.warning("precheck: 第%d集 ! %s", ep.index, w)
        total_errors += len(errors)
        total_warnings += len(warnings)
        if not errors:
            ctx.mark(ep, "precheck", Status.DONE)
    ctx.save()
    ctx.log.info("precheck: %d 项错误 / %d 项警告，%d 集被阻断",
                total_errors, total_warnings, blocked)
    return {"errors": total_errors, "warnings": total_warnings, "blocked": blocked}
