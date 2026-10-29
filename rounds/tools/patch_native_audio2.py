"""The voice comes out of the clip, and the clip gets the recorded line.

- The visual stage hands H3 the recording of the line as the voice
  reference, so the mouth and the voice are one generation.
- The compose stage builds the episode's voice from the clips instead of
  from the separate recordings: the voice and the picture are then the
  same thing.
"""
from pathlib import Path

# 1) a helper that lays the clips' audio on the timeline
p = Path(r"E:\\dramakit\\dramakit\\media\\ffmpeg.py")
s = p.read_text(encoding="utf-8")
old = """def mix_voice_bgm(voice: str | Path, bgm: Optional[str | Path], out: str | Path, *,"""
new = '''def mix_shot_audio(clips: Sequence[tuple[str, float, float]], out: str | Path,
                   *, duration: float = 0.0, rate: int = 44100) -> str:
    """Lay the audio of the shots on the timeline.

    `clips` is (path, start, length) per shot: where the clip begins and
    how much of it belongs there. The voice of the episode is then the
    voice that was generated with the picture.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    usable = [(c, st, ln) for c, st, ln in clips if Path(c).exists()]
    if not usable:
        return make_silence(out, duration or 1.0, rate=rate)
    args: list[str] = [ffmpeg_bin(), "-y"]
    for c, _st, _ln in usable:
        args += ["-i", str(c)]
    parts = []
    mixin = []
    for i, (_c, st, ln) in enumerate(usable):
        ms = int(max(0.0, st) * 1000)
        # only the part that belongs to this slot
        trim = (f"[{i}:a]atrim=0:{max(0.05, ln):.3f},asetpts=N/SR/TB,"
                f"adelay={ms}|{ms}[a{i}]")
        parts.append(trim)
        mixin.append(f"[a{i}]")
    fc = ";".join(parts) + ";" + "".join(mixin) + \
        f"amix=inputs={len(mixin)}:duration=longest:normalize=0[a]"
    args += ["-filter_complex", fc, "-map", "[a]", "-ac", "1", "-ar", str(rate),
             "-c:a", "libmp3lame", "-q:a", "3", str(out)]
    _run(args, quiet=False)
    if duration > 0:
        return pad_audio(out, out.with_name(out.stem + "_pad.mp3"), duration)
    return str(out)


def mix_voice_bgm(voice: str | Path, bgm: Optional[str | Path], out: str | Path, *,'''
assert old in s, "混音锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("ffmpeg.py 已改（片段人声摆到时间线上）")

# 2) the visual stage: the recorded line goes in as the voice reference
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py")
s = p.read_text(encoding="utf-8")
old = """        vprompt = shot.video_prompt or shot.prompt
        try:
            _render(ctx, "出视频", shot.id, lambda: vis.generate_video(
                prompt=vprompt, negative=shot.negative_prompt,
                image_path=str(img_out) if img_out.exists() else "",
                frames=frames, fps=c.fps, seed=seed, out_path=str(vid_out),
                extra=_extra(ctx), last_image_path=last))"""
new = """        vprompt = shot.video_prompt or shot.prompt
        extra = _extra(ctx)
        if c.native_audio:
            ref = _reference_audio(ctx, shot)
            if ref:
                extra["ref_audio_path"] = ref
                extra["ref_audio_node"] = c.ref_audio_node
        try:
            _render(ctx, "出视频", shot.id, lambda: vis.generate_video(
                prompt=vprompt, negative=shot.negative_prompt,
                image_path=str(img_out) if img_out.exists() else "",
                frames=frames, fps=c.fps, seed=seed, out_path=str(vid_out),
                extra=extra, last_image_path=last))"""
assert old in s, "视觉锚点没找到"
s = s.replace(old, new, 1)

old = """            _render(ctx, "出视频", shot.id, lambda: vis.generate_video(
                prompt=vprompt, negative=shot.negative_prompt,
                image_path=str(img_out) if img_out.exists() else "",
                frames=frames, fps=c.fps, seed=seed, out_path=str(vid_out),
                extra=_extra(ctx)))"""
new = """            _render(ctx, "出视频", shot.id, lambda: vis.generate_video(
                prompt=vprompt, negative=shot.negative_prompt,
                image_path=str(img_out) if img_out.exists() else "",
                frames=frames, fps=c.fps, seed=seed, out_path=str(vid_out),
                extra=extra))"""
assert old in s, "视觉回退锚点没找到"
s = s.replace(old, new, 1)

# the helper that builds the shot's reference audio
old = """def _gen_video(ctx: Context, sc, shot: Shot, duration: float = 0.0) -> tuple[str, bool, str]:"""
new = '''def _reference_audio(ctx: Context, shot: Shot) -> str:
    """The recording of this shot's line, as the voice reference.

    H3 speaks the words itself, but it takes the timbre from this
    recording - so the character sounds the same in every shot.
    """
    from .lipsync import _scene_wav
    tl = ctx.timeline(ctx.target_episodes()[0])
    for tsc in tl.scenes:
        for ts in tsc.shots:
            if ts.shot.id != shot.id:
                continue
            placed = []
            for t in tsc.lines:
                if t.line.kind.value != "dialogue":
                    continue
                if not (ts.start - 0.02 <= t.start < ts.start + ts.duration):
                    continue
                if not t.line.audio_path:
                    continue
                placed.append((t.start - tsc.start,
                               ctx.store.abs(t.line.audio_path)))
            if not placed:
                return ""
            out = ctx.store.root / "tmp" / f"refaudio_{shot.id}.wav"
            if _scene_wav(placed, ts.start - tsc.start, ts.duration, out):
                return str(out)
    return ""


def _gen_video(ctx: Context, sc, shot: Shot, duration: float = 0.0) -> tuple[str, bool, str]:'''
assert old in s, "参考音频函数锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("visual.py 已改（上传参考音频）")

# 3) the compose: the voice of the episode comes from the clips
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\compose.py")
s = p.read_text(encoding="utf-8")
old = """def _scene_voice(ctx: Context, tscene, tmp: Path, idx: int = 0) -> str:
    parts: list[str] = []"""
new = """def _scene_voice(ctx: Context, tscene, tmp: Path, idx: int = 0,
                 clips=None) -> str:
    if ctx.cfg.comfyui.native_audio and clips:
        # the voice was generated with the picture: take it from the clips
        items = []
        for path, tshot in clips:
            items.append((str(path), tshot.start - tscene.start,
                          tshot.duration))
        out = tmp / f"scene_voice_{idx:03d}.mp3"
        return ff.mix_shot_audio(items, out, duration=tscene.duration)
    parts: list[str] = []"""
assert old in s, "场景人声锚点没找到"
s = s.replace(old, new, 1)

old = """        scene_voices.append(_scene_voice(ctx, tscene, tmp, si))"""
new = """        scene_voices.append(_scene_voice(ctx, tscene, tmp, si,
                                         shot_clips[begin:end]))"""
assert old in s, "调用锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("compose.py 已改（人声来自片段）")
