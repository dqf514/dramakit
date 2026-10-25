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
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import Config
from ..models import Shot, Status
from ..project import ProjectStore
from .base import Context


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
    vis = ctx.providers.visual
    if vis is None:
        return shot.id, False, "no visual provider"
    c = ctx.cfg.comfyui
    img_out = ctx.store.image_path(shot.id)
    end_out = ctx.store.end_image_path(shot.id)
    seed = _seed_for(ctx, shot)
    meta: dict = {"seed": seed, "mode": c.mode}
    try:
        if do_image and (force or not img_out.exists()):
            refs = _ref_images(ctx, shot, sc)
            vis.generate_image(
                prompt=shot.prompt, negative=shot.negative_prompt,
                width=c.width, height=c.height, seed=seed, steps=c.steps, cfg=c.cfg,
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
                    extra=_extra(ctx), ref_images=_ref_images(ctx, shot, sc))
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
        return {"shots": 0}

    ctx.log.info("visual: 生成 %d 个镜头（并发=%d，模式=%s）", len(jobs), c.concurrency, c.mode)
    ok_count = 0
    with ThreadPoolExecutor(max_workers=max(1, c.concurrency)) as ex:
        futs = [ex.submit(_gen_one, ctx, sc, shot, do_image=do_image, do_video=do_video)
                for (_ep, sc, shot) in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            _sid, ok, _msg = fut.result()
            ok_count += int(ok)
            _write_progress(ctx, "visual", i, len(jobs))
            if i % 5 == 0 or i == len(jobs):
                ctx.save()
                ctx.log.info("visual: %d/%d 完成", i, len(jobs))
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
