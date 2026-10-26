"""Stage 9 — subtitle: build timed cues from the episode timeline, write SRT+ASS.

Runs after `voice` so line durations are real. Each cue spans its line's audio;
a minimum on-screen time is enforced so fast lines stay readable.
"""
from __future__ import annotations

from ..media.subtitle import write_ass, write_srt
from ..models import Status, SubtitleCue, is_narration
from .base import Context, build_timeline

MIN_CUE = 0.8


def run(ctx: Context) -> dict:
    cc = ctx.cfg.compose
    total = 0
    for ep in ctx.target_episodes():
        if not ep.scenes:
            continue
        tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds)
        cues: list[SubtitleCue] = []
        for tsc in tl.scenes:
            for tl_line in tsc.lines:
                l = tl_line.line
                if not l.text.strip():
                    continue
                start = tl_line.start
                end = max(tl_line.end, start + MIN_CUE)
                narr = is_narration(l)
                cues.append(SubtitleCue(
                    start=round(start, 3), end=round(end, 3),
                    speaker="" if narr else l.speaker,
                    text=l.text, kind=l.kind))
        cues.sort(key=lambda c: c.start)
        # Avoid overlaps, but only inside the same slot: narration cards are
        # allowed to sit on screen while dialogue plays (different area).
        # The readable minimum must never win over the cut - two subtitles on
        # screen at once is worse than a short one.
        for i in range(len(cues) - 1):
            cur, nxt = cues[i], cues[i + 1]
            if cur.kind != nxt.kind:
                continue
            if cur.end > nxt.start:
                cur.end = max(cur.start + 0.35, nxt.start - 0.02)

        srt = write_srt(cues, ctx.store.subtitle_path(ep, "srt"))
        ep.subtitle_path = ctx.store.rel(srt)
        if cc.burn_subtitles:
            ass = write_ass(cues, ctx.store.subtitle_path(ep, "ass"),
                            style=cc.subtitle_style, width=cc.width, height=cc.height,
                            show_speaker=cc.show_speaker_name)
            ep.ass_path = ctx.store.rel(ass)
        ctx.mark(ep, "subtitle", Status.DONE)
        ctx.save()
        total += len(cues)
    ctx.log.info("subtitle: 写出 %d 条字幕", total)
    return {"cues": total}
