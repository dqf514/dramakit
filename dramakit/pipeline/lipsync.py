"""Stage: put the recorded words on the lips that are on screen.

The picture is generated from a prompt, so the mouths move to the model's
own idea of the sentence. The words are recorded separately, so the voice
and the lips do not have to agree - and the viewer hears it as the sound
coming from outside the picture.

MuseTalk takes the finished clip and the recorded line and redraws the
mouth, so the face says what is actually being said. It runs on the shots
that carry a line, before the cut.
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

from ..models import Status
from .base import Context

SR = 16000          # what MuseTalk's audio features expect


def _pcm(path: Path) -> bytes:
    """One wav file as raw 16 bit mono at 16 kHz."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-acodec",
         "pcm_s16le", "-ar", str(SR), "-ac", "1", "-"],
        capture_output=True)
    return r.stdout


def _scene_wav(lines, start: float, total: float, out: Path) -> bool:
    """The scene's voice, from the shot's own start, as one wav.

    The silence in front of the first line matters: the lips have to start
    moving when the voice starts, not when the shot does.
    """
    buf = bytearray(int(total * SR) * 2)
    placed = False
    for rel, path in lines:
        if not path or not Path(path).exists():
            continue
        pcm = _pcm(Path(path))
        # where the line falls inside the clip
        at = int(max(0.0, rel - start) * SR) * 2
        end = at + len(pcm)
        if end > len(buf):
            pcm = pcm[:len(buf) - at]
            end = len(buf)
        buf[at:end] = pcm
        placed = True
    if not placed:
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(buf))
    return True


def _musetalk(ctx: Context, jobs: list[tuple[Path, Path, Path]]) -> dict[Path, bool]:
    """The clips through MuseTalk, one model load for all of them."""
    root = Path(ctx.cfg.compose.musetalk_root or r"E:\musetalk")
    py = ctx.cfg.compose.musetalk_python or r"E:\ComfyUI\venv\Scripts\python.exe"
    if not root.exists() or not Path(py).exists():
        ctx.log.warning("lipsync: 找不到 MuseTalk（%s），跳过", root)
        return {out: False for _, _, out in jobs}
    work = root / "results" / "dramakit"
    work.mkdir(parents=True, exist_ok=True)
    cfg = work / "task.yaml"
    parts = []
    for i, (video, wav, out) in enumerate(jobs):
        parts.append(f"task_{i}:\n  video_path: \"{video.as_posix()}\"\n"
                     f"  audio_path: \"{wav.as_posix()}\"\n"
                     f"  result_name: \"{out.name}\"\n")
    cfg.write_text("\n".join(parts), encoding="utf-8")
    # MuseTalk has to be run as a module: its own imports are relative to the
    # repository, and running the file directly puts the scripts folder on the
    # path instead of the repository
    cmd = [py, "-m", "scripts.inference",
           "--inference_config", str(cfg),
           "--result_dir", str(work),
           "--unet_config", str(root / "models" / "musetalkV15" / "musetalk.json"),
           "--unet_model_path", str(root / "models" / "musetalkV15" / "unet.pth"),
           "--whisper_dir", str(root / "models" / "whisper"),
           "--version", "v15", "--use_float16"]
    try:
        r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                           errors="replace",
                           timeout=float(ctx.cfg.compose.lipsync_timeout))
    except subprocess.TimeoutExpired:
        ctx.log.warning("lipsync: 超时")
        return {out: False for _, _, out in jobs}
    ok: dict[Path, bool] = {}
    for video, wav, out in jobs:
        produced = work / "v15" / out.name
        if produced.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            produced.replace(out)
            ok[out] = True
        else:
            ok[out] = False
    if not all(ok.values()):
        tail = (r.stderr or r.stdout or "")[-400:].replace("\n", " ")
        ctx.log.warning("lipsync: 有一部分失败 %s", tail)
    return ok


def run(ctx: Context) -> dict:
    cfg = ctx.cfg.compose
    if not cfg.lipsync:
        return {"skipped": True}
    if ctx.cfg.comfyui.native_audio:
        # the mouth already moves with the voice the model generated; a
        # second pass would put the lips out of step with the sound
        ctx.log.info("lipsync: 跳过（画面里的人声是 H3 自己说的，嘴本来就对上了）")
        return {"skipped": True}
    done = 0
    failed = 0
    for ep in ctx.target_episodes():
        if ctx.stage_done(ep, "lipsync"):
            continue
        tl = ctx.timeline(ep)
        jobs: list[tuple[Path, Path, Path]] = []
        keep: list[tuple[Path, Path]] = []
        for tsc in tl.scenes:
            for ts in tsc.shots:
                shot = ts.shot
                if not shot.video_path:
                    continue
                video = ctx.store.abs(shot.video_path)
                if not video.exists():
                    continue
                # the lines inside this shot, in scene-relative time
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
                    continue
                dur = ff_duration(video) or ts.duration
                wav = video.parent / f"{shot.id}_line.wav"
                if not _scene_wav(placed, ts.start - tsc.start, dur, wav):
                    continue
                out = video.parent.parent / "lipsync" / f"{shot.id}.mp4"
                jobs.append((video, wav, out))
                keep.append((shot, out))
        if jobs:
            results = _musetalk(ctx, jobs)
            for shot, out in keep:
                if results.get(out):
                    shot.video_path = ctx.store.rel(out)
                    done += 1
                else:
                    failed += 1
        for _, wav, _ in jobs:
            wav.unlink(missing_ok=True)
        ctx.mark(ep, "lipsync", Status.DONE)
    ctx.save()
    ctx.log.info("lipsync: 对齐了 %d 个镜头（失败 %d）", done, failed)
    return {"lipsynced": done, "failed": failed}


def ff_duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, errors="replace")
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0
