"""Stage 8 — visual: generate each shot's image (and optional video) via ComfyUI.

Craft upgrades mirroring a professional short-drama workflow:
  * character reference images are uploaded into the t2i workflow when
    `characters.consistency = "ref"` (needs a LoadImage node id)
  * first/last-frame mode renders an end keyframe and drives i2v with both
    frames, giving a controlled camera move instead of a drifting still
  * seeds are derived from the character name (sha1) so the same actor keeps
    a stable latent identity across shots

Resumable: DONE shots are skipped. If ComfyUI is disabled/unreachable the
stage is skipped and compose falls back to Ken Burns on any available still,
or a card. `regen_shot()` is the single-shot entry used by the web console.
"""
from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import Config
from ..media import ffmpeg as ff
from ..models import Shot, Status
from ..project import ProjectStore
from .base import Context, build_timeline


def _stable_seed(token: str) -> int:
    return int(hashlib.sha1(token.encode("utf-8")).hexdigest()[:8], 16) % (2**31)


def _seed_for(ctx: Context, shot: Shot) -> int:
    mode = ctx.cfg.comfyui.seed_mode
    if mode == "fixed":
        return ctx.cfg.comfyui.fixed_seed
    if mode == "character":
        return _stable_seed(shot.characters[0] if shot.characters else shot.id)
    if shot.seed >= 0:
        return shot.seed
    return -1  # client randomizes


def _ref_images(ctx: Context, shot: Shot, scene=None) -> list[str]:
    """One reference image per on-screen character, then the scene's location.

    Order matters: the first slot drives the primary identity. Extra slots (if
    the workflow exposes several IP-Adapter inputs) get the rest in this order.
    """
    if ctx.cfg.characters.consistency != "ref":
        return []
    out: list[str] = []
    for name in shot.characters or []:
        c = ctx.project.character(name)
        if c is None or (c.consistency and c.consistency != "ref"):
            continue
        refs = c.refs()
        primary = refs[0] if refs else ""
        if not primary:
            continue
        p = ctx.store.abs(primary)
        if p.exists() and str(p) not in out:
            out.append(str(p))
    if scene is not None:
        for loc in ctx.project.locations:
            if loc.name != scene.location:
                continue
            for rel in loc.ref_images[:1]:
                p = ctx.store.abs(rel)
                if p.exists() and str(p) not in out:
                    out.append(str(p))
    return out


def _fit_refs(ctx: Context, refs: list[str], shot: Shot) -> list[str]:
    """Bring reference images to the delivery aspect.

    FLUX 3 takes the output size from the reference image, and the character
    sheets are portrait while the episode is 16:9. Fitting them first keeps
    the render at the right shape.
    """
    if not refs:
        return refs
    iw, ih = _image_size(ctx)
    out_dir = ctx.store.root / "tmp" / "refs"
    out: list[str] = []
    for i, path in enumerate(refs):
        dst = out_dir / f"{shot.id}_{i}.png"
        try:
            ff.fit_reference(path, dst, iw, ih)
            out.append(str(dst))
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("参考图适配失败(%s)，用原图: %s", path, str(e)[:120])
            out.append(path)
    return out


def flf_enabled(ctx: Context, shot: Shot) -> bool:
    c = ctx.cfg.comfyui
    if not c.first_last_frame or shot.flf is False:
        return False
    return bool(c.flf_workflow and c.i2v_nodes.get("last_image"))


def _extra(ctx: Context) -> dict:
    c = ctx.cfg.comfyui
    return {"sampler": c.sampler, "scheduler": c.scheduler, "checkpoint": c.checkpoint}


