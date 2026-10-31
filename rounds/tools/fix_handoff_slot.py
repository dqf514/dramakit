"""The handoff slot is always reserved.

The slot was only filled when the shot before had a video - and the prompt
is written before any video exists, so the prompt numbered the pictures
without it and the job sent the pictures with it: the numbers after the
inserted picture all moved by one.

The slot is reserved whether or not there is a frame for it yet, and the
job leaves the slot empty when there is no frame - the numbering is what
the prompt and the job have to agree on.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\refs.py")
s = p.read_text(encoding="utf-8")

old = """        # the handoff: where the shot before this one ended
        prev = _previous_shot(ctx, sc, shot)
        if prev is not None and prev.video_path:
            q = ctx.store.abs(prev.video_path)
            if str(q) not in seen:
                seen.add(str(q))
                out.append((str(q),
                            "the last frame of the shot before this one: the "
                            "people and the props are exactly where that shot "
                            "left them",
                            "handoff"))"""
new = """        # the handoff: where the shot before this one ended.  The slot is
        # reserved whether or not there is such a frame yet - the prompt is
        # written before the clip exists, and the numbers have to match.
        prev = _previous_shot(ctx, sc, shot)
        if prev is not None:
            prev_rel = prev.video_path or ctx.store.rel(
                ctx.store.video_path(prev.id))
            q = ctx.store.abs(prev_rel)
            if str(q) not in seen:
                seen.add(str(q))
                out.append((str(q),
                            "the last frame of the shot before this one: the "
                            "people and the props are exactly where that shot "
                            "left them",
                            "handoff"))"""
assert old in s, "交接帧锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("refs.py: 交接帧槽位永远预留")
