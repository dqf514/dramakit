"""Stage 10 — music: produce a per-episode BGM track matching the dominant mood."""
from __future__ import annotations

from collections import Counter

from ..models import Status
from .base import Context, build_timeline, run_jobs, write_workers


def _dominant_mood(ep) -> str:
    moods = [ (sc.bgm_mood or sc.mood or "中性") for sc in ep.scenes ]
    moods = [m for m in moods if m]
    if not moods:
        return "中性"
    return Counter(moods).most_common(1)[0][0]


def run(ctx: Context) -> dict:
    mc = ctx.cfg.music
    if mc.provider == "none":
        ctx.log.info("music: provider=none，跳过")
        return {"skipped": True}
    if ctx.cfg.comfyui.native_audio and ctx.cfg.compose.native_audio_exclusive:
        # the sound came with the picture: H3's own voice, room and music.
        # A library track laid under it is one music too many.
        ctx.log.info("music: H3 原生音轨，跳过曲库 BGM")
        return {"skipped": True}
    music = ctx.providers.music
    made = 0
    jobs = []
    for ep in ctx.target_episodes():
        if ctx.stage_done(ep, "music"):
            continue
        if not ep.scenes:
            continue
        duration = ctx.timeline(ep).duration
        if duration <= 0:
            continue
        jobs.append((ep, duration))

    # one track per episode, and the episodes do not wait on each other
    def _one(job):
        ep, duration = job
        mood = _dominant_mood(ep)
        out = ctx.store.bgm_path(ep)
        try:
            return music.get_track(mood, duration + 1.0, str(out))
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("music: 第%d集 BGM 失败(%s)", ep.index, e)
            return None

    for (job, path, err) in run_jobs(ctx, jobs, _one, workers=write_workers(ctx),
                                     label="music"):
        ep, _duration = job
        if path:
            ep.bgm_path = ctx.store.rel(path)
            made += 1
        elif mc.provider == "library":
            ctx.log.warning(
                "music: 第%d集 没有曲库可用（%s 里没有匹配的曲子），"
                "成片的音乐将只来自 H3 原生音频",
                ep.index, mc.library_dir)
        ctx.mark(ep, "music", Status.DONE if path else Status.SKIPPED)
    ctx.save()
    ctx.log.info("music: 生成 %d 集 BGM", made)
    return {"tracks": made}
