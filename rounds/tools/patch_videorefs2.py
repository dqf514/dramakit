"""The video gets the references, and no video without them.

The picture was made from the character's three views and the room; the
video was made from the first frame alone, so the model guessed the person
from one angle and the face changed from shot to shot. Now the video gets
the same pictures - the character sheets, the room and the frame it
continues from - and a shot whose references are short is not drawn at
all: a card spent on a video with nothing to hold on to is a card wasted.
"""
from pathlib import Path

# 1) the visual stage: the pictures and the gate
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py")
s = p.read_text(encoding="utf-8")

old = """def _gen_video(ctx: Context, sc, shot: Shot, duration: float = 0.0) -> tuple[str, bool, str]:
    \"\"\"Render only the video for one shot.\"\"\"
    vis = ctx.providers.visual
    c = ctx.cfg.comfyui
    img_out = ctx.store.image_path(shot.id)
    end_out = ctx.store.end_image_path(shot.id)
    vid_out = ctx.store.video_path(shot.id)
    seed = _seed_for(ctx, shot)
    frames = _shot_frames(ctx, shot, duration)
    meta: dict = dict(shot.gen_meta or {})
    meta.update({"seed": seed, "mode": c.mode, "frames": frames})
    try:"""
new = """def _gen_video(ctx: Context, sc, shot: Shot, duration: float = 0.0) -> tuple[str, bool, str]:
    \"\"\"Render only the video for one shot.\"\"\"
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
    try:"""
assert old in s, "_gen_video 锚点没找到"
s = s.replace(old, new, 1)

old = """        extra = _extra(ctx)
        if c.native_audio:
            ref = _reference_audio(ctx, shot)
            if ref:
                extra["ref_audio_path"] = ref
                extra["ref_audio_node"] = c.ref_audio_node"""
new = """        extra = _extra(ctx)
        if plan:
            extra["ref_pictures"] = plan
        if c.native_audio:
            ref = _reference_audio(ctx, shot)
            if ref:
                extra["ref_audio_path"] = ref
                extra["ref_audio_node"] = c.ref_audio_node"""
assert old in s, "extra 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("visual.py: 参考图清单 + 闸门")

# 2) the config: the switch
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    native_audio: bool = False"""
new = """    native_audio: bool = False
    # 每个视频都带上参考图（角色资产图、场景图、本镜首帧），参考图不齐就不抽卡
    video_references: bool = True"""
assert old in s, "config 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py: video_references")

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = "  native_audio: true"
new = """  native_audio: true
  video_references: true                    # 每个视频都带参考图；不齐就不抽卡"""
assert old in s, "yaml 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml: video_references")
