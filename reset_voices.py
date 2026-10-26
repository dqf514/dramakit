"""Re-cast the voices and drop the old audio so the voice stage redoes it."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.project import ProjectStore

cfg = Config.load(r"E:\dramakit\config\default.yaml")
root = Path(r"E:\dramakit\projects\测试短剧")
store = ProjectStore(root)
proj = store.load()

n_cast = 0
for c in proj.characters:
    if c.voice_id:
        n_cast += 1
    c.voice_id = ""
    c.voice_pitch = ""
    c.voice_rate = ""

n_line = 0
for ep in proj.episodes:
    ep.stage_status.pop("voice", None)
    ep.stage_status.pop("subtitle", None)
    ep.stage_status.pop("compose", None)
    ep.stage_status.pop("qc", None)
    for sc in ep.scenes:
        for l in sc.lines:
            if l.audio_path:
                store.abs(l.audio_path).unlink(missing_ok=True)
                l.audio_path = ""
                l.duration = 0.0
                n_line += 1

store.save(proj)
print(f"清掉 {n_cast} 个角色的旧音色、{n_line} 句旧配音")
