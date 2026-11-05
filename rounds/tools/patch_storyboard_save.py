"""The storyboard: each scene is saved as soon as it is designed.

The scenes of every episode are asked at once, and a scene is finished
long before the others are.  If the run is stopped halfway, the scenes
that were already designed have to stay designed - so the work is put
into the scene and saved in the worker, not after the batch.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\pipeline\storyboard.py")
text = PATH.read_text(encoding="utf-8")

old = '''    # Every scene is its own question to the model, and the scenes of
    # different episodes do not wait on each other - so they are asked
    # together.
    def _one(job):
        _ep, _sc, _spoken_at, _spoken_pos, user = job
        return pool.next().complete_json(system, user)

    results = run_jobs(ctx, jobs, _one, workers=write_workers(ctx),
                       label="storyboard")

    # the answers go back in
    failed: set = set()
    for (job, data, err) in results:
        ep, sc, spoken_at, spoken_pos, _user = job
        if err:
            ctx.log.error("storyboard: 第%d集 场%d 失败 %s", ep.index, sc.index, err)
            sc.status = Status.FAILED
            failed.add(ep.index)
            if ctx.cfg.pipeline.fail_fast:
                raise RuntimeError(err)
            # fallback: one shot per line so the pipeline still proceeds
            sc.shots = _fallback_shots(sc, dmin, dmax)
            continue
        if isinstance(data, list):
            data = data[0] if data else {}
        shots = []
        for i, s in enumerate(data.get("shots", []) or [], 0):
            # which lines this shot carries, so the cut can land on them
            idx: list[int] = []
            for v in (s.get("lines") or []):
                try:
                    n = int(v)
                except (TypeError, ValueError):
                    continue
                k = spoken_pos.get(n)
                if k and k not in idx:
                    idx.append(k)
            shots.append(Shot(
                id=_id("sh"), index=i, shot_type=_to_shot_type(s.get("shot_type", "中景")),
                camera_move=s.get("camera_move", "固定"),
                angle=_to_angle(s.get("angle", "")),
                height=_to_height(s.get("height", "")),
                lens=_to_lens(s.get("lens", "")),
                purpose=(s.get("purpose") or "").strip(),
                subject=(s.get("subject") or "").strip(),
                duration=_clamp(s.get("duration"), dmin, dmax, 3.0),
                action=_strip_facing_camera(s.get("action", "")),
                characters=[str(c) for c in (s.get("characters") or [])],
                line_indices=sorted(idx),
            ))
        sc.shots = shots or _fallback_shots(sc, dmin, dmax)
        _repair_line_casts(sc)
        _repair_characters(ctx, sc)
        # a shot that carries too much dialogue gets a second shot
        _split_long_shots(sc)
        # the coverage rules: nobody talks to the lens, and no two
        # shots in a row are the same picture
        _enforce_coverage(sc)
'''

new = '''    # Every scene is its own question to the model, and the scenes of
    # different episodes do not wait on each other - so they are asked
    # together.
    def _one(job):
        ep, sc, spoken_at, spoken_pos, user = job
        data = pool.next().complete_json(system, user)
        if isinstance(data, list):
            data = data[0] if data else {}
        shots = []
        for i, s in enumerate(data.get("shots", []) or [], 0):
            # which lines this shot carries, so the cut can land on them
            idx: list[int] = []
            for v in (s.get("lines") or []):
                try:
                    n = int(v)
                except (TypeError, ValueError):
                    continue
                k = spoken_pos.get(n)
                if k and k not in idx:
                    idx.append(k)
            shots.append(Shot(
                id=_id("sh"), index=i, shot_type=_to_shot_type(s.get("shot_type", "中景")),
                camera_move=s.get("camera_move", "固定"),
                angle=_to_angle(s.get("angle", "")),
                height=_to_height(s.get("height", "")),
                lens=_to_lens(s.get("lens", "")),
                purpose=(s.get("purpose") or "").strip(),
                subject=(s.get("subject") or "").strip(),
                duration=_clamp(s.get("duration"), dmin, dmax, 3.0),
                action=_strip_facing_camera(s.get("action", "")),
                characters=[str(c) for c in (s.get("characters") or [])],
                line_indices=sorted(idx),
            ))
        sc.shots = shots or _fallback_shots(sc, dmin, dmax)
        _repair_line_casts(sc)
        _repair_characters(ctx, sc)
        # a shot that carries too much dialogue gets a second shot
        _split_long_shots(sc)
        # the coverage rules: nobody talks to the lens, and no two
        # shots in a row are the same picture
        _enforce_coverage(sc)
        # the scene is saved as it arrives: a run that is stopped
        # halfway keeps the scenes that were already designed
        ctx.save()
        return len(shots)

    results = run_jobs(ctx, jobs, _one, workers=write_workers(ctx),
                       label="storyboard")

    # the answers go back in
    failed: set = set()
    for (job, _n, err) in results:
        ep, sc, _spoken_at, _spoken_pos, _user = job
        if err:
            ctx.log.error("storyboard: 第%d集 场%d 失败 %s", ep.index, sc.index, err)
            sc.status = Status.FAILED
            failed.add(ep.index)
            if ctx.cfg.pipeline.fail_fast:
                raise RuntimeError(err)
            # fallback: one shot per line so the pipeline still proceeds
            sc.shots = _fallback_shots(sc, dmin, dmax)
            ctx.save()
'''

assert old in text, "找不到分镜的那一段"
text = text.replace(old, new, 1)
PATH.write_text(text, encoding="utf-8")
print("storyboard 改好了")
