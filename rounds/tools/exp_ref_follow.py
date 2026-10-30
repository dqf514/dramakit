"""Does the model follow the reference?  Four minutes instead of twenty.

A segment of twenty-two frames is one second of picture - long enough to
look at, short enough to try four ways of doing it in one sitting:

  * four steps with the turbo LoRA (what we run now)
  * eight steps with the turbo LoRA
  * the official single pass: the LoRA off, twenty steps
  * the official single pass with the references at their own size

The first frame of each result is put next to the still it was made from.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.refs import picture_plan
from dramakit.project import ProjectStore

steps = int(sys.argv[1]) if len(sys.argv) > 1 else 8
use_lora = (sys.argv[2] if len(sys.argv) > 2 else "yes") == "yes"
ref_size = sys.argv[3] if len(sys.argv) > 3 else "match"
shot_id = sys.argv[4] if len(sys.argv) > 4 else "sh-428137b3"

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母"))
ctx = Context(cfg, store)
ep = ctx.project.episodes[0]
sc = ep.scenes[0]
shot = next(sh for sh in sc.shots if sh.id == shot_id)

overrides = {"9": {"steps": steps}, "104": {"ref_image_size": ref_size}}
if not use_lora:
    overrides["121"] = {"strength_model": 0.0}
for node in cfg.comfyui.nodes:
    if node.name == "gpu3090-a":
        node.graph_overrides = {**(node.graph_overrides or {}), **overrides}

plan = picture_plan(ctx, shot, sc)
print(f"镜头 {shot.id} | 步数 {steps} | LoRA {'开' if use_lora else '关'} | "
      f"参考图尺寸 {ref_size}")
for i, (p, role, kind) in enumerate(plan, 1):
    print(f"   Picture {i}: {kind:<10} {Path(p).name}")

out = Path(r"C:\\tmp") / f"test_s{steps}_{'lora' if use_lora else 'nolora'}_{ref_size}.mp4"
vis = ctx.providers.visual
t0 = time.time()
vis.generate_video(
    prompt=shot.video_prompt, negative=shot.negative_prompt,
    image_path="", frames=22, fps=24, seed=181037156, out_path=str(out),
    extra={"ref_pictures": [p for p, _r, _k in plan],
           "ref_audio_path": str(ctx.store.root / "tmp" / f"refaudio_{shot.id}.wav")
           if (ctx.store.root / "tmp" / f"refaudio_{shot.id}.wav").exists() else "",
           "ref_audio_node": cfg.comfyui.ref_audio_node})
print(f"\n用时 {(time.time()-t0)/60:.1f} 分钟 -> {out}")
