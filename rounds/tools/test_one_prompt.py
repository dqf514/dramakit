"""One shot's prompt, written by the model with the new instruction."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _dialogue_by_shot, _gen_h3_prompt, _char_visuals
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1
            else r"E:\\dramakit\\projects\\短剧_重生恶毒继母")
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 1
shot_id = sys.argv[3] if len(sys.argv) > 3 else "sh-428137b3"
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.project.episode(ep_index)
sc = next(s for s in ep.scenes if any(sh.id == shot_id for sh in s.shots))
shot = next(sh for sh in sc.shots if sh.id == shot_id)

dlg = _dialogue_by_shot(ctx, ep)
visuals = _char_visuals(ctx, shot)
loc = None
from dramakit.pipeline.refs import find_location
loc = find_location(ctx, sc.location)
loc_visual = (loc.visual_prompt or loc.description) if loc else ""
llm = ctx.providers.llm_for("promptgen")
_gen_h3_prompt(ctx, llm, shot, sc, visuals, loc_visual,
               dlg.get(shot_id, []), continuity="")

vp = shot.video_prompt or ""
print("有 [Shot 2]:", "[Shot 2]" in vp)
print("有切点标记:", "cuts to" in vp)
i = vp.find("detailed_description:")
print(vp[i:i + 1200])
ctx.save()
print("\n已保存")
