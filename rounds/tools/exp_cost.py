"""How much does a segment cost?

The same picture in a shorter segment is not twice the price: the model
pays for the tokens of every frame, and the attention between them grows
faster than the frames do.  So the same five minutes cost less when it is
cut into more, shorter segments - and a segment of six to eight seconds is
what the format asks for anyway.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.refs import picture_plan
from dramakit.project import ProjectStore

frames = int(sys.argv[1]) if len(sys.argv) > 1 else 124
shot_id = sys.argv[2] if len(sys.argv) > 2 else "sh-428137b3"

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母"))
ctx = Context(cfg, store)
ep = ctx.project.episodes[0]
sc = ep.scenes[0]
shot = next(sh for sh in sc.shots if sh.id == shot_id)
plan = picture_plan(ctx, shot, sc)

out = Path(r"C:\\tmp") / f"timing_{frames}.mp4"
t0 = time.time()
ctx.providers.visual.generate_video(
    prompt=shot.video_prompt, negative=shot.negative_prompt,
    image_path="", frames=frames, fps=24, seed=181037156, out_path=str(out),
    extra={"ref_pictures": [p for p, _r, _k in plan]})
dt = (time.time() - t0) / 60
print(f"{frames} 帧（{frames/24:.1f} 秒）用时 {dt:.1f} 分钟 "
      f"= {dt*60/frames:.2f} 秒/帧；一集 300 秒要 "
      f"{dt/frames*300/60:.1f} 小时")
