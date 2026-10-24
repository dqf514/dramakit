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
    `duration` by loop/trim, audio stripped (we add our own mix later)."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
          f"crop={width}:{height},fps={fps},format=yuv420p")
    cmd = [ffmpeg_bin(), "-y", "-stream_loop", "-1", "-i", str(src),
           "-t", f"{duration:.3f}", "-vf", vf, "-an",
           "-c:v", "libx264", "-crf", str(crf), "-preset", preset, str(out)]
    _run(cmd, quiet=False)
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


def mix_voice_bgm(voice: str | Path, bgm: Optional[str | Path], out: str | Path, *,
                  bgm_volume: float = 0.22, duck: bool = True,
                  target_lufs: Optional[float] = None) -> str:
    """Mix dialogue with background music (optional sidechain ducking) and
    optional EBU loudness normalization."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    has_bgm = bool(bgm and Path(bgm).exists())
    af_tail = f",loudnorm=I={target_lufs}:TP=-1.5:LRA=11" if target_lufs else ""
    if not has_bgm:
        _run([ffmpeg_bin(), "-y", "-i", str(voice),
              "-af", f"aresample=44100{af_tail}",
              "-c:a", "libmp3lame", "-q:a", "3", str(out)], quiet=False)
        return str(out)
    if duck:
        fc = (f"[0:a]asplit=2[v][sc];"
              f"[1:a]volume={bgm_volume}[b];"
              f"[b][sc]sidechaincompress=threshold=0.05:ratio=9:attack=15:release=280[bg];"
              f"[v][bg]amix=inputs=2:duration=first:dropout_transition=0,"
              f"aresample=44100{af_tail}[a]")
    else:
        fc = (f"[1:a]volume={bgm_volume}[b];"
              f"[0:a][b]amix=inputs=2:duration=first:dropout_transition=0,"
              f"aresample=44100{af_tail}[a]")
    _run([ffmpeg_bin(), "-y", "-i", str(voice), "-i", str(bgm),
          "-filter_complex", fc, "-map", "[a]",
          "-c:a", "libmp3lame", "-q:a", "3", str(out)], quiet=False)
    return str(out)


# --------------------------------------------------------------------------- #
# final mux / subtitles
# --------------------------------------------------------------------------- #
def mux(video: str | Path, audio: str | Path, out: str | Path, *,
        video_bitrate: str = "6M", audio_bitrate: str = "192k",
        codec: str = "libx264", crf: int = 20, preset: str = "medium",
        pixel_format: str = "yuv420p", fps: Optional[int] = None,
        ass_file: Optional[str | Path] = None) -> str:
    """Mux picture + audio into the final mp4; optionally burn ASS subtitles.

    When burning, we chdir into the ASS file's directory and reference it by a
    bare filename to avoid Windows path-escaping issues in the filtergraph.
    Because of that chdir, all other paths are resolved to absolute first.
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
    if fps:
        vf.append(f"fps={fps}")
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
