"""Stage 8 — voice: synthesize every line with the configured TTS provider.

Voice selection: explicit voice_map -> gender fallback -> narrator/default.
Each clip's measured duration is written back to the Line so the timeline and
subtitles stay in sync.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models import LineKind, Status
from ..providers.tts import resolve_voice
from .base import Context

NARRATORS = {"旁白", "解说", ""}


def _voice_for(ctx: Context, speaker: str, is_narration: bool) -> str:
    ch = ctx.project.character(speaker) if speaker else None
    gender = ch.gender if ch else "未知"
    return resolve_voice(ctx.cfg.tts, speaker, gender, is_narration)


def _synth_one(ctx: Context, line) -> tuple[str, bool, str]:
    out = ctx.store.audio_path(line.id)
    if line.status == Status.DONE and line.audio_path and out.exists():
        return line.id, True, "cached"
    try:
        is_narr = line.kind in (LineKind.NARRATION, LineKind.CAPTION) or line.speaker in NARRATORS
        voice = _voice_for(ctx, line.speaker, is_narr)
        emotion = ctx.cfg.tts.emotion_map.get(line.emotion, "")
        dur = ctx.providers.tts.synthesize(
            line.text, voice, str(out),
            rate=ctx.cfg.tts.rate, volume=ctx.cfg.tts.volume, pitch=ctx.cfg.tts.pitch,
            speed=ctx.cfg.tts.speed, emotion=emotion)
        line.audio_path = ctx.store.rel(out)
        line.duration = round(dur, 3)
        line.status = Status.DONE
        return line.id, True, ""
    except Exception as e:  # noqa: BLE001
        ctx.log.error("voice: 台词 %s 合成失败 %s", line.id, str(e)[:150])
        line.status = Status.FAILED
        return line.id, False, str(e)[:150]


def run(ctx: Context) -> dict:
    lines = []
    for ep in ctx.target_episodes():
        if ctx.stage_done(ep, "voice"):
            continue
        for sc in ep.scenes:
            for line in sc.lines:
                if line.status == Status.DONE and line.audio_path:
                    continue
                lines.append(line)

    if not lines:
        ctx.log.info("voice: 所有台词已合成")
        return {"lines": 0}

    ctx.log.info("voice: 合成 %d 句（provider=%s，并发=%d）",
                 len(lines), ctx.cfg.tts.provider, ctx.cfg.tts.concurrency)
    ok = 0
    with ThreadPoolExecutor(max_workers=max(1, ctx.cfg.tts.concurrency)) as ex:
        futs = [ex.submit(_synth_one, ctx, l) for l in lines]
        for i, fut in enumerate(as_completed(futs), 1):
            _id, good, _m = fut.result()
            ok += int(good)
            if i % 20 == 0 or i == len(lines):
                ctx.save()
                ctx.log.info("voice: %d/%d", i, len(lines))
    ctx.save()

    for ep in ctx.target_episodes():
        all_lines = [l for sc in ep.scenes for l in sc.lines]
        if all_lines and all(l.status == Status.DONE for l in all_lines):
            ctx.mark(ep, "voice", Status.DONE)
    ctx.save()
    return {"lines_ok": ok, "lines_total": len(lines)}
