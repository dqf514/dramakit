"""Stage 8 — voice: synthesize every line with the configured TTS provider.

Voice selection: character.voice_id (auto-cast) -> voice_map -> gender fallback
-> narrator/default. Each clip's measured duration is written back to the Line
so the timeline and subtitles stay in sync.
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models import LineKind, Status, is_narration
from ..providers.tts import resolve_voice
from .base import Context

NARRATORS = {"旁白", "解说", ""}


def _emotion_key(cfg, emotion: str) -> str:
    """Find the emotion the map knows for a label the script invented.

    The script writes labels like "冷笑（愤怒）" or "犹豫（心虚）"; only the
    plain part is in the map. A label that is not in the map at all means the
    line is read out with no emotion and no modulation - flat, which is the
    one thing a short drama cannot afford.
    """
    emap = cfg.tts.emotion_map or {}
    fallback = "平静" if "平静" in emap else (next(iter(emap), "") if emap else "")
    if not emotion:
        return fallback
    if emotion in emap:
        return emotion
    # the part in brackets carries the real emotion
    m = re.search(r"[（(]([^）)]+)[）)]", emotion)
    inner = m.group(1).strip() if m else ""
    for cand in (inner, re.split(r"[（(]", emotion)[0].strip()):
        if not cand:
            continue
        if cand in emap:
            return cand
        for k in emap:
            if k and k in cand:
                return k
    # last resort: a known emotion word anywhere in the label
    for k in emap:
        if k and k in emotion:
            return k
    return fallback


def _apply_emotion(ctx: Context, emotion: str, *, speed: float,
                   pitch: str, rate: str) -> tuple[float, str, str]:
    """Bend the delivery to the line's emotion.

    A short drama lives on tension: anger has to push, grief has to drop.
    Providers with a real emotion parameter get that too; the speed and pitch
    nudge is what makes the line read even without one.
    """
    mod = (ctx.cfg.tts.emotion_modulation or {}).get(_emotion_key(ctx.cfg, emotion), {})
    if not mod:
        return speed, pitch, rate
    speed = max(0.5, min(2.0, speed * float(mod.get("speed", 1.0))))
    half = int(mod.get("pitch", 0))
    if half:
        pitch = _shift_hz(pitch, half)
        rate = _shift_rate(rate, mod.get("rate", 0))
    return speed, pitch, rate


def _shift_hz(pitch: str, half_tones: int) -> str:
    """Move an edge-style '+3Hz' pitch by a number of semitones."""
    m = re.match(r"\s*([+-]?\d+)\s*Hz", pitch or "")
    hz = int(m.group(1)) if m else 0
    # roughly a semitone every 8 Hz for a speaking voice
    return f"{hz + half_tones * 8:+d}Hz"


def _shift_rate(rate: str, percent: int) -> str:
    if not percent:
        return rate
    m = re.match(r"\s*([+-]?\d+)\s*%", rate or "")
    pct = int(m.group(1)) if m else 0
    return f"{pct + percent:+d}%"


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
    voice = resolve_voice(ctx.cfg.tts, speaker, gender, is_narration)
    if voice and voice not in ("default", ctx.cfg.tts.model):
        return voice
    # the character has no voice yet (or the config gave a placeholder):
    # fall back to something the provider actually has
    return _any_voice(ctx, gender)


def _any_voice(ctx: Context, gender: str) -> str:
    """A usable voice id from the provider, by gender if we can tell."""
    try:
        voices = ctx.providers.tts.list_voices()
    except Exception:  # noqa: BLE001
        voices = []
    if not voices:
        return ""
    if gender in ("女", "female"):
        pref = [v for v in voices if v.startswith("female-")] or \
               [v for v in voices if "female" in v.lower()]
        if pref:
            return pref[0]
    if gender in ("男", "male"):
        pref = [v for v in voices if v.startswith("male-")] or \
               [v for v in voices if "male" in v.lower()]
        if pref:
            return pref[0]
    return voices[0]


def _synth_one(ctx: Context, line, tries: int = 3) -> tuple[str, bool, str]:
    out = ctx.store.audio_path(line.id)
    if line.status == Status.DONE and line.audio_path and out.exists():
        return line.id, True, "cached"
    is_narr = is_narration(line)
    # Narration is a screen-only card by default: no voice, no audio track.
    if is_narr and not ctx.cfg.tts.speak_narration:
        line.audio_path = ""
        line.duration = 0.0
        line.status = Status.SKIPPED
        return line.id, True, "narration"
    voice = _voice_for(ctx, line.speaker, is_narr)
    emotion = ctx.cfg.tts.emotion_map.get(_emotion_key(ctx.cfg, line.emotion), "")
    pitch, rate = _voice_shaping(ctx, line.speaker)
    speed, pitch, rate = _apply_emotion(ctx, line.emotion, speed=ctx.cfg.tts.speed,
                                        pitch=pitch, rate=rate)
    # A single line can fail for a reason that has nothing to do with the line
    # - a locked file on Windows, a hiccup in the network. That took a whole
    # episode down once, so every line gets a few attempts.
    last = ""
    for attempt in range(1, tries + 1):
        try:
            dur = ctx.providers.tts.synthesize(
                line.text, voice, str(out),
                rate=rate or ctx.cfg.tts.rate, volume=ctx.cfg.tts.volume,
                pitch=pitch or ctx.cfg.tts.pitch,
                speed=speed, emotion=emotion)
            line.audio_path = ctx.store.rel(out)
            line.duration = round(dur, 3)
            line.status = Status.DONE
            return line.id, True, ""
        except Exception as e:  # noqa: BLE001
            last = str(e)[:150]
            ctx.log.warning("voice: 台词 %s 第 %d 次合成失败 %s",
                            line.id, attempt, last)
            if attempt < tries:
                time.sleep(2.0 * attempt)
    ctx.log.error("voice: 台词 %s 合成失败 %s", line.id, last)
    line.status = Status.FAILED
    return line.id, False, last


def run(ctx: Context) -> dict:
    # casting belongs with the voice stage: a character without a voice would
    # otherwise fall through to the same default for everyone
    if ctx.cfg.characters.auto_cast:
        from .character import cast_voices
        cast_voices(ctx, list(ctx.project.characters))
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
        else:
            # leave it unfinished so the next run retries instead of treating
            # a half-silent episode as done
            ctx.mark(ep, "voice", Status.FAILED)
    ctx.save()
    if ok < len(lines):
        raise RuntimeError(f"voice: {len(lines) - ok}/{len(lines)} 句合成失败")
    return {"lines_ok": ok, "lines_total": len(lines)}
