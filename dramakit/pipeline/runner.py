"""Pipeline runner: executes stages in order with resume / stop-after control."""
from __future__ import annotations

import logging
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


def _complete_canon(ctx: Context, season_obj) -> None:
    """Close a season off into the canon.

    A season consumed some chapters and produced some episodes. Recording
    that is what lets the next season start at the right chapter, and what
    gives analyze a digest of the story so far instead of the whole book -
    which is the whole reason a million-word novel can be made a season at
    a time rather than never.
    """
    meta = ctx.project.meta
    # what this season actually turned into episodes, which is not always
    # what it was seeded with: a rerun that found nothing new still owns
    # what it already had.
    owned = sorted(e.index for e in ctx.project.episodes
                   if getattr(e, "season", 1) == season_obj.index)
    # the chapters this season laid down, if the marker was written
    season_ch = sorted({ch for ch, s in (meta.chapter_season or {}).items()
                        if s == season_obj.index} | set(season_obj.chapters or []))
    # A season's chapters are the story it told, whether or not it got as
    # far as cutting them into episodes. The canon records them here rather
    # than waiting for segment, so the next season knows where the story is
    # even when this one was closed early - continuity is not something a
    # later stage should have to grant.
    # The whole-project set is the history; season_ch is what this season
    # added, and it is the only part that is new.
    history = sorted(set(meta.segmented_chapters or []) | set(season_ch))
    complete_season(season_obj, chapters=season_ch,
                    done_chapters=history,
                    synopsis=season_obj.synopsis or "",
                    canon=ctx.project.canon)
    if owned:
        season_obj.episode_range = [owned[0], owned[-1]]
    ctx.save()


def run_pipeline(ctx: Context, source_file: Optional[str] = None,
                 stages: Optional[list[str]] = None,
                 season: Optional[int] = None) -> dict:
    cfg = ctx.cfg
    stages = stages or cfg.pipeline.stages_enabled
    # keep canonical order, only requested stages
    stages = [s for s in ORDER if s in stages]
    stop_after = cfg.pipeline.stop_after
    results: dict[str, dict] = {}

    # one season's chapters, one season's episodes, one season's looks.
    # Pointing the run at a season is what keeps a rerun of season 3 from
    # rewriting season 1's pictures, voices and timing.
    if season is not None:
        ctx.use_season(season)
        ctx.seed_season(list(ctx.project.meta.chosen_chapters or []))
    season_obj = ctx.season

    for name in stages:
        # Ask before starting anything new. A stage that was already asked
        # to stop raises inside its own loops; this is the other half, so
        # a stop between stages does not begin the next one.
        if ctx.stopped:
            log.info("── 已停止，未开始 [%s] ──", name)
            ctx.project.stage_status[name] = Status.INTERRUPTED
            if season_obj is not None:
                season_obj.stage_status[name] = Status.INTERRUPTED
            results[name] = {"interrupted": True}
            break
        if name not in cfg.pipeline.stages_enabled and stages == cfg.pipeline.stages_enabled:
            continue
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
                    continue
                res = fn(ctx) or {}
            results[name] = res
            ctx.project.stage_status[name] = Status.DONE
            if season_obj is not None:
                season_obj.stage_status[name] = Status.DONE
            ctx.save()
            log.info("── 阶段 [%s] 完成: %s ──", name, res)
        except RunStopped:
            # a refusal, not a fault: whatever the stage finished stays
            # finished, and the stage is marked interrupted so the next
            # run knows to begin here rather than at the start
            ctx.project.stage_status[name] = Status.INTERRUPTED
            if season_obj is not None:
                season_obj.stage_status[name] = Status.INTERRUPTED
            ctx.save()
            log.info("── 阶段 [%s] 已停止 ──", name)
            results[name] = {"interrupted": True}
            break
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
        if stop_after and name == stop_after:
            log.info("已在 [%s] 后停止（stop_after）", name)
            break

    # the season is finished when every stage it ran came out clean
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
    # this one stopped: the chapters it turned into episodes, and a digest
    # of the story so far, both go into the canon for analyze to inherit.
    # A season that failed is not closed - there is no "where it left off"
    # to carry forward when it did not get there.
    if season_obj is not None and season_obj.status == Status.DONE:
        _complete_canon(ctx, season_obj)
    return results


def make_context(cfg: Config, store: ProjectStore,
                 providers: Optional[Providers] = None) -> Context:
    return Context(cfg, store, providers)