def _gen_one(ctx: Context, sc, shot: Shot, *, do_image: bool, do_video: bool,
             force: bool = False) -> tuple[str, bool, str]:
    """Render one shot, image first and then video.

    Kept for the single-shot paths (regen). The stage runs the two phases
    separately - see `run` - so the image model and the video model are not
    swapped in and out for every shot.
    """
    vis = ctx.providers.visual
    if vis is None:
        return shot.id, False, "no visual provider"
    c = ctx.cfg.comfyui
    iw, ih = _image_size(ctx)
    img_out = ctx.store.image_path(shot.id)
    end_out = ctx.store.end_image_path(shot.id)
    seed = _seed_for(ctx, shot)
    meta: dict = {"seed": seed, "mode": c.mode}
    try:
        if do_image and (force or not img_out.exists()):
            refs = _fit_refs(ctx, _ref_images(ctx, shot, sc), shot)
            vis.generate_image(
                prompt=shot.prompt, negative=shot.negative_prompt,
                width=iw, height=ih, seed=seed, steps=c.steps, cfg=c.cfg,
                out_path=str(img_out), extra=_extra(ctx), ref_images=refs)
            meta["refs"] = len(refs)
        if img_out.exists():
            shot.image_path = ctx.store.rel(img_out)
        if force and not do_image and not img_out.exists():
            raise FileNotFoundError("缺少首帧，无法只重生成视频")

        if do_video:
            use_flf = flf_enabled(ctx, shot)
            if use_flf and (force or not end_out.exists()):
                vis.generate_image(
                    prompt=shot.end_prompt or shot.prompt,
                    negative=shot.negative_prompt,
                    width=c.width, height=c.height,
                    seed=(seed + 1) % (2**31) if seed >= 0 else seed,
                    steps=c.steps, cfg=c.cfg, out_path=str(end_out),
                    extra=_extra(ctx),
                    ref_images=_fit_refs(ctx, _ref_images(ctx, shot, sc), shot))
                meta["end_seed"] = (seed + 1) % (2**31) if seed >= 0 else -1
            last = str(end_out) if use_flf and end_out.exists() else ""
            vid_out = ctx.store.video_path(shot.id)
            # H3 wants its own three-field prompt; fall back to the image prompt
            vprompt = shot.video_prompt or shot.prompt
            try:
                vis.generate_video(
                    prompt=vprompt, negative=shot.negative_prompt,
                    image_path=str(img_out) if img_out.exists() else "",
                    frames=c.frames, fps=c.fps, seed=seed, out_path=str(vid_out),
                    extra=_extra(ctx), last_image_path=last)
            except Exception as e:  # noqa: BLE001
                if not last:
                    raise
                ctx.log.warning("visual: 镜 %s 首尾帧失败(%s)，退回单图 i2v",
                                shot.id, str(e)[:120])
                use_flf = False
                vis.generate_video(
                    prompt=vprompt, negative=shot.negative_prompt,
                    image_path=str(img_out) if img_out.exists() else "",
                    frames=c.frames, fps=c.fps, seed=seed, out_path=str(vid_out),
                    extra=_extra(ctx))
            shot.video_path = ctx.store.rel(vid_out)
            meta["flf"] = use_flf

        if flf_enabled(ctx, shot) and end_out.exists():
            shot.end_image_path = ctx.store.rel(end_out)
        shot.gen_meta = meta
        shot.status = Status.DONE
        return shot.id, True, ""
    except Exception as e:  # noqa: BLE001
        msg = str(e)[:200]
        shot.status = Status.FAILED
        ctx.log.error("visual: 镜 %s 失败 %s", shot.id, msg)
        return shot.id, False, msg


def _render(ctx: Context, what: str, shot_id: str, fn, tries: int = 3):
    """Render, and retry when the card ran out of memory.

    ComfyUI drops every model when it hits an OOM, so the next attempt starts
    fresh and normally goes through. Without the retry a single spike took the
    whole episode down with it.
    """
    last: Optional[Exception] = None
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            from ..providers.comfyui import ComfyUIClient
            if not ComfyUIClient.is_oom(e):
                raise
            ctx.log.warning("visual: 镜 %s %s 显存不足，第%d 次重试",
                            shot_id, what, attempt + 2)
            time.sleep(15 + attempt * 10)
    raise last  # type: ignore[misc]


