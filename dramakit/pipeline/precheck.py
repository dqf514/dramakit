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

from pathlib import Path

from ..media import ffmpeg as ff
from ..models import Episode, Status, is_narration
from .base import Context

# the three core fields an H3 prompt must carry
H3_FIELDS = ("integrated_multimodal_description", "overall_soundscape",
             "non_diegetic_music")


def _uses_h3(ctx: Context) -> bool:
    """True when the configured video workflow uses the native H3 nodes."""
    try:
        wf = ctx.providers.visual._load_workflow(  # noqa: SLF001
            ctx.cfg.comfyui.i2v_workflow)
    except Exception:  # noqa: BLE001
        return False
    return any("MiniMaxH3" in str(n.get("class_type", "")) for n in wf.values())


def _check_episode(ctx: Context, ep: Episode, h3: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
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
                vp = shot.video_prompt or ""
                missing = [f for f in H3_FIELDS if f + ":" not in vp]
                if missing:
                    errors.append(f"镜 {shot.id} H3 提示词缺少字段: {', '.join(missing)}")
        for line in sc.lines:
            if is_narration(line):
                continue
            if not line.audio_path:
                # a spoken line with no audio is a broken episode, not a note
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
