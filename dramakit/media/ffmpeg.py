"""ffmpeg / ffprobe helpers.

All episode assembly goes through here. Design goals:
  * every shot becomes a normalized 1080x1920 @fps clip of an exact duration
    (still image -> Ken Burns motion clip, or generated video -> re-timed clip)
  * clips concat losslessly (identical params) into the silent picture track
  * voice + BGM are mixed (optionally sidechain-ducked) into the audio track
  * subtitles are burned from an ASS file (red-fruit short-drama styling)

Windows note: the `subtitles` filter path is resolved relative to CWD, so for
burning we chdir into the subtitle folder and pass a bare filename — this dodges
the notorious Windows drive-letter/colon escaping problem entirely.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence

log = logging.getLogger("dramakit.ffmpeg")


def ffmpeg_bin() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def ffprobe_bin() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def _run(cmd: Sequence[str], cwd: Optional[Path] = None, quiet: bool = True) -> subprocess.CompletedProcess:
    log.debug("ffmpeg: %s", " ".join(str(c) for c in cmd))
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0 and not quiet:
        raise RuntimeError(f"ffmpeg failed ({r.returncode}): {r.stderr[-800:]}")
    if r.returncode != 0:
        log.error("ffmpeg failed (%s): %s", r.returncode, r.stderr[-500:])
    return r


# --------------------------------------------------------------------------- #
# probing
# --------------------------------------------------------------------------- #
def probe_duration(path: str | Path) -> float:
    try:
        r = subprocess.run(
            [ffprobe_bin(), "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, encoding="utf-8", errors="ignore")
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:  # noqa: BLE001
        try:
            from mutagen import File as MFile
            f = MFile(str(path))
            if f and f.info and f.info.length:
                return float(f.info.length)
        except Exception:  # noqa: BLE001
            pass
    return 0.0


def probe_streams(path: str | Path) -> dict:
    r = subprocess.run(
        [ffprobe_bin(), "-v", "error", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="ignore")
    try:
        data = json.loads(r.stdout)
    except Exception:  # noqa: BLE001
        return {}
    out = {"video": None, "audio": None}
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and not out["video"]:
            out["video"] = s
        elif s.get("codec_type") == "audio" and not out["audio"]:
            out["audio"] = s
    return out


# --------------------------------------------------------------------------- #
# single-clip builders
# --------------------------------------------------------------------------- #
def image_to_clip(image: str | Path, out: str | Path, duration: float, *,
                  width: int, height: int, fps: int, motion: str = "kenburns",
                  zoom_max: float = 1.12, zoom_out: bool = False,
                  crf: int = 20, preset: str = "medium") -> str:
    """Still image -> mp4 clip of exact duration, cover-cropped to WxH, with
    optional Ken Burns (zoompan) motion. Single input frame expanded by zoompan."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    duration = max(duration, 0.04)
    frames = max(int(round(duration * fps)), 1)
    # scale up 2x then cover-crop for smooth zoom without jitter
    pre = (f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
           f"crop={width*2}:{height*2}")
    if motion in ("kenburns", "zoompan"):
        if zoom_out:
            zexpr = f"max({zoom_max:.3f}-({zoom_max-1.0:.4f})*on/{frames},1.0)"
        else:
            zexpr = f"min(1.0+{ (zoom_max-1.0)/max(frames,1):.6f}*on,{zoom_max:.3f})"
        vf = (f"{pre},zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={width}x{height}:fps={fps},format=yuv420p")
    else:
        vf = f"{pre},scale={width}:{height},fps={fps},format=yuv420p"
    cmd = [ffmpeg_bin(), "-y", "-i", str(image), "-vf", vf,
           "-r", str(fps), "-frames:v", str(frames),
           "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
           "-pix_fmt", "yuv420p", "-t", f"{duration:.3f}", str(out)]
    _run(cmd, quiet=False)
    return str(out)


