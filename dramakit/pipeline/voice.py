"""Stage 8 — voice: synthesize every line with the configured TTS provider.

Voice selection: character.voice_id (auto-cast) -> voice_map -> gender fallback
-> narrator/default. Each clip's measured duration is written back to the Line
so the timeline and subtitles stay in sync.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models import LineKind, Status, is_narration
from ..providers.tts import resolve_voice
from .base import Context

NARRATORS = {"旁白", "解说", ""}


def _voice_shaping(ctx: Context, speaker: str) -> tuple[str, str]:
    """Per-character pitch/rate so age reads even when voices are reused.

    The voice design (pitch/rate) is decided with the character sheet, so it
    wins; the age heuristic is only a fallback for characters that were
    designed before the voice design existed.
    """
    ch = ctx.project.character(speaker) if speaker else None
    if ch is None:
        return "", ""
    if ch.voice_pitch or ch.voice_rate:
        return ch.voice_pitch, ch.voice_rate
    age = (ch.age or "").strip()
    if not age:
        return "", ""
    m = re.search(r"(\d+)", age)
    if m:
        years = int(m.group(1))
        if years >= 55:
            return "-14Hz", "-8%"
        if years >= 38:
            return "-6Hz", "-3%"
        if years <= 16:
            return "+10Hz", "+0%"
        return "", ""
    if any(k in age for k in ("老年", "中老年", "老人", "长者")):
        return "-12Hz", "-6%"
    if any(k in age for k in ("少年", "少女", "孩子", "幼年")):
        return "+10Hz", "+0%"
    return "", ""


def _voice_for(ctx: Context, speaker: str, is_narration: bool) -> str:
    ch = ctx.project.character(speaker) if speaker else None
    if ch is not None and ch.voice_id and not is_narration:
        return ch.voice_id
    gender = ch.gender if ch else "未知"
    return resolve_voice(ctx.cfg.tts, speaker, gender, is_narration)


def _synth_one(ctx: Context, line) -> tuple[str, bool, str]:
    out = ctx.store.audio_path(line.id)
    if line.status == Status.DONE and line.audio_path and out.exists():
        return line.id, True, "cached"
    try:
        is_narr = is_narration(line)
        # Narration is a screen-only card by default: no voice, no audio track.
        if is_narr and not ctx.cfg.tts.speak_narration:
            line.audio_path = ""
            line.duration = 0.0
            line.status = Status.SKIPPED
            return line.id, True, "narration"
        voice = _voice_for(ctx, line.speaker, is_narr)
        emotion = ctx.cfg.tts.emotion_map.get(line.emotion, "")
        pitch, rate = _voice_shaping(ctx, line.speaker)
        dur = ctx.providers.tts.synthesize(
            line.text, voice, str(out),
            rate=rate or ctx.cfg.tts.rate, volume=ctx.cfg.tts.volume,
            pitch=pitch or ctx.cfg.tts.pitch,
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
                if line.status == Status.SKIPPED:
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
        # narration lines are intentionally skipped -> not a failure
        if all_lines and all(l.status in (Status.DONE, Status.SKIPPED) for l in all_lines):
            ctx.mark(ep, "voice", Status.DONE)
    ctx.save()
    return {"lines_ok": ok, "lines_total": len(lines)}
