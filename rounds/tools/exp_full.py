"""One full segment at a given setting, for comparison with the others."""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.refs import picture_plan
from dramakit.project import ProjectStore

steps = int(sys.argv[1])
size = sys.argv[2]
ref_size = sys.argv[3] if len(sys.argv) > 3 else "max"
shot_id = sys.argv[4] if len(sys.argv) > 4 else "sh-428137b3"
frames = int(sys.argv[5]) if len(sys.argv) > 5 else 243
W, H = (int(x) for x in size.split("x"))

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
cfg.comfyui.video_width = W
cfg.comfyui.video_height = H
for node in cfg.comfyui.nodes:
    if node.name == "gpu3090-a":
        node.graph_overrides = {**(node.graph_overrides or {}),
                               "9": {"steps": steps},
                               "104": {"ref_image_size": ref_size}}
store = ProjectStore(Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母"))
ctx = Context(cfg, store)
sc = ctx.project.episodes[0].scenes[0]
shot = next(sh for sh in sc.shots if sh.id == shot_id)
plan = picture_plan(ctx, shot, sc)

out = Path(r"C:\\tmp") / f"full_s{steps}_{size.replace('x','_')}_{ref_size}.mp4"
t0 = time.time()
ctx.providers.visual.generate_video(
    prompt=shot.video_prompt, negative=shot.negative_prompt,
    image_path="", frames=frames, fps=24, seed=181037156, out_path=str(out),
    extra={"ref_pictures": [p for p, _r, _k in plan]})
print(f"{steps} 步 {size} {ref_size} {frames}帧: {(time.time()-t0)/60:.1f} 分钟 -> {out}")