def normalize_video_clip(src: str | Path, out: str | Path, duration: float, *,
                         width: int, height: int, fps: int,
                         crf: int = 20, preset: str = "medium") -> str:
    """Existing video (e.g. ComfyUI i2v) -> cover-crop to WxH, retimed to
    `duration` by loop/trim, audio stripped (we add our own mix later).

    A clip shorter than its slot is held on its last frame rather than
    rewound to the start - a rewind in the middle of a cut reads as a glitch.
    The hold has to be long enough: the timeline can stretch a shot well past
    the length of the video that was generated for it, and a fixed two second
    hold left the picture short of the dialogue, which cut the end of the
    episode off in the mux.
    """
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    src_dur = probe_duration(src)
    hold = 0.5
    if src_dur > 0:
        hold = max(hold, duration - src_dur + 0.5)
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
          f"crop={width}:{height},fps={fps},format=yuv420p,"
          f"tpad=stop_mode=clone:stop_duration={hold:.3f}")
    cmd = [ffmpeg_bin(), "-y", "-i", str(src),
           "-vf", vf,
           "-t", f"{duration:.3f}", "-an",
           "-c:v", "libx264", "-crf", str(crf), "-preset", preset, str(out)]
    _run(cmd, quiet=False)
    return str(out)


def pad_video(src: str | Path, out: str | Path, total_duration: float, *,
              width: int = 0, height: int = 0, fps: int = 30,
              crf: int = 20, preset: str = "medium") -> str:
    """Hold the last frame until the clip is exactly `total_duration` long."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    cur = probe_duration(src)
    if cur <= 0:
        return str(src)
    if cur >= total_duration - 0.03:
        return str(src)
    vf = f"tpad=stop_mode=clone:stop_duration={total_duration - cur + 0.5:.3f}"
    _run([ffmpeg_bin(), "-y", "-i", str(src), "-vf", vf, "-t", f"{total_duration:.3f}",
          "-an", "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
          "-pix_fmt", "yuv420p", str(out)], quiet=False)
    return str(out)


def apply_fades(src: str | Path, out: str | Path, duration: float, *,
                fade_in: float = 0.0, fade_out: float = 0.0,
                crf: int = 20, preset: str = "medium") -> str:
    """Fade a clip in/out without changing its duration.

    Scene transitions use this instead of xfade: overlapping two clips would
    shorten the picture track and desync it from the dialogue/subtitle timeline.
    """
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    vf: list[str] = []
    if fade_in > 0:
        vf.append(f"fade=t=in:st=0:d={fade_in:.3f}")
    if fade_out > 0:
        vf.append(f"fade=t=out:st={max(duration - fade_out, 0):.3f}:d={fade_out:.3f}")
    if not vf:
        shutil.copy2(src, out)
        return str(out)
    _run([ffmpeg_bin(), "-y", "-i", str(src), "-vf", ",".join(vf), "-an",
          "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
          "-pix_fmt", "yuv420p", "-t", f"{duration:.3f}", str(out)], quiet=False)
    return str(out)


def color_clip(out: str | Path, duration: float, *, width: int, height: int,
               fps: int, color: str = "black", text: str = "") -> str:
    """Solid color (or title-card) clip — used as a placeholder when a shot has
    no generated visual yet, so the timeline still assembles."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    vf = f"color=c={color}:s={width}x{height}:r={fps}:d={duration:.3f}"
    cmd = [ffmpeg_bin(), "-y", "-f", "lavfi", "-i", vf,
           "-t", f"{duration:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)]
    _run(cmd, quiet=False)
    return str(out)


# --------------------------------------------------------------------------- #
# concatenation
# --------------------------------------------------------------------------- #
def concat_videos(clips: Sequence[str | Path], out: str | Path) -> str:
    """Lossless concat of identically-encoded clips via the concat demuxer."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    clips = [str(c) for c in clips if Path(c).exists()]
    if not clips:
        raise RuntimeError("concat_videos: no clips")
    if len(clips) == 1:
        shutil.copy2(clips[0], out)
        return str(out)
    list_file = out.with_suffix(".concat.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{Path(c).resolve().as_posix()}'\n")
    cmd = [ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
           "-c", "copy", str(out)]
    r = _run(cmd)
    if r.returncode != 0:
        # fallback: re-encode (handles minor param drift)
        cmd = [ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
               "-c:v", "libx264", "-crf", "20", "-preset", "medium",
               "-pix_fmt", "yuv420p", str(out)]
        _run(cmd, quiet=False)
    list_file.unlink(missing_ok=True)
    return str(out)


# --------------------------------------------------------------------------- #
# audio
# --------------------------------------------------------------------------- #
def make_silence(out: str | Path, duration: float, *, rate: int = 44100) -> str:
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    _run([ffmpeg_bin(), "-y", "-f", "lavfi", "-i", f"anullsrc=r={rate}:cl=stereo",
          "-t", f"{max(duration,0.01):.3f}", "-c:a", "libmp3lame", "-q:a", "4", str(out)])
    return str(out)


def extract_audio(src: str | Path, out: str | Path, *, volume: float = 1.0) -> str:
    """Extract the audio stream of a video to an mp3 (empty file if none)."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    af = f"volume={volume}" if abs(volume - 1.0) > 1e-3 else "anull"
    r = _run([ffmpeg_bin(), "-y", "-i", str(src), "-vn", "-af", af,
              "-c:a", "libmp3lame", "-q:a", "4", str(out)], quiet=True)
    if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        out.unlink(missing_ok=True)
        return ""
    return str(out)


def concat_audio(parts: Sequence[str | Path], out: str | Path) -> str:
    """Concat audio files (re-encoded to a uniform mp3 stream)."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    parts = [str(p) for p in parts if Path(p).exists()]
    if not parts:
        return make_silence(out, 0.1)
    if len(parts) == 1:
        shutil.copy2(parts[0], out)
        return str(out)
    list_file = out.with_suffix(".concat.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{Path(p).resolve().as_posix()}'\n")
    cmd = [ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
           "-c:a", "libmp3lame", "-q:a", "4", str(out)]
    r = _run(cmd)
    if r.returncode != 0:
        inputs: list[str] = []
        for p in parts:
            inputs += ["-i", p]
        n = len(parts)
        filt = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
        _run([ffmpeg_bin(), "-y", *inputs, "-filter_complex", filt, "-map", "[a]",
              "-c:a", "libmp3lame", "-q:a", "4", str(out)], quiet=False)
    list_file.unlink(missing_ok=True)
    return str(out)


def loop_audio(src: str | Path, out: str | Path, duration: float,
               fade: float = 0.4) -> str:
    """Loop a clip until it fills `duration`, with a fade at the end.

    The music bed is one short clip of the scene played under the whole
    scene; a hard cut every few seconds would be noticed, so it fades out
    instead.
    """
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    cur = probe_duration(src)
    if cur <= 0:
        return make_silence(out, duration)
    if cur >= duration - 0.05:
        return pad_audio(src, out, duration)
    af = f"afade=t=out:st={max(duration - fade, 0):.3f}:d={fade:.3f}"
    _run([ffmpeg_bin(), "-y", "-stream_loop", "-1", "-i", str(src),
          "-t", f"{duration:.3f}", "-af", af,
          "-c:a", "libmp3lame", "-q:a", "3", str(out)])
    return str(out)


def pad_audio(src: str | Path, out: str | Path, total_duration: float) -> str:
    """Pad/truncate audio to exactly total_duration (trailing silence)."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    cur = probe_duration(src)
    if cur <= 0:
        return make_silence(out, total_duration)
    if abs(cur - total_duration) < 0.03:
        shutil.copy2(src, out); return str(out)
    if cur < total_duration:
        _run([ffmpeg_bin(), "-y", "-i", str(src),
              "-af", f"apad=whole_dur={total_duration:.3f}",
              "-t", f"{total_duration:.3f}", "-c:a", "libmp3lame", "-q:a", "4", str(out)])
    else:
        _run([ffmpeg_bin(), "-y", "-i", str(src), "-t", f"{total_duration:.3f}",
              "-c:a", "libmp3lame", "-q:a", "4", str(out)])
    return str(out)


def fit_reference(src: str | Path, out: str | Path, width: int, height: int) -> str:
    """Fit an image into a canvas without distorting it.

    FLUX 3's reference conditioning takes the output size from the reference
    image, so a portrait character sheet has to be brought to the delivery
    aspect first. The sides are filled with a blurred copy of the same image
    rather than black bars, which the model reads as "portrait on a soft
    background" instead of "letterboxed photo".
    """
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    fc = (f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
          f"crop={width}:{height},boxblur=24:2[b];"
          f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease[s];"
          f"[b][s]overlay=(W-w)/2:(H-h)/2")
    _run([ffmpeg_bin(), "-y", "-i", str(src), "-filter_complex", fc,
          "-frames:v", "1", str(out)], quiet=False)
    return str(out)


def mix_tracks(parts: Sequence[tuple[str | Path, float]], out: str | Path, *,
               duration: Optional[float] = None) -> str:
    """Mix several audio stems with individual gains into one track.

    Used to build the music stem: the H3 bed and the library BGM each have
    their own level, and the result sits under the dialogue as one unit.
    """
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    usable = [(p, g) for p, g in parts if p and Path(p).exists()]
    if not usable:
        return ""
    if len(usable) == 1:
        path, gain = usable[0]
        cmd = [ffmpeg_bin(), "-y", "-i", str(path)]
        af = f"volume={gain},aresample=44100"
        if duration:
            cmd += ["-t", f"{duration:.3f}"]
        cmd += ["-af", af, "-c:a", "libmp3lame", "-q:a", "3", str(out)]
        _run(cmd, quiet=False)
        return str(out)
    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    for i, (path, gain) in enumerate(usable):
        inputs += ["-i", str(path)]
        filters.append(f"[{i}:a]volume={gain},aresample=44100[a{i}]")
        labels.append(f"[a{i}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:dropout_transition=0[m]")
    cmd = [ffmpeg_bin(), "-y", *inputs, "-filter_complex", ";".join(filters),
           "-map", "[m]"]
    if duration:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += ["-c:a", "libmp3lame", "-q:a", "3", str(out)]
    _run(cmd, quiet=False)
    return str(out)


def momentary_lufs(path: str | Path, limit: int = 20000) -> list[float]:
    """EBU R128 momentary (400ms) loudness over time.

    The integrated loudness of a dialogue track is dragged down by the silences
    between the lines, so it cannot answer "can you hear the speech over the
    music". The momentary profile can: the loud windows are the speech, the
    quiet ones are the bed alone.
    """
    r = _run([ffmpeg_bin(), "-i", str(path), "-af",
              "ebur128=metadata=1,ametadata=mode=print:file=-",
              "-f", "null", "-"], quiet=True)
    import re
    vals = [float(x) for x in re.findall(r"lavfi\.r128\.M=(-?[\d.]+)", r.stdout)]
    return [v for v in vals if v > -120][:limit]


def _speech_level(path: str | Path) -> float:
    """Loudness of the speech itself: the median of the loud windows."""
    vals = sorted(momentary_lufs(path))
    if len(vals) < 20:
        return -60.0
    top = vals[int(len(vals) * 0.6):]
    return top[len(top) // 2]


def _bed_peak(path: str | Path) -> float:
    """The bed's loudest moments - that is what can mask a voice."""
    vals = sorted(momentary_lufs(path))
    if len(vals) < 20:
        return -60.0
    return vals[int(len(vals) * 0.9)]


def bed_gain_for(voice: str | Path, bed: str | Path,
                 target_gap_lu: float = 12.0) -> float:
    """The gain the music bed needs so the dialogue stays clear of it.

    How loud the bed should be depends on the episode: the H3 score has its own
    dynamics and the dialogue is not equally dense everywhere. Measuring the
    speech and the bed's loudest moments, and setting the gap, keeps every
    episode at the same balance.
    """
    speech = _speech_level(voice)
    peak = _bed_peak(bed)
    if speech <= -60 or peak <= -60:
        return 1.0
    import math
    gain_db = speech - target_gap_lu - peak
    return max(0.05, min(1.5, 10 ** (gain_db / 20.0)))


def mix_voice_bgm(voice: str | Path, bgm: Optional[str | Path], out: str | Path, *,
                  bgm_volume: float = 0.22, duck: bool = True,
                  target_lufs: Optional[float] = None) -> str:
    """Mix dialogue with background music (optional sidechain ducking) and
    optional EBU loudness normalization.

    The loudness is applied in two passes: the mix is measured first and then
    corrected with a linear gain, so the result actually lands on the target
    instead of near it.
    """
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    has_bgm = bool(bgm and Path(bgm).exists())
    if not has_bgm:
        _run([ffmpeg_bin(), "-y", "-i", str(voice),
              "-af", "aresample=44100", "-c:a", "libmp3lame", "-q:a", "3", str(out)],
             quiet=False)
        return str(out)
    if duck:
        fc = (f"[0:a]asplit=2[v][sc];"
              f"[1:a]volume={bgm_volume}[b];"
              f"[b][sc]sidechaincompress=threshold=0.05:ratio=9:attack=15:release=280[bg];"
              f"[v][bg]amix=inputs=2:duration=first:dropout_transition=0,"
              f"aresample=44100[a]")
    else:
        fc = (f"[1:a]volume={bgm_volume}[b];"
              f"[0:a][b]amix=inputs=2:duration=first:dropout_transition=0,"
              f"aresample=44100[a]")
    raw = out.with_suffix(".raw.mp3")
    _run([ffmpeg_bin(), "-y", "-i", str(voice), "-i", str(bgm),
          "-filter_complex", fc, "-map", "[a]",
          "-c:a", "libmp3lame", "-q:a", "3", str(raw)], quiet=False)
    if not target_lufs:
        raw.replace(out)
        return str(out)
    m = measure_loudness(raw)
    # the aac encode pushes the peaks up a little, so the normaliser leaves
    # more headroom than the target itself
    af = f"loudnorm=I={target_lufs}:TP=-2.2:LRA=11"
    if m.get("input_i"):
        af += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
               f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}")
        if m.get("target_offset"):
            af += f":offset={m['target_offset']}"
        af += ":linear=true"
    _run([ffmpeg_bin(), "-y", "-i", str(raw), "-af", af,
          "-c:a", "libmp3lame", "-q:a", "3", str(out)], quiet=False)
    raw.unlink(missing_ok=True)
    return str(out)


def measure_loudness(src: str | Path) -> dict:
    """Measure a track with EBU R128 (loudnorm's analysis pass).

    Returns the measured_* values loudnorm needs for a linear second pass.
    """
    r = _run([ffmpeg_bin(), "-i", str(src), "-af",
              "loudnorm=I=-24:TP=-2.0:LRA=11:print_format=json",
              "-f", "null", "-"], quiet=True)
    text = (r.stderr or "") + (r.stdout or "")
    start = text.rfind("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        return json.loads(text[start:end + 1])
    except Exception:  # noqa: BLE001
        return {}


def normalize_loudness(src: str | Path, out: str | Path, target_lufs: float = -24.0,
                        tp: float = -2.0, lra: float = 11.0,
                        sample_rate: int = 44100) -> str:
    """Bring one track to a target loudness using loudnorm's two-pass linear mode.

    The single-pass dynamic mode pumps and changes the character of the audio
    between shots; measuring first and applying a fixed gain does not.
    """
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    m = measure_loudness(src)
    af = (f"loudnorm=I={target_lufs}:TP={tp}:LRA={lra}")
    if m.get("input_i"):
        af += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
               f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}")
        if m.get("target_offset"):
            af += f":offset={m['target_offset']}"
        af += ":linear=true"
    af += f",aresample={sample_rate}"
    _run([ffmpeg_bin(), "-y", "-i", str(src), "-af", af,
          "-c:a", "libmp3lame", "-q:a", "3", str(out)], quiet=False)
    return str(out)


# --------------------------------------------------------------------------- #
# final mux / subtitles
# --------------------------------------------------------------------------- #
def _cjk_font() -> str:
    """A font file that can draw Chinese, for the AIGC label.

    ffmpeg's drawtext resolves fonts through fontconfig, which does not know
    the Windows font names, so the file has to be named explicitly.
    """
    import os
    for name in ("msyh.ttc", "simhei.ttf", "simsun.ttc", "msyhl.ttc"):
        p = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name
        if p.exists():
            return str(p).replace("\\", "/").replace(":", "\\:")
    return ""


def draw_title(src: str | Path, out: str | Path, title: str, *,
              width: int = 960, height: int = 544) -> str:
    """Put the title on the cover, big enough to read on a phone."""
    out = Path(out)
    font = _cjk_font()
    size = max(20, int(height * 0.11))
    # the title can be long: keep it on one line by shrinking it to fit
    while size > 16 and len(title) * size * 1.05 > width * 0.86:
        size -= 2
    text = (title.replace("\\", "\\\\").replace(":", "\\:")
            .replace("'", "").replace("%", "\\%"))
    vf = (f"drawtext=fontfile='{font}':text='{text}':fontcolor=white:"
          f"fontsize={size}:x=(w-text_w)/2:y=h-text_h-{int(height*0.06)}:"
          f"box=1:boxcolor=black@0.45:boxborderw={max(8, int(height*0.03))}")
    _run([ffmpeg_bin(), "-y", "-i", str(src), "-vf", vf, "-frames:v", "1", str(out)])
    return str(out)


def mux(video: str | Path, audio: str | Path, out: str | Path, *,
        video_bitrate: str = "6M", audio_bitrate: str = "192k",
        codec: str = "libx264", crf: int = 20, preset: str = "medium",
        pixel_format: str = "yuv420p", fps: Optional[int] = None,
        ass_file: Optional[str | Path] = None,
        watermark: str = "", watermark_size: int = 18,
        watermark_seconds: float = 0.0, grain: int = 0) -> str:
    """Mux picture + audio into the final mp4; optionally burn ASS subtitles.

    When burning, we chdir into the ASS file's directory and reference it by a
    bare filename to avoid Windows path-escaping issues in the filtergraph.
    Because of that chdir, all other paths are resolved to absolute first.

    The watermark is the AIGC label: since 2026 an AI drama has to say that
    it was made by AI, and the filing number goes on the picture too.
    """
    out = Path(out).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    video = Path(video).resolve()
    audio = Path(audio).resolve()
    vf: list[str] = []
    cwd: Optional[Path] = None
    if ass_file and Path(ass_file).exists():
        ass_path = Path(ass_file).resolve()
        cwd = ass_path.parent
        vf.append(f"subtitles={ass_path.name}")
    if watermark:
        text = watermark.replace("\\", "\\\\").replace(":", "\\:").replace("'", "")
        font = _cjk_font()
        label = (f"drawtext=fontfile='{font}':text='{text}':fontcolor=white@0.6:"
                 f"fontsize={watermark_size}"
                 f":x=24:y=20:box=1:boxcolor=black@0.35:boxborderw=6")
        if watermark_seconds and watermark_seconds > 0:
            # the platform asks for the label in the opening, not on every frame
            label += f":enable='between(t,0,{watermark_seconds:.1f})'"
        vf.append(label)
    if fps:
        vf.append(f"fps={fps}")
    if grain > 0:
        # a little grain takes the plastic look off an AI picture
        vf.append(f"noise=alls={int(grain)}:allf=t")
    cmd = [ffmpeg_bin(), "-y", "-i", str(video), "-i", str(audio),
           "-map", "0:v:0", "-map", "1:a:0"]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-c:v", codec]
    if codec == "libx264":
        cmd += ["-crf", str(crf), "-preset", preset]
    else:
        cmd += ["-b:v", video_bitrate]
    cmd += ["-pix_fmt", pixel_format, "-c:a", "aac", "-b:a", audio_bitrate,
            "-shortest", str(out)]
    _run(cmd, cwd=cwd, quiet=False)
    return str(out)


def extract_frame(video_or_image: str | Path, out: str | Path, at: float = 0.0,
                  width: Optional[int] = None) -> str:
    """Grab a single frame (for episode covers)."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale={width}:-1" if width else None
    cmd = [ffmpeg_bin(), "-y", "-ss", f"{at:.3f}", "-i", str(video_or_image),
           "-frames:v", "1"]
    if vf:
        cmd += ["-vf", vf]
    cmd += [str(out)]
    _run(cmd, quiet=False)
    return str(out)


def check_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
