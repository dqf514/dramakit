"""Let the score clips be generated on their own.

The visual stage used to return early when every shot was done, so a
project whose pictures are finished could not get its music clips without
re-rendering the pictures as well.
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\visual.py")
s = p.read_text(encoding="utf-8")

old = """    if not jobs:
        ctx.log.info("visual: 所有镜头已生成")
        return {"shots": 0}
"""
new = """    if not jobs:
        ctx.log.info("visual: 所有镜头已生成")
        _gen_scores(ctx)
        return {"shots": 0}
"""
assert old in s, "提前返回锚点没找到"
s = s.replace(old, new, 1)

old = """    # the music bed: one music-only clip per scene
    if do_video and ctx.cfg.compose.h3_audio == "bed":
        score_jobs = []
        for ep in ctx.target_episodes():
            for tscene in build_timeline(
                    ep, max_shot=ctx.cfg.comfyui.max_video_seconds).scenes:
                score_jobs.append((ep, tscene.scene, tscene.duration))
        if score_jobs:
            ctx.log.info("visual: 第三批 · 配乐镜头（%d 段）", len(score_jobs))
            with ThreadPoolExecutor(max_workers=1) as ex:
                futs = [ex.submit(_gen_score, ctx, ep, sc, dur)
                        for ep, sc, dur in score_jobs]
                for i, fut in enumerate(as_completed(futs), 1):
                    _sid, ok, _msg = fut.result()
                    ok_count += int(ok)
                    _write_progress(ctx, "visual", offset + i, total + len(score_jobs))
                    if i % 2 == 0 or i == len(score_jobs):
                        ctx.log.info("visual: 配乐 %d/%d 完成", i, len(score_jobs))
    ctx.save()"""
new = """    # the music bed: one music-only clip per scene
    if do_video:
        _gen_scores(ctx)
    ctx.save()"""
assert old in s, "配乐批次锚点没找到"
s = s.replace(old, new, 1)

old = """def _gen_score(ctx: Context, ep, sc, scene_duration: float = 0.0) -> tuple[str, bool, str]:"""
new = '''def _gen_scores(ctx: Context) -> int:
    """One music-only clip per scene: the score of the episode."""
    if ctx.cfg.compose.h3_audio != "bed":
        return 0
    jobs = []
    for ep in ctx.target_episodes():
        for tscene in build_timeline(
                ep, max_shot=ctx.cfg.comfyui.max_video_seconds).scenes:
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


def _gen_score(ctx: Context, ep, sc, scene_duration: float = 0.0) -> tuple[str, bool, str]:'''
assert old in s, "_gen_score 锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("visual.py 已打补丁")
