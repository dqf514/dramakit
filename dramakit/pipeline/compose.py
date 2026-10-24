"""Stage 11 — compose: assemble each episode into a finished 1080x1920 mp4.

Per episode:
  1. build the timeline (dialogue-driven; shots stretched to cover each scene)
  2. each shot -> a normalized clip (generated video re-timed, still image given
     Ken Burns motion, or a black card placeholder when no visual exists)
  3. concat shots -> scene picture; concat scenes -> episode picture (silent)
  4. concat line audio per scene (silence for any missing) -> pad to scene dur;
     concat scenes -> episode dialogue track (sample-aligned with the picture)
  5. mix dialogue + BGM (sidechain ducking, loudness normalize)
  6. mux picture + mix, burn ASS subtitles -> episodes/ep_XXX.mp4
  7. grab a cover frame
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..media import ffmpeg as ff
from ..models import Status
from .base import Context, build_timeline

log = logging.getLogger("dramakit.compose")


def _shot_clip(ctx: Context, tshot, cc, tmp: Path, idx: int) -> str:
    shot = tshot.shot
    out = tmp / f"shot_{idx:04d}.mp4"
    dur = tshot.duration
    # 1) generated video
    if shot.video_path:
        vp = ctx.store.abs(shot.video_path)
        if vp.exists():
            return ff.normalize_video_clip(vp, out, dur, width=cc.width, height=cc.height,
                                           fps=cc.fps, crf=cc.crf, preset=cc.preset)
    # 2) still image -> Ken Burns
    if shot.image_path:
        ip = ctx.store.abs(shot.image_path)
        if ip.exists():
            zoom_out = (idx % 2 == 1) and cc.motion_effect == "kenburns"
            return ff.image_to_clip(ip, out, dur, width=cc.width, height=cc.height,
                                    fps=cc.fps, motion=cc.motion_effect,
                                    zoom_max=cc.kenburns_scale, zoom_out=zoom_out,
                                    crf=cc.crf, preset=cc.preset)
    # 3) placeholder card
    return ff.color_clip(out, dur, width=cc.width, height=cc.height, fps=cc.fps,
                         color="0x101014")


def _scene_voice(ctx: Context, tscene, tmp: Path) -> str:
    parts: list[str] = []
    for i, tl_line in enumerate(tscene.lines):
        l = tl_line.line
        d = max(l.duration, 0.05)
        if l.audio_path:
            ap = ctx.store.abs(l.audio_path)
            if ap.exists():
                parts.append(str(ap))
                continue
        sil = tmp / f"sil_{i:03d}.mp3"
        parts.append(ff.make_silence(sil, d))
    if not parts:
        v = tmp / "scene_voice_empty.mp3"
        return ff.make_silence(v, tscene.duration)
    joined = tmp / "scene_voice_raw.mp3"
    ff.concat_audio(parts, joined)
    padded = tmp / "scene_voice.mp3"
    return ff.pad_audio(joined, padded, tscene.duration)


def compose_episode(ctx: Context, ep) -> str:
    cc = ctx.cfg.compose
    tl = build_timeline(ep)
    if tl.duration <= 0:
        raise RuntimeError(f"第{ep.index}集时间线为空")
    tmp = ctx.store.root / "tmp" / f"ep_{ep.index:03d}"
    tmp.mkdir(parents=True, exist_ok=True)

    # --- picture ---
    scene_videos: list[str] = []
    scene_voices: list[str] = []
    shot_idx = 0
    for si, tscene in enumerate(tl.scenes):
        clips = []
        for tshot in tscene.shots:
            clips.append(_shot_clip(ctx, tshot, cc, tmp, shot_idx))
            shot_idx += 1
        if not clips:  # scene with no shots -> single card for its duration
            clips.append(ff.color_clip(tmp / f"sc_{si}_card.mp4", tscene.duration,
                                       width=cc.width, height=cc.height, fps=cc.fps,
                                       color="0x101014"))
        sv = tmp / f"scene_{si:03d}_v.mp4"
        ff.concat_videos(clips, sv)
        sv_path = str(sv)
        if cc.transition != "none" and tscene.duration > 0.25:
            # duration-preserving fades keep picture/voice/subtitles in sync
            fd = min(cc.transition_duration, tscene.duration / 3)
            sv_path = ff.apply_fades(sv, tmp / f"scene_{si:03d}_vf.mp4",
                                     tscene.duration, fade_in=fd, fade_out=fd,
                                     crf=cc.crf, preset=cc.preset)
        scene_videos.append(sv_path)
        scene_voices.append(_scene_voice(ctx, tscene, tmp))

    picture = tmp / "picture.mp4"
    ff.concat_videos(scene_videos, picture)
    voice = tmp / "voice.mp3"
    ff.concat_audio(scene_voices, voice)
    ep.voice_path = ctx.store.rel(voice)

    # --- music ---
    bgm = ctx.store.abs(ep.bgm_path) if ep.bgm_path else None
    if bgm and not bgm.exists():
        bgm = None
    mix = tmp / "mix.mp3"
    target = cc.target_loudness_lufs if cc.loudness_normalize else None
    ff.mix_voice_bgm(voice, str(bgm) if bgm else None, mix,
                     bgm_volume=ctx.cfg.music.bgm_volume,
                     duck=ctx.cfg.music.duck_voice, target_lufs=target)

    # --- mux + burn subtitles ---
    ass = ctx.store.abs(ep.ass_path) if ep.ass_path else None
    if ass and not ass.exists():
        ass = None
    final = ctx.store.episode_video_path(ep)
    ff.mux(picture, mix, final, video_bitrate=cc.video_bitrate, audio_bitrate=cc.audio_bitrate,
           codec=cc.codec, crf=cc.crf, preset=cc.preset, pixel_format=cc.pixel_format,
           fps=cc.fps, ass_file=str(ass) if (cc.burn_subtitles and ass) else None)

    # --- cover ---
    if cc.generate_cover:
        try:
            cover = ctx.store.cover_path(ep)
            at = 0.5
            first_img = next((ctx.store.abs(ts.shot.image_path)
                              for ts in tl.shots if ts.shot.image_path), None)
            if cc.cover_from_shot == "first" and first_img and first_img.exists():
                ff.extract_frame(first_img, cover, at=0.0, width=cc.width)
            else:
                ff.extract_frame(final, cover,
                                 at=(cc.cover_from_shot == "last") * max(tl.duration - 0.5, 0)
                                 or min(1.0, tl.duration / 2), width=cc.width)
            ep.cover_path = ctx.store.rel(cover)
        except Exception as e:  # noqa: BLE001
            log.warning("封面生成失败: %s", e)

    ep.status = Status.DONE
    ep.video_path = ctx.store.rel(final)
    ctx.mark(ep, "compose", Status.DONE)

    # cleanup intermediates unless asked to keep
    if not ctx.cfg.comfyui.save_intermediate:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    return str(final)


def run(ctx: Context) -> dict:
    if not ff.check_available():
        raise RuntimeError("未找到 ffmpeg/ffprobe，请先安装并加入 PATH")
    made = 0
    for ep in ctx.target_episodes():
        if ctx.stage_done(ep, "compose") and ep.video_path and ctx.store.abs(ep.video_path).exists():
            continue
        if not ep.scenes:
            ctx.log.warning("compose: 第%d集无内容，跳过", ep.index)
            continue
        ctx.log.info("compose: 第%d集《%s》渲染中…", ep.index, ep.title)
        try:
            out = compose_episode(ctx, ep)
            ctx.save()
            made += 1
            ctx.log.info("compose: 第%d集 → %s (%.1fs)", ep.index,
                         Path(out).name, build_timeline(ep).duration)
        except Exception as e:  # noqa: BLE001
            ctx.log.error("compose: 第%d集失败 %s", ep.index, e)
            ctx.mark(ep, "compose", Status.FAILED)
            ctx.save()
            if ctx.cfg.pipeline.fail_fast:
                raise
    return {"episodes_rendered": made}
