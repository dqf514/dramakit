"""Same shot, same prompt, two transformers: which one holds the face?

    python rounds/tools/ab_ref2v.py 轮次09_09
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
shot_id = sys.argv[2] if len(sys.argv) > 2 else ""
out_dir = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\ab")
out_dir.mkdir(parents=True, exist_ok=True)

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(Path(r"E:\\dramakit\\projects") / name))
ep = ctx.target_episodes()[0]
vis = ctx.providers.visual
print("provider:", type(vis).__name__)

# the shot with the most face in it
cands = [sh for sc in ep.scenes for sh in sc.shots if sh.video_prompt]
if shot_id:
    cands = [s for s in cands if s.id == shot_id]
else:
    cands.sort(key=lambda s: 0 if s.shot_type.value in ("特写", "近景") else 1)
shot = cands[0]
print(f"镜头 {shot.id} {shot.shot_type.value} 时长 {shot.duration:.2f}s")
print("提示词前 200 字:", (shot.video_prompt or "")[:200].replace("\n", " "))

# the reference wording: the picture is the reference, not a first frame
R2V_ALIGN = ("For the target video, <Picture 1> is the reference: the person "
             "in <Picture 1> keeps their face, hair and clothes, and the shot "
             "is the one shown in <Picture 1>.")
prompt = (shot.video_prompt or "").replace(
    "For the target video, at 0.00 seconds into the target video, "
    "<Picture 1> (from [Shot 1]) is fully referenced.", R2V_ALIGN)

img = ctx.store.abs(shot.image_path)
frames = max(22, int(round(shot.duration * 24 / 17) * 17 + 5))
seed = 20260101

# 1) the reference transformer
cfg2 = copy.deepcopy(cfg)
cfg2.comfyui.i2v_workflow = "config/comfyui/i2v_minimax_h3_ref2v.json"
vis.cfg = cfg2
out_ref = out_dir / f"{shot.id}_ref2v.mp4"
print("提交 ref2va ...")
vis.generate_video(prompt, "", image_path=str(img), frames=frames, fps=24,
                   seed=seed, out_path=str(out_ref))
print("  ->", out_ref, out_ref.stat().st_size, "字节")

# 2) the first-frame transformer (the one we have been using)
cfg3 = copy.deepcopy(cfg)
cfg3.comfyui.i2v_workflow = "config/comfyui/i2v_minimax_h3.json"
vis.cfg = cfg3
out_fl2 = out_dir / f"{shot.id}_fl2va.mp4"
print("提交 fl2va ...")
vis.generate_video((shot.video_prompt or ""), "", image_path=str(img),
                   frames=frames, fps=24, seed=seed, out_path=str(out_fl2))
print("  ->", out_fl2, out_fl2.stat().st_size, "字节")
print("DONE", out_dir)
