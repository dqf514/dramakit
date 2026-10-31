"""Run the fix on a prompt that is missing a line and see what happens."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _dialogue_by_shot, _line_windows, _said
from dramakit.project import ProjectStore

root = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\\tmp\\ep23")
ep_index = int(sys.argv[2]) if len(sys.argv) > 2 else 2
shot_id = sys.argv[3] if len(sys.argv) > 3 else "sh-725b076a"
cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(root))
ep = ctx.project.episode(ep_index)
dlg = _dialogue_by_shot(ctx, ep)
shot = next(s for sc in ep.scenes for s in sc.shots if s.id == shot_id)
lines = dlg.get(shot_id, [])
print("分到的台词:", lines)
vp = shot.video_prompt or ""
body = vp[vp.find("detailed_description:"):]
print("native_audio:", ctx.cfg.comfyui.native_audio)
print("windows:", _line_windows(shot, lines))
for (start, end, spk, txt) in _line_windows(shot, lines):
    print(f"  「{txt}」 说过了吗: {_said(body, txt)}")
