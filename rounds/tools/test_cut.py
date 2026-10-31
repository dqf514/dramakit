"""Does the model cut when the prompt says where?

One segment, the cut markers put in from the director's own times, and
the cuts measured on the result.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _internal_cuts, _r2v_header
from dramakit.pipeline.refs import picture_plan
from dramakit.pipeline.visual import regen_shot
from dramakit.project import ProjectStore

root = Path(r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
shot_id = sys.argv[1] if len(sys.argv) > 1 else "sh-428137b3"
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.project.episodes[0]
sc = next(s for s in ep.scenes if any(sh.id == shot_id for sh in s.shots))
shot = next(sh for sh in sc.shots if sh.id == shot_id)

cuts = _internal_cuts(shot)
vp = shot.video_prompt or ""
body = vp[vp.rfind("detailed_description:") + len("detailed_description:"):]
marks = [f"At {at:06.3f}, the camera cuts to [Shot {i}]: a different framing of the "
         f"same moment - a different size of shot and a different angle on the "
         f"people - the action carrying on and the light unchanged."
         for i, (at, _e) in enumerate(cuts[1:], 2)]
shot.video_prompt = _r2v_header(picture_plan(ctx, shot, sc)) + body.rstrip() + "\n" + "\n".join(marks)
ctx.save()
print("切点标记:", [(round(a, 2), round(b, 2)) for a, b in cuts])

t0 = time.time()
res = regen_shot(ctx.store, cfg, 1, shot_id, mode="video")
print(f"渲染: ok={res.get('ok')} 用时 {(time.time()-t0)/60:.1f} 分钟")

p = ctx.store.root / "video" / f"shot_{shot_id}.mp4"
if p.exists():
    from dramakit.ref_rhythm import analyse
    r = analyse(p)
    print("片段里的镜头数:", r.get("shots"), "| 平均", r.get("avg_shot"), "秒 | 切点:",
          [round(t, 2) for t in (r.get("cut_times") or [])])
