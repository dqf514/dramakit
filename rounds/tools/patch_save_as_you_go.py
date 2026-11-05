"""Each episode is saved as soon as it is written.

The parallel stages take all the episodes at once, and the work of one
episode is finished long before the work of the others.  If the run is
stopped halfway - or the console is restarted - the episodes that were
already written have to stay written.  So the writing, the marking and
the saving happen in the worker, not after the batch.
"""
import pathlib

# ---------------------------------------------------------------- script
PATH = pathlib.Path(r"E:\dramakit\dramakit\pipeline\script.py")
text = PATH.read_text(encoding="utf-8")

old = '''    # The episodes are independent of each other, and the endpoint answers
    # several calls at once - so they are asked together, not one after
    # another.
    def _one(job):
        ep, user = job
        data = pool.next().complete_json(T.SCRIPT_SYSTEM, user)
        if isinstance(data, list):
            data = data[0] if data else {}
        return data

    results = run_jobs(ctx, jobs, _one, workers=write_workers(ctx),
                       label="script")
    for (job, data, err) in results:
        ep, _user = job
        if err:
            ctx.log.error("script: 第%d集失败 %s", ep.index, err)
            ctx.mark(ep, "script", Status.FAILED)
            if cfg.pipeline.fail_fast:
                raise RuntimeError(err)
            continue
        scenes = []
        for si, s in enumerate(data.get("scenes", []) or [], 1):
            sc = Scene(id=_id("sc"), index=si, location=s.get("location", ""),
                       time_of_day=s.get("time_of_day", "日"),
                       summary=s.get("summary", ""), mood=s.get("mood", "中性"),
                       bgm_mood=s.get("bgm_mood", ""))
            for li, l in enumerate(s.get("lines", []) or [], 1):
                txt = (l.get("text") or "").strip()
                if not txt:
                    continue
                sc.lines.append(Line(id=_id("ln"), kind=_to_kind(l.get("kind", "dialogue")),
                                     speaker=(l.get("speaker") or "旁白").strip(),
                                     text=txt, emotion=l.get("emotion", "平静")))
            if sc.lines:
                scenes.append(sc)
        ep.scenes = scenes
        ctx.mark(ep, "script", Status.DONE)
        ctx.save()
        done += 1
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 句",
                     ep.index, ep.title, len(scenes), sum(len(s.lines) for s in scenes))
    return {"episodes_scripted": done}'''

new = '''    # The episodes are independent of each other, and the endpoint answers
    # several calls at once - so they are asked together, not one after
    # another.
    def _one(job):
        ep, user = job
        data = pool.next().complete_json(T.SCRIPT_SYSTEM, user)
        if isinstance(data, list):
            data = data[0] if data else {}
        scenes = []
        for si, s in enumerate(data.get("scenes", []) or [], 1):
            sc = Scene(id=_id("sc"), index=si, location=s.get("location", ""),
                       time_of_day=s.get("time_of_day", "日"),
                       summary=s.get("summary", ""), mood=s.get("mood", "中性"),
                       bgm_mood=s.get("bgm_mood", ""))
            for li, l in enumerate(s.get("lines", []) or [], 1):
                txt = (l.get("text") or "").strip()
                if not txt:
                    continue
                sc.lines.append(Line(id=_id("ln"), kind=_to_kind(l.get("kind", "dialogue")),
                                     speaker=(l.get("speaker") or "旁白").strip(),
                                     text=txt, emotion=l.get("emotion", "平静")))
            if sc.lines:
                scenes.append(sc)
        # the episode is written and saved here, not after the whole
        # batch: a run that is stopped halfway keeps the episodes that
        # were already done
        ep.scenes = scenes
        ctx.mark(ep, "script", Status.DONE)
        ctx.save()
        return len(scenes)

    results = run_jobs(ctx, jobs, _one, workers=write_workers(ctx),
                       label="script")
    for (job, _scenes, err) in results:
        ep, _user = job
        if err:
            ctx.log.error("script: 第%d集失败 %s", ep.index, err)
            ctx.mark(ep, "script", Status.FAILED)
            if cfg.pipeline.fail_fast:
                raise RuntimeError(err)
            continue
        done += 1
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 句",
                     ep.index, ep.title, len(ep.scenes),
                     sum(len(s.lines) for s in ep.scenes))
    return {"episodes_scripted": done}'''

assert old in text, "找不到 script 的那一段"
text = text.replace(old, new, 1)
PATH.write_text(text, encoding="utf-8")
print("script 改好了")
