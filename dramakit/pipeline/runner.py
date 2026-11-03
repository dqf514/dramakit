"""Pipeline runner: the stages that can overlap, run together.

The stages were ordered one after another: every episode had to be
written before any of them could be drawn, and every one of those drawn
before any of them could be rendered. The machines are different - the
stills come from a local card, the clips from a remote one, the words from
a model on someone else's network entirely - so ordering them meant the
machine that renders sat at zero percent while the machine that wrote
finished a batch it did not have to finish first.

Now the run is in three parts. The stages that set everything up go first,
because nothing downstream can start without them. Then two lanes: the
one that writes - script, storyboard, prompts, voices, music - and the one
that draws and renders, which picks up a shot as soon as that shot's
prompts exist rather than when every prompt in the project does. Whatever
needs both lanes finished goes last.

The lanes share one project, so saving it takes turns: the lock is on the
write, not on the work, and the lanes still run at the same time.
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from ..config import Config
from ..models import Status
from ..project import ProjectStore
from ..providers import Providers
from ..seasons import complete_season
from . import (analyze, character, compose, ingest, lipsync, music_stage,
               precheck, promptgen, qc, script, segment, storyboard, subtitle,
               visual, voice)
from .base import Context, RunStopped

log = logging.getLogger("dramakit.runner")

# canonical order
# The voice comes before the picture: the shot lengths are derived from the
# dialogue, so the video has to be shot to the timing of the finished lines
# rather than to an estimate of them.
ORDER = ["ingest", "analyze", "character", "segment", "script", "storyboard",
         "promptgen", "voice", "visual", "lipsync", "subtitle", "music",
         "precheck", "compose", "qc"]

# What runs first, what can overlap, and what has to wait. The middle is
# split by machine: the writing stages need a model, the picture stage
# needs a card, and neither has to finish before the other begins.
SETUP = ("ingest", "analyze", "character", "segment")
WRITES = ("script", "storyboard", "promptgen", "voice", "music")
DRAWS = ("visual",)
TAIL = ("lipsync", "subtitle", "precheck", "compose", "qc")


def _stage_fn(name: str) -> Optional[Callable]:
    return {
        "ingest": None,  # handled specially (needs source_file)
        "analyze": analyze.run,
        "character": character.run,
        "segment": segment.run,
        "script": script.run,
        "storyboard": storyboard.run,
        "promptgen": promptgen.run,
        "visual": visual.run,
        "voice": voice.run,
        "lipsync": lipsync.run,
        "subtitle": subtitle.run,
        "music": music_stage.run,
        "precheck": precheck.run,
        "compose": compose.run,
        "qc": qc.run,
    }.get(name)


def _run_stage(ctx: Context, name: str, source_file: Optional[str],
               season_obj, results: dict, cfg: Config) -> None:
    """Run one stage, recording what it did the way the run has always done.

    A refusal is not a failure: RunStopped leaves whatever the stage
    finished where it is and marks the stage interrupted, so the next run
    knows to begin there rather than at the start.
    """
    log.info("── 阶段 [%s] 开始 ──", name)
    ctx.project.stage_status[name] = Status.RUNNING
    if season_obj is not None:
        season_obj.stage_status[name] = Status.RUNNING
    ctx.save()
    try:
        if name == "ingest":
            res = ingest.run(ctx, source_file)
        else:
            fn = _stage_fn(name)
            if fn is None:
                return
            res = fn(ctx) or {}
        results[name] = res
        ctx.project.stage_status[name] = Status.DONE
        if season_obj is not None:
            season_obj.stage_status[name] = Status.DONE
        ctx.save()
        log.info("── 阶段 [%s] 完成: %s ──", name, res)
    except RunStopped:
        ctx.project.stage_status[name] = Status.INTERRUPTED
        if season_obj is not None:
            season_obj.stage_status[name] = Status.INTERRUPTED
        ctx.save()
        log.info("── 阶段 [%s] 已停止 ──", name)
        results[name] = {"interrupted": True}
        raise
    except Exception as e:  # noqa: BLE001
        ctx.project.stage_status[name] = Status.FAILED
        if season_obj is not None:
            season_obj.stage_status[name] = Status.FAILED
        ctx.save()
        log.error("阶段 [%s] 失败: %s", name, e)
        if cfg.pipeline.fail_fast:
            raise
        results[name] = {"error": str(e)[:300]}
        # compose/visual can be skipped without killing everything else
        if name in ("analyze", "segment"):
            raise  # these are foundational; can't continue


def _complete_canon(ctx: Context, season_obj) -> None:
    """Close a season off into the canon.

    A season consumed some chapters and produced some episodes. Recording
    that is what lets the next season start at the right chapter, and what
    gives analyze a digest of the story so far instead of the whole book -
    which is the whole reason a million-word novel can be made a season at
    a time rather than never.
    """
    meta = ctx.project.meta
    owned = sorted(e.index for e in ctx.project.episodes
                   if getattr(e, "season", 1) == season_obj.index)
    season_ch = sorted({ch for ch, s in (meta.chapter_season or {}).items()
                        if s == season_obj.index} | set(season_obj.chapters or []))
    history = sorted(set(meta.segmented_chapters or []) | set(season_ch))
    complete_season(season_obj, chapters=season_ch,
                    done_chapters=history,
                    synopsis=season_obj.synopsis or "",
                    canon=ctx.project.canon)
    if owned:
        season_obj.episode_range = [owned[0], owned[-1]]
    ctx.save()


def _draw_until_done(ctx: Context, writes_done: threading.Event,
                     results: dict, cfg: Config) -> None:
    """Render whatever has its prompts, for as long as there is any.

    The picture stage used to start only after every prompt in the project
    existed, which put the card at zero percent for hours while a model on
    someone else's network finished sentences for episodes nobody was
    drawing yet. It now runs as the prompts arrive: a shot is rendered when
    that shot is ready, not when the project is.

    It loops rather than runs once, because the set of ready shots grows
    while it works. When the stage reports nothing to do, that means
    either everything is drawn or nothing is ready yet - so it waits for
    the writers, and only stops when they have finished as well. Stopping
    at the first empty pass would leave the shots that landed in between
    unrendered.

    The status is written here rather than by _run_stage, because this
    lane calls the stage itself: without it the project never records that
    visual ran or finished, and a resume - which reads the statuses to
    decide what is still owed - is left believing the stage was never
    asked for.
    """
    season = ctx.season
    ctx.project.stage_status["visual"] = Status.RUNNING
    if season is not None:
        season.stage_status["visual"] = Status.RUNNING
    ctx.save()

    def _mark(status) -> None:
        ctx.project.stage_status["visual"] = status
        if season is not None:
            season.stage_status["visual"] = status
        ctx.save()

    passes = 0
    try:
        while True:
            if ctx.stopped:
                raise RunStopped()
            res = visual.run(ctx) or {}
            passes += 1
            if res.get("shots"):
                # work was done: there may be more waiting behind it
                results["visual"] = res
                continue
            if writes_done.is_set():
                results["visual"] = res
                _mark(Status.DONE)
                log.info("── 阶段 [visual] 完成（%d 趟）: %s ──", passes, res)
                return
            # nothing ready and the writers are still going: wait rather than
            # spin, then look again
            results["visual"] = res
            writes_done.wait(5)
    except RunStopped:
        _mark(Status.INTERRUPTED)
        raise
    except Exception:
        _mark(Status.FAILED)
        raise


def run_pipeline(ctx: Context, source_file: Optional[str] = None,
                 stages: Optional[list[str]] = None,
                 season: Optional[int] = None) -> dict:
    cfg = ctx.cfg
    stages = stages or cfg.pipeline.stages_enabled
    stages = [s for s in ORDER if s in stages]
    stop_after = cfg.pipeline.stop_after
    results: dict[str, dict] = {}

    # one season's chapters, one season's episodes, one season's looks.
    if season is not None:
        ctx.use_season(season)
        ctx.seed_season(list(ctx.project.meta.chosen_chapters or []))
    season_obj = ctx.season

    def _wanted(group: tuple[str, ...]) -> list[str]:
        return [s for s in stages if s in group]

    def _stop_if_wanted(name: str) -> bool:
        if stop_after and name == stop_after:
            log.info("已在 [%s] 后停止（stop_after）", name)
            return True
        return False

    try:
        # ---- the stages that set everything else up ----------------------
        for name in _wanted(SETUP):
            if (name not in cfg.pipeline.stages_enabled
                    and stages == cfg.pipeline.stages_enabled):
                continue
            if ctx.stopped:
                break
            _run_stage(ctx, name, source_file, season_obj, results, cfg)
            if _stop_if_wanted(name):
                return _finish(ctx, season_obj, stages, results)

        writes = _wanted(WRITES)
        draws = _wanted(DRAWS)

        # ---- the two lanes that do not have to wait for each other -------
        if writes and draws:
            log.info("── 两道并行：写作 %s / 绘制 %s ──", writes, draws)
            writes_done = threading.Event()

            def _write_lane():
                try:
                    for name in writes:
                        if ctx.stopped:
                            break
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if _stop_if_wanted(name):
                            break
                finally:
                    # the drawer's last pass is gated on this, so it has to
                    # be set even when the lane failed or was stopped
                    writes_done.set()

            with ThreadPoolExecutor(max_workers=2) as pool:
                wfut = pool.submit(_write_lane)
                dfut = pool.submit(_draw_until_done, ctx, writes_done,
                                   results, cfg)
                wfut.result()
                dfut.result()
            if ctx.stopped:
                return _finish(ctx, season_obj, stages, results)
        else:
            for name in writes + draws:
                if ctx.stopped:
                    break
                _run_stage(ctx, name, None, season_obj, results, cfg)
                if _stop_if_wanted(name):
                    return _finish(ctx, season_obj, stages, results)

        # ---- what needs both lanes finished -------------------------------
        for name in _wanted(TAIL):
            if ctx.stopped:
                break
            _run_stage(ctx, name, None, season_obj, results, cfg)
            if _stop_if_wanted(name):
                break
    except RunStopped:
        log.info("── 已停止 ──")

    return _finish(ctx, season_obj, stages, results)


def _finish(ctx: Context, season_obj, stages: list[str],
            results: dict) -> dict:
    """Close the run off: season status, and the canon if it went the distance."""
    if season_obj is not None:
        vals = [season_obj.stage_status.get(n) for n in stages
                if n in season_obj.stage_status]
        if any(v == Status.INTERRUPTED for v in vals):
            season_obj.status = Status.INTERRUPTED
        else:
            done = all(v == Status.DONE for v in vals)
            season_obj.status = Status.DONE if done else Status.FAILED
        ctx.save()
    # Closing a season off is what makes the next one able to start where
    # this one stopped. A season that failed or was stopped is not closed:
    # there is no "where it left off" to carry forward.
    if season_obj is not None and season_obj.status == Status.DONE:
        _complete_canon(ctx, season_obj)
    return results


def make_context(cfg: Config, store: ProjectStore,
                 providers: Optional[Providers] = None) -> Context:
    return Context(cfg, store, providers)
