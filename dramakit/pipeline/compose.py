"""Stage 11 — compose: assemble each episode into a finished mp4.

Per episode:
  1. build the timeline (dialogue-driven; shots stretched to cover each scene)
  2. each shot -> a normalized clip (generated video re-timed, still image given
     Ken Burns motion, or a black card placeholder when no visual exists)
  2b. colour grade: measure every shot, pull them onto one look
  3. concat shots -> scene picture; concat scenes -> episode picture (silent)
  4. concat line audio per scene (silence for any missing) -> pad to scene dur;
     concat scenes -> episode dialogue track (sample-aligned with the picture)
  5. mix dialogue + BGM (sidechain ducking, loudness normalize)
  6. mux picture + mix, burn ASS subtitles -> episodes/ep_XXX.mp4
  7. grab a cover frame
  8. export an FCPXML timeline so an editor can pick the episode up in an NLE
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..media import ffmpeg as ff
from ..media import grade as gr
from ..media import nle
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


def _grade_shots(ctx: Context, cc, clips: list[tuple[str, object]],
                 tmp: Path) -> list[tuple[str, object]]:
    """Pull every shot onto one look.

    AI shots are rendered independently, so each one lands on a slightly
    different exposure / saturation / white balance. Cut together they read as
    amateur. Measuring all of them and targeting the episode median is the
    cheapest big win in the whole post chain.
    """
    if not clips:
        return clips
    measured = [gr.analyze(path) for path, _ in clips]
    target = gr.median_stats(measured)
    lut = cc.lut or None
    if lut:
        lut_path = Path(lut)
        if not lut_path.is_absolute():
            lut_path = (ctx.store.root / lut_path)
        if not lut_path.exists():
            ctx.log.warning("compose: LUT 文件不存在，跳过: %s", lut)
            lut = None
        else:
            lut = str(lut_path)
    out: list[tuple[str, object]] = []
    changed = 0
    for i, (path, tshot) in enumerate(clips):
        if not gr.grade_filter(measured[i], target, strength=cc.grade_strength, lut=lut):
            out.append((path, tshot))
            continue
        dst = tmp / f"grade_{i:04d}.mp4"
        gr.grade_shot(path, dst, target, strength=cc.grade_strength, lut=lut,
                      measured=measured[i], crf=cc.crf, preset=cc.preset,
                      fps=cc.fps)
        out.append((str(dst), tshot))
        changed += 1
    if changed:
        ctx.log.info("compose: 统一调色 %d/%d 镜（目标 luma=%.1f sat=%.1f tint=%+.1f）",
                     changed, len(clips), target.luma, target.sat, target.tint)
    return out


def _export_nle(ctx: Context, ep, tl, shot_clips: list[tuple[str, object]],
                music_path: str | None) -> str | None:
    """Export the episode as an FCPXML timeline an editor can open.

    The clips are copied to a persistent folder first: the working files live
    in tmp/ and are deleted after compose, and a timeline whose media is gone
    is worthless.
    """
    if not shot_clips:
        return None
    out_dir = ctx.store.root / "nle" / f"ep_{ep.index:03d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    timeline = nle.Timeline(
        name=f"{ctx.project.meta.title or ctx.project.meta.name} EP{ep.index:03d}",
        width=ctx.cfg.compose.width, height=ctx.cfg.compose.height,
        fps=ctx.cfg.compose.fps, duration=tl.duration,
    )

    # picture spine: one clip per shot, at its exact timeline position
    for (src, tshot), timed in zip(shot_clips, tl.shots):
        dst = out_dir / f"shot_{timed.shot.id}.mp4"
        try:
            import shutil
            shutil.copy2(src, dst)
        except Exception:  # noqa: BLE001
            dst = Path(src)
        timeline.video.append(nle.Clip(
            src=dst, offset=timed.start, duration=timed.duration, start=0.0,
            name=f"shot_{timed.shot.id}", has_video=True, has_audio=False))

    # dialogue lane: the per-line TTS clips
    dialogue: list[nle.Clip] = []
    for tl_line in tl.lines:
        if tl_line.is_narration or not tl_line.line.audio_path:
            continue
        ap = ctx.store.abs(tl_line.line.audio_path)
        if not ap.exists():
            continue
        dialogue.append(nle.Clip(
            src=ap, offset=tl_line.start,
            duration=max(tl_line.end - tl_line.start, 0.05), start=0.0,
            name=f"{tl_line.line.speaker}_{tl_line.line.id}",
            has_video=False, has_audio=True))
    if dialogue:
        timeline.lanes[1] = ("Dialogue", dialogue)

    # music lane: the bed / BGM stem
    if music_path and Path(music_path).exists():
        stem = out_dir / "music.mp3"
        try:
            import shutil
            shutil.copy2(music_path, stem)
        except Exception:  # noqa: BLE001
            stem = Path(music_path)
        timeline.lanes[2] = ("Music", [nle.Clip(
            src=stem, offset=0.0, duration=tl.duration, start=0.0,
            name="music", has_video=False, has_audio=True)])

    out = out_dir / f"ep_{ep.index:03d}.fcpxml"
    nle.write_fcpxml(timeline, out)
    ctx.log.info("compose: 第%d集 已导出 FCPXML 时间线 %s", ep.index, out.name)
    return str(out)


def _scene_voice(ctx: Context, tscene, tmp: Path, idx: int = 0) -> str:
    parts: list[str] = []
    for i, tl_line in enumerate(tscene.lines):
        l = tl_line.line
        # narration is screen-only: it contributes no voice and no silence gap
        if tl_line.is_narration:
            continue
        d = max(l.duration, 0.05)
        if l.audio_path:
            ap = ctx.store.abs(l.audio_path)
            if ap.exists():
                parts.append(str(ap))
                continue
        sil = tmp / f"sil_{idx:03d}_{i:03d}.mp3"
        parts.append(ff.make_silence(sil, d))
    if not parts:
        v = tmp / f"scene_voice_empty_{idx:03d}.mp3"
        return ff.make_silence(v, tscene.duration)
    joined = tmp / f"scene_voice_raw_{idx:03d}.mp3"
    ff.concat_audio(parts, joined)
    padded = tmp / f"scene_voice_{idx:03d}.mp3"
    return ff.pad_audio(joined, padded, tscene.duration)


def compose_episode(ctx: Context, ep) -> str:
    cc = ctx.cfg.compose
    tl = ctx.timeline(ep)
    if tl.duration <= 0:
        raise RuntimeError(f"第{ep.index}集时间线为空")
    tmp = ctx.store.root / "tmp" / f"ep_{ep.index:03d}"
    tmp.mkdir(parents=True, exist_ok=True)

    # --- picture ---
    # Build every shot clip first, grade them as a set (the grade target is the
    # episode median, so it needs all shots), then group them into scenes.
    shot_clips: list[tuple[str, object]] = []
    scene_ranges: list[tuple[int, int]] = []
    for tscene in tl.scenes:
        begin = len(shot_clips)
        for tshot in tscene.shots:
            shot_clips.append(
                (_shot_clip(ctx, tshot, cc, tmp, len(shot_clips)), tshot))
        scene_ranges.append((begin, len(shot_clips)))
    if cc.grade_shots:
        shot_clips = _grade_shots(ctx, cc, shot_clips, tmp)

    scene_videos: list[str] = []
    scene_voices: list[str] = []
    for si, tscene in enumerate(tl.scenes):
        begin, end = scene_ranges[si]
        clips = [path for path, _ in shot_clips[begin:end]]
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
        scene_voices.append(_scene_voice(ctx, tscene, tmp, si))

    picture = tmp / "picture.mp4"
    ff.concat_videos(scene_videos, picture)
    voice = tmp / "voice.mp3"
    ff.concat_audio(scene_voices, voice)
    ep.voice_path = ctx.store.rel(voice)

    # --- MiniMax H3 native audio bed ---
    # The score comes from a music-only clip of every scene: an empty shot of
    # the location, with no one in it and nobody speaking. The shots' own
    # sound is not used - H3 reads the prompt out loud in gibberish when a
    # character is told to talk, and that would end up under the recorded
    # dialogue.
    bed = None
    if cc.h3_audio == "bed":
        beds: list[str] = []
        for tscene in tl.scenes:
            sc = tscene.scene
            clip = ctx.store.root / "music" / f"score_ep{ep.index:03d}_sc{sc.index:03d}.mp4"
            if not clip.exists():
                continue
            raw = ff.extract_audio(clip, tmp / f"score_sc{sc.index:03d}.mp3")
            if not raw:
                continue
            beds.append(ff.loop_audio(raw, tmp / f"scorebed_sc{sc.index:03d}.mp3",
                                       tscene.duration))
        if beds:
            bed = tmp / "h3_bed.mp3"
            ff.concat_audio(beds, bed)
            ctx.log.info("compose: 第%d集 配乐垫底 %d 段（每场一段无人空镜）",
                         ep.index, len(beds))
        else:
            ctx.log.warning("compose: 第%d集 没有配乐镜头，音乐垫底为空", ep.index)

    # --- music stem ---
    # One music track under the dialogue: the H3 bed and the library BGM each
    # with their own level. Mixing them here (instead of chaining two passes
    # of bgm_volume) keeps the balance predictable.
    bgm = ctx.store.abs(ep.bgm_path) if ep.bgm_path else None
    if bgm and not bgm.exists():
        bgm = None
    parts: list[tuple[str, float]] = []
    if bed:
        # the bed level depends on the episode, so set it against the dialogue:
        # the music's loudest moments have to stay clearly under the voices
        try:
            gain = ff.bed_gain_for(voice, bed, target_gap_lu=cc.music_gap_lu)
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("compose: 垫底增益测算失败: %s", str(e)[:120])
            gain = cc.h3_audio_gain
        parts.append((bed, gain))
        ctx.log.info("compose: 第%d集 垫底增益 x%.2f（目标比人声低 %d LU）",
                     ep.index, gain, cc.music_gap_lu)
    if bgm:
        parts.append((bgm, ctx.cfg.music.bgm_volume))
    music = ""
    if parts:
        music = ff.mix_tracks(parts, tmp / "music.mp3", duration=tl.duration)

    # The music stem is the only thing that proves "there is a BGM": the final
    # mix is loud either way because the dialogue is in it. Measure the stem.
    mix_info: dict = {"bed_segments": len(beds) if bed else 0,
                      "library_bgm": bool(bgm)}
    if music:
        measured = ff.measure_loudness(music)
        mix_info["music_lufs"] = round(float(measured.get("input_i", 0.0)), 2)
        if mix_info["music_lufs"] < -60:
            ctx.log.warning("compose: 第%d集 音乐轨是静音的（%.1f LUFS）",
                            ep.index, mix_info["music_lufs"])
        else:
            ctx.log.info("compose: 第%d集 音乐轨 %.1f LUFS（垫底 %d 段%s）",
                         ep.index, mix_info["music_lufs"], mix_info["bed_segments"],
                         " + 曲库" if bgm else "")
    else:
        mix_info["music_lufs"] = None
        ctx.log.warning("compose: 第%d集 没有任何音乐轨", ep.index)
    ep.qc_report = {**(ep.qc_report or {}), "mix": mix_info}

    mix = tmp / "mix.mp3"
    target = cc.target_loudness_lufs if cc.loudness_normalize else None
    ff.mix_voice_bgm(voice, music or None, mix,
                     bgm_volume=1.0,
                     duck=ctx.cfg.music.duck_voice, target_lufs=target,
                     room=float(cc.voice_room or 0))

    # The mux takes the shorter of the two tracks, so a picture that came out
    # a little short would cut the end of the dialogue off. Both tracks are
    # brought to the timeline length first.
    pic_dur = ff.probe_duration(picture)
    mix_dur = ff.probe_duration(mix)
    if pic_dur and mix_dur and abs(pic_dur - mix_dur) > 0.1:
        if mix_dur < pic_dur:
            ctx.log.warning("compose: 第%d集 音轨比画面短 %.2fs，补静音", ep.index,
                             pic_dur - mix_dur)
            mix = ff.pad_audio(mix, tmp / "mix_pad.mp3", pic_dur)
        else:
            ctx.log.warning("compose: 第%d集 画面比音轨短 %.2fs，补末帧", ep.index,
                             mix_dur - pic_dur)
            picture = ff.pad_video(picture, tmp / "picture_pad.mp4", mix_dur,
                                   width=cc.width, height=cc.height, fps=cc.fps,
                                   crf=cc.crf, preset=cc.preset)

    # --- mux + burn subtitles ---
    ass = ctx.store.abs(ep.ass_path) if ep.ass_path else None
    if ass and not ass.exists():
        ass = None
    final = ctx.store.episode_video_path(ep)
    # The AIGC label: since 2026 an AI drama has to say so on the picture,
    # and the filing number belongs on it as well.
    mark = (cc.ai_declaration or "").strip()
    if mark and cc.filing_number:
        mark = f"{mark}  {cc.filing_number}"
    ff.mux(picture, mix, final, video_bitrate=cc.video_bitrate, audio_bitrate=cc.audio_bitrate,
           codec=cc.codec, crf=cc.crf, preset=cc.preset, pixel_format=cc.pixel_format,
           fps=cc.fps, ass_file=str(ass) if (cc.burn_subtitles and ass) else None,
           watermark=mark, watermark_size=max(12, cc.width // 52),
           watermark_seconds=float(cc.ai_declaration_seconds or 0),
           grain=int(cc.film_grain or 0))

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
            # The cover decides whether anybody clicks: the title has to be
            # on it, big enough to read on a phone.
            title = (ep.title or "").strip()
            if title and cc.cover_title:
                ff.draw_title(cover, title, width=cc.width, height=cc.height)
            ep.cover_path = ctx.store.rel(cover)
        except Exception as e:  # noqa: BLE001
            log.warning("封面生成失败: %s", e)

    ep.status = Status.DONE
    ep.video_path = ctx.store.rel(final)
    ctx.mark(ep, "compose", Status.DONE)

    # --- NLE hand-off ---
    # A single FCPXML an editor can open in Resolve / Premiere / FCP, so the
    # automated render is a starting point rather than a dead end.
    if cc.nle_export:
        try:
            _export_nle(ctx, ep, tl, shot_clips, music or None)
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("compose: 第%d集 FCPXML 导出失败: %s", ep.index, str(e)[:160])

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
        if ep.compose_blocked:
            ctx.log.error("compose: 第%d集被 precheck 阻断，跳过（%s）",
                          ep.index, ep.compose_blocked[:160])
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
                         Path(out).name,
         ctx.timeline(ep).duration)
        except Exception as e:  # noqa: BLE001
            ctx.log.error("compose: 第%d集失败 %s", ep.index, e)
            ctx.mark(ep, "compose", Status.FAILED)
            ctx.save()
            if ctx.cfg.pipeline.fail_fast:
                raise
    return {"episodes_rendered": made}
