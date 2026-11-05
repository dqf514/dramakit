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
prompts exist rather than when every prompt in the project does. A third
lane puts each episode together as soon as its own shots are done, so
the first episode can be watched while the last one is still being
drawn. Whatever needs both lanes finished goes last.

The lanes share one project, so saving it takes turns: the lock is on the
write, not on the work, and the lanes still run at the same time. And
before any of them writes, it takes in what the others have finished -
so a lane that is drawing and a lane that is putting a film together
can write the same file without losing each other's work.
"""
from __future__ import annotations

import json
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
from . import (analyze, character, compose, cover, ingest, lipsync, music_stage,
               precheck, promptgen, qc, script, segment, storyboard, subtitle,
               visual, voice)
from .base import Context, RunStopped

log = logging.getLogger("dramakit.runner")

# canonical order
# The voice comes before the picture: the shot lengths are derived from the
# dialogue, so the video has to be shot to the timing of the finished lines
# rather than to an estimate of them.
ORDER = ["ingest", "analyze", "cover", "character", "segment", "script",
         "storyboard", "promptgen", "voice", "visual", "lipsync", "subtitle",
         "music", "precheck", "compose", "qc"]

# What runs first, what can overlap, and what has to wait. The middle is
# split by machine: the writing stages need a model, the picture stage
# needs a card, and neither has to finish before the other begins.
SETUP = ("ingest", "analyze", "cover")
# The casting is the heaviest thing on the card - four reference pictures
# for every character and a voice sample each - and the writing only
# needs the names and the text of the cast.  So the casting runs beside
# the writing instead of in front of it, and the one stage that waits
# for it is the prompt writer, which puts the anchors into the prompts.
CASTING = ("character",)
WRITES = ("segment", "script", "storyboard", "promptgen", "voice", "music")
# The stages that only need the script: the voice and the music do not
# wait for the storyboard, so they are made beside it.
SIDE_WRITES = ("voice", "music")
DRAWS = ("visual",)
TAIL = ("lipsync", "subtitle", "precheck", "compose", "qc")



def _lane(ctx, lane: str, stage: str) -> None:
    """Say which stage a lane is working on, for the console."""
    try:
        from . import progress as _progress
        prog = _progress.attach(ctx)
        if stage:
            prog.lane(lane, stage)
        else:
            prog.lane_done(lane)
    except Exception:  # noqa: BLE001
        pass


def _stage_fn(name: str) -> Optional[Callable]:
    return {
        "ingest": None,  # handled specially (needs source_file)
        "analyze": analyze.run,
        "cover": cover.run,
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
               season_obj, results: dict, cfg: Config):
    """Run one stage, recording what it did the way the run has always done.

    A refusal is not a failure: RunStopped leaves whatever the stage
    finished where it is and marks the stage interrupted, so the next run
    knows to begin there rather than at the start.

    Returns the season, which may be new: a stage that cuts the chapters
    into episodes is the one that makes the season, and the stages that
    follow need to write their status on it.
    """
    log.info("── 阶段 [%s] 开始 ──", name)
    ctx.project.stage_status[name] = Status.RUNNING
    if season_obj is not None:
        season_obj.stage_status[name] = Status.RUNNING
    ctx.save()
    if name not in ("ingest", "analyze", "character", "segment"):
        # A stage that is given nothing says so and finishes in a second,
        # which reads like success.  The reason is almost always the
        # filter: the run was asked for a set of episodes that this
        # project does not have.
        if not ctx.target_episodes():
            log.warning("阶段 [%s]：这一轮没有要处理的集"
                        "（只处理=%s，季=%s，项目现有 %d 集）",
                        name, cfg.pipeline.only_episodes, ctx.season_index,
                        len(ctx.project.episodes))
    try:
        if name == "ingest":
            res = ingest.run(ctx, source_file)
        else:
            fn = _stage_fn(name)
            if fn is None:
                return season_obj
            res = fn(ctx) or {}
        # A stage that creates the season - cutting the chapters into
        # episodes does - leaves it here for the stages that follow.
        if season_obj is None:
            season_obj = ctx.season
        results[name] = _merge_results(results.get(name), res)
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
    return season_obj


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


def _episode_ready(ctx: Context, ep) -> bool:
    """Is every shot of this episode drawn?

    The film is put together from the shots, so an episode can be made
    when its shots are all there - it does not wait for the episodes
    that come after it.
    """
    shots = [sh for sc in ep.scenes for sh in sc.shots]
    if not shots:
        return False
    return all(getattr(sh, "video_path", "") for sh in shots)


def _episode_made(ep) -> bool:
    """Has this episode already been put together?"""
    if not getattr(ep, "video_path", ""):
        return False
    return (ep.stage_status or {}).get("compose") == Status.DONE


def _merge_results(prev, new):
    """Add up the counts of two runs of the same stage.

    A stage can run twice: once by the lane that puts an episode
    together as it becomes ready, and once by the tail at the end of the
    run. The report should say what was done in total, not what the last
    one did - otherwise a run that made a film says it made nothing.
    """
    if not isinstance(prev, dict) or not isinstance(new, dict):
        return new
    out = dict(prev)
    for k, v in new.items():
        old = out.get(k)
        if (isinstance(v, (int, float)) and not isinstance(v, bool)
                and isinstance(old, (int, float)) and not isinstance(old, bool)):
            out[k] = old + v
        else:
            out[k] = v
    return out


def _finish_one(ctx: Context, cfg: Config, ep_index: int,
                results: dict, lock: threading.Lock, tail: list[str]) -> dict:
    """Put one episode together, in a context of its own.

    The stages take a context and work on the episodes that context
    points at. The run's own context points at every episode, and the
    run is drawing them, so the episode being finished gets a context of
    its own with a copy of the settings that names only it.

    What the two write is the same file, and the file is written whole
    each time - so before either of them writes, it takes in what the
    other has finished. That is what makes this safe to do while the
    cards are still working.

    Returns what was made, so the run's own copy of the episode knows
    about it too - otherwise the run would put the same episode together
    again the moment it looks.
    """
    from .base import Context
    own_cfg = cfg.model_copy(deep=True)
    own_cfg.pipeline.only_episodes = [ep_index]
    # the run's own providers: they are the clients that answer, and
    # building a second set would go and look at the cards all over
    # again for nothing
    own_ctx = Context(own_cfg, ctx.store, ctx.providers)
    if getattr(ctx, "_stop", None) is not None:
        own_ctx.bind_stop(ctx._stop)
    for name in tail:
        fn = _stage_fn(name)
        if fn is None:
            continue
        try:
            res = fn(own_ctx) or {}
        except Exception as e:  # noqa: BLE001
            log.error("第%d集 %s 失败: %s", ep_index, name, str(e)[:200])
            continue
        with lock:
            results[name] = _merge_results(results.get(name), res)
        log.info("第%d集 %s 完成: %s", ep_index, name,
                 json.dumps(res, ensure_ascii=False)[:160])
    own_ep = own_ctx.project.episode(ep_index)
    if own_ep is None:
        return {}
    return {"video_path": own_ep.video_path,
            "subtitle_path": own_ep.subtitle_path,
            "status": own_ep.status,
            "stage_status": dict(own_ep.stage_status or {}),
            "qc_report": own_ep.qc_report,
            "compose_blocked": own_ep.compose_blocked}


def _finish_when_ready(ctx: Context, cfg: Config, results: dict,
                       drawing_done: threading.Event,
                       lock: threading.Lock, tail: list[str]) -> None:
    """Put each episode together as soon as its shots are all drawn.

    The film does not have to wait for the last shot of the last
    episode. The cards are busy for hours, and an episode that is
    finished can be put together while the others are still being
    drawn: the machines keep working, and the first episode is ready
    to watch long before the last one is.

    An episode that cannot be made is not tried over and over: it is
    tried again when its shots change, and otherwise it is left to the
    tail at the end of the run.
    """
    tried: dict[int, tuple] = {}
    while True:
        worked = False
        try:
            episodes = list(ctx.target_episodes())
        except Exception:  # noqa: BLE001
            episodes = []
        for ep in episodes:
            if ctx.stopped:
                return
            if _episode_made(ep):
                continue
            shots = [sh for sc in ep.scenes for sh in sc.shots]
            if not shots or not all(getattr(sh, "video_path", "") for sh in shots):
                continue
            ready = tuple(sh.id for sh in shots)
            if tried.get(ep.index) == ready:
                continue          # nothing new since the last attempt
            tried[ep.index] = ready
            log.info("第%d集《%s》的镜头齐了，开始合成", ep.index, ep.title)
            made = _finish_one(ctx, cfg, ep.index, results, lock, tail)
            # the run's own copy has to know, or it will put the same
            # episode together again the moment it looks
            if made:
                ep.video_path = made.get("video_path") or ep.video_path
                ep.subtitle_path = made.get("subtitle_path") or ep.subtitle_path
                if made.get("status"):
                    ep.status = made["status"]
                if made.get("qc_report"):
                    ep.qc_report = made["qc_report"]
                ep.compose_blocked = made.get("compose_blocked") or ""
                for k, v in (made.get("stage_status") or {}).items():
                    if not ep.stage_status:
                        ep.stage_status = {}
                    ep.stage_status[k] = v
            worked = True
        if drawing_done.is_set() and not worked:
            return
        time.sleep(10)


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
    # The counts the run reports. Each shot is counted once, when it
    # comes out: a shot that was tried three times and failed is one
    # failure, not three, so the tally is read from the project at the
    # end rather than summed over the passes.
    images_ok = 0
    videos_ok = 0

    def _tally(res: dict) -> None:
        nonlocal images_ok, videos_ok
        images_ok += int(res.get("images_ok") or 0)
        videos_ok += int(res.get("videos_ok") or 0)

    try:
        while True:
            if ctx.stopped:
                raise RunStopped()
            res = visual.run(ctx) or {}
            passes += 1
            _tally(res)
            # `shots_total` is how many shots the pass had in hand. It is
            # the thing that says whether the pass did anything: a pass
            # that found nothing to do reports no shots at all, and a
            # pass whose shots all failed still had shots.
            if res.get("shots_total"):
                # work was done: there may be more waiting behind it
                continue
            if not writes_done.is_set():
                # nothing ready and the writers are still going: wait
                # rather than spin, then look again
                writes_done.wait(5)
                continue
            # The writers are done - and they may have finished between
            # the pass above and this check, so what they left behind is
            # ours to draw. One more pass takes it; without it a run
            # whose writers were quick finishes with nothing drawn and
            # reports a clean run that drew nothing.
            res = visual.run(ctx) or {}
            passes += 1
            _tally(res)
            if res.get("shots_total"):
                continue
            ok = failed = no_still = 0
            wants_still = ctx.cfg.comfyui.mode in ("image", "image_then_video")
            for ep in ctx.target_episodes():
                for sc in ep.scenes:
                    for shot in sc.shots:
                        if not (shot.prompt or "").strip():
                            continue   # nothing to draw from yet
                        if shot.status != Status.DONE:
                            failed += 1
                        elif wants_still and not (shot.image_path or "").strip():
                            # the clip is there, but the still it was to
                            # continue from is not: it was made from the
                            # text alone, and the report must not call
                            # that a success
                            no_still += 1
                        else:
                            ok += 1
            results["visual"] = {
                "shots_ok": ok, "shots_total": ok + failed + no_still,
                "images_ok": images_ok, "videos_ok": videos_ok,
                "failed": failed + no_still, "no_still": no_still}
            _mark(Status.DONE)
            log.info("── 阶段 [visual] 完成（%d 趟）: %s ──", passes,
                     results["visual"])
            return
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
            season_obj = _run_stage(ctx, name, source_file, season_obj,
                                    results, cfg) or season_obj
            if _stop_if_wanted(name):
                return _finish(ctx, season_obj, stages, results)

        writes = _wanted(WRITES)
        draws = _wanted(DRAWS)
        casting = _wanted(CASTING)
        # The chain: each stage writes what the next one reads.  The rest
        # only need the script, so they do not wait for the storyboard or
        # the prompts - the voice and the music are made while the shots
        # are still being written.
        chain = [s for s in writes if s not in SIDE_WRITES]
        side = [s for s in writes if s in SIDE_WRITES]

        # ---- the lanes that do not have to wait for each other -------
        if writes and draws:
            log.info("── 两道并行：写作 %s / 绘制 %s ──", writes, draws)
            writes_done = threading.Event()
            drawing_done = threading.Event()
            script_done = threading.Event()
            side_done = threading.Event()
            cast_done = threading.Event()
            results_lock = threading.Lock()

            def _cast_lane():
                """The casting: the pictures of the cast and their voices."""
                try:
                    for name in casting:
                        if ctx.stopped:
                            break
                        _lane(ctx, "定妆", name)
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if _stop_if_wanted(name):
                            break
                finally:
                    cast_done.set()
                    _lane(ctx, "定妆", "")

            def _write_lane():
                try:
                    for name in chain:
                        if ctx.stopped:
                            break
                        if name == "promptgen":
                            # the prompts carry the characters' anchors, so
                            # this is the one stage that waits for the casting
                            cast_done.wait()
                        _lane(ctx, "写作", name)
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if name == "script":
                            script_done.set()
                        if _stop_if_wanted(name):
                            break
                finally:
                    # the side lane waits for the script, and the drawer's
                    # last pass waits for both lanes
                    script_done.set()
                    _lane(ctx, "写作", "")
                    side_done.wait()
                    writes_done.set()

            def _side_lane():
                try:
                    # the voice and the music need the script and nothing
                    # else, so they start as soon as it is written
                    script_done.wait()
                    for name in side:
                        if ctx.stopped:
                            break
                        _lane(ctx, "旁路", name)
                        _run_stage(ctx, name, None, season_obj, results, cfg)
                        if _stop_if_wanted(name):
                            break
                finally:
                    _lane(ctx, "旁路", "")
                    side_done.set()

            def _draw_lane():
                try:
                    _lane(ctx, "绘制", "visual")
                    _draw_until_done(ctx, writes_done, results, cfg)
                finally:
                    _lane(ctx, "绘制", "")
                    # the finisher waits for this: an episode can only be
                    # made once its shots are all drawn
                    drawing_done.set()

            with ThreadPoolExecutor(max_workers=5) as pool:
                wfut = pool.submit(_write_lane)
                cfut = pool.submit(_cast_lane)
                sfut = pool.submit(_side_lane)
                dfut = pool.submit(_draw_lane)
                # the third lane puts each episode together as soon as its
                # own shots are done, so the first episode can be watched
                # while the last one is still being drawn
                ffut = pool.submit(_finish_when_ready, ctx, cfg, results,
                                   drawing_done, results_lock,
                                   _wanted(TAIL))
                wfut.result()
                cfut.result()
                sfut.result()
                dfut.result()
                ffut.result()
            if ctx.stopped:
                return _finish(ctx, season_obj, stages, results)
        else:
            for name in list(casting) + chain + draws:
                if ctx.stopped:
                    break
                season_obj = _run_stage(ctx, name, None, season_obj,
                                        results, cfg) or season_obj
                if _stop_if_wanted(name):
                    return _finish(ctx, season_obj, stages, results)
            for name in side:
                if ctx.stopped:
                    break
                season_obj = _run_stage(ctx, name, None, season_obj,
                                        results, cfg) or season_obj
                if _stop_if_wanted(name):
                    return _finish(ctx, season_obj, stages, results)

        # ---- what needs both lanes finished -------------------------------
        # The safety net: anything the third lane did not get to - an
        # episode whose shots arrived too late to be caught - is made here.
        for name in _wanted(TAIL):
            if ctx.stopped:
                break
            season_obj = _run_stage(ctx, name, None, season_obj,
                                    results, cfg) or season_obj
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
