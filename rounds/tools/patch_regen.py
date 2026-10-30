"""One path for every render.

`regen_shot` - the console button and this test - used an older code path
that rendered the video without the reference pictures and without the voice
reference, so a shot re-rendered from the console came out with a different
face and a different voice than the one the episode was built with.

It now goes through the same two functions the stage uses.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py")
s = p.read_text(encoding="utf-8")

old = '''    for sc in ep.scenes:
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
    return {"ok": False, "error": f"没有镜头 {shot_id}"}'''

new = '''    # the slot the shot sits in: the clip is shot to that length
    dur = 0.0
    for target in ctx.target_episodes():
        for ts in ctx.timeline(target).shots:
            if ts.shot.id == shot_id:
                dur = ts.duration
                break
    for sc in ep.scenes:
        for shot in sc.shots:
            if shot.id != shot_id:
                continue
            ok = True
            msg = ""
            if mode in ("image", "all"):
                _sid, ok, msg = _gen_image(ctx, sc, shot)
            if ok and mode in ("video", "all"):
                _sid, ok, msg = _gen_video(ctx, sc, shot, dur)
            ctx.save()
            return {"ok": ok, "shot": shot.id, "error": msg,
                    "image_path": shot.image_path, "end_image_path": shot.end_image_path,
                    "video_path": shot.video_path, "gen_meta": shot.gen_meta,
                    "duration": dur}
    return {"ok": False, "error": f"没有镜头 {shot_id}"}'''

assert old in s, "regen_shot 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("visual.py: regen 走同一条渲染路径了")
