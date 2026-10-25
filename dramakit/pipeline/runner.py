"""Pipeline runner: executes stages in order with resume / stop-after control."""
from __future__ import annotations

import logging
from typing import Callable, Optional

from ..config import Config
from ..models import Status
from ..project import ProjectStore
from ..providers import Providers
from . import (analyze, character, compose, ingest, music_stage, precheck, promptgen,
               qc, script, segment, storyboard, subtitle, visual, voice)
from .base import Context

log = logging.getLogger("dramakit.runner")

# canonical order
ORDER = ["ingest", "analyze", "character", "segment", "script", "storyboard",
         "promptgen", "visual", "voice", "subtitle", "music", "precheck",
         "compose", "qc"]


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
        "subtitle": subtitle.run,
        "music": music_stage.run,
        "precheck": precheck.run,
        "compose": compose.run,
        "qc": qc.run,
    }.get(name)


def run_pipeline(ctx: Context, source_file: Optional[str] = None,
                 stages: Optional[list[str]] = None) -> dict:
    cfg = ctx.cfg
    stages = stages or cfg.pipeline.stages_enabled
    # keep canonical order, only requested stages
    stages = [s for s in ORDER if s in stages]
    stop_after = cfg.pipeline.stop_after
    results: dict[str, dict] = {}

    for name in stages:
        if name not in cfg.pipeline.stages_enabled and stages == cfg.pipeline.stages_enabled:
            continue
        log.info("── 阶段 [%s] 开始 ──", name)
        ctx.project.stage_status[name] = Status.RUNNING
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
            ctx.save()
            log.info("── 阶段 [%s] 完成: %s ──", name, res)
        except Exception as e:  # noqa: BLE001
            ctx.project.stage_status[name] = Status.FAILED
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
    return results


def make_context(cfg: Config, store: ProjectStore,
                 providers: Optional[Providers] = None) -> Context:
    return Context(cfg, store, providers)
