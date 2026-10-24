"""Stage 9 — subtitle: build timed cues from the episode timeline, write SRT+ASS.

Runs after `voice` so line durations are real. Each cue spans its line's audio;
a minimum on-screen time is enforced so fast lines stay readable.
"""
from __future__ import annotations

from ..media.subtitle import write_ass, write_srt
from ..models import Status, SubtitleCue
from .base import Context, build_timeline

MIN_CUE = 0.8


def run(ctx: Context) -> dict:
    cc = ctx.cfg.compose
    total = 0
    for ep in ctx.target_episodes():
        if not ep.scenes:
            continue
        tl = build_timeline(ep)
        cues: list[SubtitleCue] = []
        for tsc in tl.scenes:
            for tl_line in tsc.lines:
                l = tl_line.line
                if not l.text.strip():
                    continue
                start = tl_line.start
                end = max(tl_line.end, start + MIN_CUE)
                cues.append(SubtitleCue(
                    start=round(start, 3), end=round(end, 3),
                    speaker=l.speaker if l.speaker not in ("旁白", "解说") else "",
                    text=l.text, kind=l.kind))
        cues.sort(key=lambda c: c.start)
        # avoid overlaps (clamp each cue to the next start)
        for i in range(len(cues) - 1):
            if cues[i].end > cues[i + 1].start:
                cues[i].end = max(MIN_CUE, cues[i + 1].start - 0.02)

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