def _image_size(ctx: Context) -> tuple[int, int]:
    """The size the stills are made at.

    The picture has to be made in the shape it is going to be shown in: a
    still made in another shape is cropped to fit, and the crop is what takes
    the faces off. The configured image size is kept as long as its shape
    matches the delivery format.
    """
    c = ctx.cfg.comfyui
    w, h = int(c.width or 1280), int(c.height or 720)
    dw, dh = int(ctx.cfg.compose.width or 0), int(ctx.cfg.compose.height or 0)
    if dw <= 0 or dh <= 0:
        return w, h
    if abs((w / h) - (dw / dh)) <= 0.03:
        return w, h
    k = min(w / dw, h / dh)
    nw = max(512, int(dw * k) // 16 * 16)
    nh = max(512, int(dh * k) // 16 * 16)
    ctx.log.warning("visual: 出图尺寸 %dx%d 与成片 %dx%d 比例不符，改用 %dx%d",
                    w, h, dw, dh, nw, nh)
    return nw, nh


def _gen_image(ctx: Context, sc, shot: Shot) -> tuple[str, bool, str]:
    """Render only the still (and the flf end frame)."""
    vis = ctx.providers.visual
    c = ctx.cfg.comfyui
    img_out = ctx.store.image_path(shot.id)
    end_out = ctx.store.end_image_path(shot.id)
    seed = _seed_for(ctx, shot)
    meta: dict = dict(shot.gen_meta or {})
    meta.update({"seed": seed, "mode": c.mode})
    try:
        if not img_out.exists():
            refs = _fit_refs(ctx, _ref_images(ctx, shot, sc), shot)
            _render(ctx, "出图", shot.id, lambda: vis.generate_image(
                prompt=shot.prompt, negative=shot.negative_prompt,
                width=c.width, height=c.height, seed=seed, steps=c.steps, cfg=c.cfg,
                out_path=str(img_out), extra=_extra(ctx), ref_images=refs))
            meta["refs"] = len(refs)
        shot.image_path = ctx.store.rel(img_out)
        if flf_enabled(ctx, shot) and not end_out.exists():
            vis.generate_image(
                prompt=shot.end_prompt or shot.prompt,
                negative=shot.negative_prompt, width=c.width, height=c.height,
                seed=(seed + 1) % (2**31) if seed >= 0 else seed,
                steps=c.steps, cfg=c.cfg, out_path=str(end_out),
                extra=_extra(ctx),
                ref_images=_fit_refs(ctx, _ref_images(ctx, shot, sc), shot))
            meta["end_seed"] = (seed + 1) % (2**31) if seed >= 0 else -1
        if end_out.exists():
            shot.end_image_path = ctx.store.rel(end_out)
        shot.gen_meta = meta
        return shot.id, True, ""
    except Exception as e:  # noqa: BLE001
        msg = str(e)[:200]
        ctx.log.error("visual: 镜 %s 出图失败 %s", shot.id, msg)
        return shot.id, False, msg


def _shot_frames(ctx: Context, shot: Shot, duration: float) -> int:
    """Frame count for one shot.

    H3 only takes lengths on its 17k+5 grid (124 = ~5s at 24fps, up to 362 =
    ~15s). A shot gets the length it actually needs on the timeline, so a long
    beat is not played back as a loop and a short one is not padded.
    """
    c = ctx.cfg.comfyui
    if c.frame_mode != "auto" or duration <= 0:
        return c.frames
    fps = c.fps or 24
    longest = max(5, int(c.max_video_seconds * fps))
    target = int(round(duration * fps))
    # round up: a clip shorter than its slot would have to be looped, and the
    # rewind at the end of the shot is visible
    k = max(1, -(-(target - 5) // 17))
    return max(5, min(17 * k + 5, longest))


def _reference_audio(ctx: Context, shot: Shot) -> str:
    """The recording of this shot's line, as the voice reference.

    H3 speaks the words itself, but it takes the timbre from this
    recording - so the character sounds the same in every shot.
    """
    from .lipsync import _scene_wav
    tl = ctx.timeline(ctx.target_episodes()[0])
    for tsc in tl.scenes:
        for ts in tsc.shots:
            if ts.shot.id != shot.id:
                continue
            placed = []
            for t in tsc.lines:
                if t.line.kind.value != "dialogue":
                    continue
                if not (ts.start - 0.02 <= t.start < ts.start + ts.duration):
                    continue
                if not t.line.audio_path:
                    continue
                placed.append((t.start - tsc.start,
                               ctx.store.abs(t.line.audio_path)))
            if not placed:
                return ""
            out = ctx.store.root / "tmp" / f"refaudio_{shot.id}.wav"
            if _scene_wav(placed, ts.start - tsc.start, ts.duration, out):
                return str(out)
    return ""


def _gen_video(ctx: Context, sc, shot: Shot, duration: float = 0.0) -> tuple[str, bool, str]:
    """Render only the video for one shot."""
    vis = ctx.providers.visual
    c = ctx.cfg.comfyui
    img_out = ctx.store.image_path(shot.id)
    end_out = ctx.store.end_image_path(shot.id)
    vid_out = ctx.store.video_path(shot.id)
    seed = _seed_for(ctx, shot)
    frames = _shot_frames(ctx, shot, duration)
    meta: dict = dict(shot.gen_meta or {})
    meta.update({"seed": seed, "mode": c.mode, "frames": frames})
    # The references have to be there before a card is spent: the character's
    # views, the room, and the frame this shot continues from.
    plan: list[str] = []
    if c.native_audio or c.video_references:
        from .refs import missing_references, picture_plan
        missing = missing_references(ctx, shot, sc)
        if missing:
            msg = "参考图不齐: " + "、".join(missing)
            ctx.log.error("visual: 镜 %s %s（不抽卡）", shot.id, msg)
            shot.status = Status.FAILED
            return shot.id, False, msg
        plan = [p for p, _role in picture_plan(ctx, shot, sc)]
        meta["references"] = len(plan)
    try:
        use_flf = flf_enabled(ctx, shot) and end_out.exists()
        last = str(end_out) if use_flf else ""
        vprompt = shot.video_prompt or shot.prompt
        extra = _extra(ctx)
        if plan:
            extra["ref_pictures"] = plan
        if c.native_audio:
            ref = _reference_audio(ctx, shot)
            if ref:
                extra["ref_audio_path"] = ref
                extra["ref_audio_node"] = c.ref_audio_node
        try:
            _render(ctx, "出视频", shot.id, lambda: vis.generate_video(
                prompt=vprompt, negative=shot.negative_prompt,
                image_path=str(img_out) if img_out.exists() else "",
                frames=frames, fps=c.fps, seed=seed, out_path=str(vid_out),
                extra=extra, last_image_path=last))
        except Exception as e:  # noqa: BLE001
            if not last:
                raise
            ctx.log.warning("visual: 镜 %s 首尾帧失败(%s)，退回单图 i2v",
                            shot.id, str(e)[:120])
            use_flf = False
            _render(ctx, "出视频", shot.id, lambda: vis.generate_video(
                prompt=vprompt, negative=shot.negative_prompt,
                image_path=str(img_out) if img_out.exists() else "",
                frames=frames, fps=c.fps, seed=seed, out_path=str(vid_out),
                extra=extra))
        shot.video_path = ctx.store.rel(vid_out)
        meta["flf"] = use_flf
        shot.gen_meta = meta
        shot.status = Status.DONE
        return shot.id, True, ""
    except Exception as e:  # noqa: BLE001
        msg = str(e)[:200]
        shot.status = Status.FAILED
        ctx.log.error("visual: 镜 %s 出视频失败 %s", shot.id, msg)
        return shot.id, False, msg


def _gen_scores(ctx: Context) -> int:
    """One music-only clip per scene: the score of the episode."""
    if ctx.cfg.compose.h3_audio != "bed":
        return 0
    jobs = []
    for ep in ctx.target_episodes():
        for tscene in ctx.timeline(ep).scenes:
            jobs.append((ep, tscene.scene, tscene.duration))
    if not jobs:
        return 0
    ctx.log.info("visual: 配乐镜头（%d 段）", len(jobs))
    ok = 0
    with ThreadPoolExecutor(max_workers=1) as ex:
        futs = [ex.submit(_gen_score, ctx, ep, sc, dur) for ep, sc, dur in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            _sid, good, _msg = fut.result()
            ok += int(good)
            _write_progress(ctx, "visual", i, len(jobs))
            if i % 2 == 0 or i == len(jobs):
                ctx.log.info("visual: 配乐 %d/%d 完成", i, len(jobs))
    return ok


def _gen_score(ctx: Context, ep, sc, scene_duration: float = 0.0) -> tuple[str, bool, str]:
    """Render the scene's music-only clip.

    The clip has no people in it, so its sound is only ambience and music -
    which is what the episode needs for its score. The shots' own sound is
    not used: H3 speaks the prompt out loud in gibberish when a character is
    told to talk, and that belongs nowhere near the recorded dialogue.
    """
    if not sc.score_prompt:
        return sc.id, False, "没有配乐提示词"
    vis = ctx.providers.visual
    c = ctx.cfg.comfyui
    out = ctx.store.root / "music" / f"score_ep{ep.index:03d}_sc{sc.index:03d}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 1024:
        return sc.id, True, "cached"
    # the location's own picture keeps the score in the right place
    first = ctx.store.location_ref_path(sc.location, "ref", "png")
    if not first.exists():
        for ext in ("jpg", "jpeg", "webp"):
            alt = ctx.store.location_ref_path(sc.location, "ref", ext)
            if alt.exists():
                first = alt
                break
    if not first.exists():
        shots = [sh for sh in sc.shots if sh.image_path]
        if not shots:
            return sc.id, False, "没有可用的首帧"
        first = ctx.store.abs(shots[0].image_path)
    # the clip is as long as the scene it scores, so the music does not have
    # to repeat every five seconds - but the model's cost climbs steeply
    # past a quarter of a minute, so the cap keeps the job affordable and the
    # music loops inside the scene
    scene_dur = scene_duration or 0.0
    frames = int(round(scene_dur * c.fps)) if scene_dur > 0 else 124
    frames = max(124, min(frames, 240, int(c.max_video_seconds * c.fps)))
    seed = 100000 + ep.index * 100 + sc.index
    try:
        _render(ctx, "配乐", sc.id, lambda: vis.generate_video(
            prompt=sc.score_prompt, negative="",
            image_path=str(first), frames=frames, fps=c.fps, seed=seed,
            out_path=str(out), extra=_extra(ctx)))
        return sc.id, True, ""
    except Exception as e:  # noqa: BLE001
        msg = str(e)[:200]
        ctx.log.error("visual: 场%d 配乐镜头失败 %s", sc.index, msg)
        return sc.id, False, msg


def _write_progress(ctx: "Context", stage: str, done: int, total: int) -> None:
    """Persist transient per-shot progress to a sidecar file the web console reads.

    Kept out of project.json (owned by the pipeline's save cycle) so it can be
    updated every shot without touching the Project model. Best-effort: any
    failure is swallowed so progress reporting never breaks generation.
    """
    try:
        import json as _json, time as _time
        p = ctx.store.root / ".progress.json"
        data: dict = {}
        if p.exists():
            try:
                data = _json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                data = {}
        data[stage] = {"done": done, "total": total, "ts": int(_time.time())}
        p.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def run(ctx: Context) -> dict:
    c = ctx.cfg.comfyui
    if not c.enabled:
        ctx.log.info("visual: ComfyUI 已禁用，跳过（compose 将用静帧/占位卡）")
        return {"skipped": True}
    vis = ctx.providers.visual
    if vis is None:
        ctx.log.warning("visual: 无可用画面 provider，跳过")
        return {"skipped": True}
    if hasattr(vis, "ping") and not vis.ping():
        ctx.log.error("visual: ComfyUI 不可达（%s）。启动服务器后重跑本阶段。", c.base_url)
        return {"error": "comfyui_unreachable", "base_url": c.base_url}

    do_image = c.mode in ("image", "image_then_video")
    do_video = c.mode in ("video", "image_then_video")
    # how long each shot actually sits on the timeline - the video is rendered
    # to that length instead of a fixed one
    durations: dict[str, float] = {}
    for ep in ctx.target_episodes():
        for ts in ctx.timeline(ep).shots:
            durations[ts.shot.id] = ts.duration
    jobs = []
    for ep in ctx.target_episodes():
        if ctx.stage_done(ep, "visual"):
            continue
        for sc in ep.scenes:
            for shot in sc.shots:
                if shot.status == Status.DONE and shot.has_visual:
                    continue
                jobs.append((ep, sc, shot))

    if not jobs:
        ctx.log.info("visual: 所有镜头已生成")
        _gen_scores(ctx)
        return {"shots": 0}

    ctx.log.info("visual: 生成 %d 个镜头（并发=%d，模式=%s）", len(jobs), c.concurrency, c.mode)
    ok_count = 0

    # Two phases on purpose. The still model and the video model do not fit in
    # one GPU at once, so alternating per shot makes ComfyUI swap 15GB of
    # weights in and out for every single shot. Doing all the stills first and
    # all the videos after keeps one model resident and the swap happens once.
    def _run_phase(label: str, fn, total: int, offset: int,
                   workers: int = 0) -> int:
        nonlocal ok_count
        done = 0
        n = workers or c.concurrency
        with ThreadPoolExecutor(max_workers=max(1, n)) as ex:
            futs = [ex.submit(fn, ctx, sc, shot, durations.get(shot.id, 0.0))
                    if fn is _gen_video else ex.submit(fn, ctx, sc, shot)
                    for (_ep, sc, shot) in jobs]
            for i, fut in enumerate(as_completed(futs), 1):
                _sid, ok, _msg = fut.result()
                ok_count += int(ok)
                done = i
                _write_progress(ctx, "visual", offset + i, total)
                if i % 5 == 0 or i == len(jobs):
                    ctx.save()
                    ctx.log.info("visual: %s %d/%d 完成", label, i, total)
        return done

    total = len(jobs) * (2 if (do_image and do_video) else 1)
    offset = 0
    if do_image:
        ctx.log.info("visual: 第一批 · 出图（%d 张）", len(jobs))
        offset += _run_phase("出图", _gen_image, total, offset)
        ctx.save()
    if do_video:
        ctx.log.info("visual: 第二批 · 出视频（%d 段）", len(jobs))
        offset += _run_phase("出视频", _gen_video, total, offset,
                             workers=max(1, int(c.video_concurrency or 0)
                                          or c.concurrency))
        ctx.save()
    elif do_image:
        for (_ep, _sc, shot) in jobs:
            if shot.image_path and shot.status != Status.FAILED:
                shot.status = Status.DONE

    # the music bed: one music-only clip per scene
    if do_video:
        _gen_scores(ctx)
    ctx.save()

    for ep in ctx.target_episodes():
        if all(sh.status == Status.DONE for sc in ep.scenes for sh in sc.shots) \
                and ep.total_shots > 0:
            ctx.mark(ep, "visual", Status.DONE)
    ctx.save()
    return {"shots_ok": ok_count, "shots_total": len(jobs)}


def regen_shot(store: ProjectStore, cfg: Config, ep_index: int, shot_id: str,
               *, mode: str = "all") -> dict:
    """Regenerate one shot from the console: image / video / all."""
    ctx = Context(cfg, store)
    ep = ctx.project.episode(ep_index)
    if ep is None:
        return {"ok": False, "error": f"没有第 {ep_index} 集"}
    for sc in ep.scenes:
        for shot in sc.shots:
            if shot.id != shot_id:
                continue
            do_image = mode in ("image", "all")
            do_video = mode in ("video", "all")
            sid, ok, msg = _gen_one(ctx, sc, shot, do_image=do_image,
                                    do_video=do_video, force=True)
            ctx.save()
            return {"ok": ok, "shot": sid, "error": msg,
                    "image_path": shot.image_path, "end_image_path": shot.end_image_path,
                    "video_path": shot.video_path, "gen_meta": shot.gen_meta}
    return {"ok": False, "error": f"没有镜头 {shot_id}"}
