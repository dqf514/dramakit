"""Does the storyboard model answer with the lines field?"""
import json
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.models import is_narration
from dramakit.prompts import templates as T
from dramakit.providers.llm import build_llm
from dramakit.project import ProjectStore
from dramakit.utils.text import estimate_reading_seconds

cfg = Config.load(r"E:\dramakit\config\default.yaml")
llm = build_llm(cfg.llm)
store = ProjectStore(r"E:\dramakit\projects\轮次01_01")
proj = store.load()
ep = proj.episodes[0]
sc = ep.scenes[0]

lines_text = "\n".join(f"- {i}. {l.speaker}({l.emotion}): {l.text}"
                       for i, l in enumerate(sc.lines, 1))
user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                time_of_day=sc.time_of_day, mood=sc.mood, summary=sc.summary,
                lines_text=lines_text, min_shots=2, max_shots=8,
                prefer_dynamic="以固定镜头为主", dur_min=2.0, dur_max=5.0,
                narration_seconds=round(sum(estimate_reading_seconds(l.text)
                                            for l in sc.lines), 1),
                character_names=", ".join(c.name for c in proj.characters))
data = llm.complete_json(T.STORYBOARD_SYSTEM, user)
if isinstance(data, list):
    data = data[0] if data else {}
for sh in data.get("shots", []):
    print(f"  {sh.get('shot_type'):<12} {str(sh.get('characters')):<22} "
          f"lines={sh.get('lines')}  {str(sh.get('action'))[:34]}")
