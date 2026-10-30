"""Get episodes two and three ready.

Their shot lists came from the first storyboard, so their segments are still
the old three-second ones, and one of the rooms they happen in has no
picture yet - a scene without a room picture is a scene whose shots cannot
be rendered at all.

This adds the missing rooms and clears the old segments so the director can
do them again with the new rule: a segment is six to fifteen seconds, and
the episode is five minutes long.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.models import Location, Status
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
eps = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [2, 3]

store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
proj = store.load()

# the rooms the script puts a scene in, and what they look like
ROOMS = {
    "卧室": ("A modern luxury bedroom in a Chinese mansion at night. A low platform "
             "bed with pale grey linen, floor-to-ceiling black-framed windows with "
             "city lights beyond, warm bedside lamps, dark walnut furniture, a single "
             "brass floor lamp, muted charcoal and warm grey palette.",
             "The bedroom of a wealthy man: a low bed, dark wood, big windows, "
             "night outside, warm lamps."),
    "卧室窗外": ("The view from a floor-to-ceiling window of a modern Chinese mansion "
                 "bedroom at night: a rain-wet courtyard far below, wet stone paths, "
                 "a car with its headlights on, dark trees and a black sky, seen "
                 "slightly from above, cold blue and grey tones against warm window "
                 "light from inside.",
                 "What you see out of the window of a mansion bedroom at night: a "
                 "rainy courtyard, wet ground, headlights."),
}

added = []
for name_, (vp, desc) in ROOMS.items():
    if any(l.name == name_ for l in proj.locations):
        continue
    proj.locations.append(Location(name=name_, description=desc, visual_prompt=vp))
    added.append(name_)
print("新增房间资产:", added or "（没有）")

n = 0
for ep in proj.episodes:
    if ep.index not in eps:
        continue
    for sc in ep.scenes:
        n += len(sc.shots)
        sc.shots = []
        sc.status = Status.PENDING
        if hasattr(sc, "_shot_budget"):
            del sc._shot_budget
    for k in ("storyboard", "promptgen", "visual"):
        ep.stage_status.pop(k, None)
store.save(proj)
print(f"第 {eps} 集清掉 {n} 个旧镜头，可以重做分镜")
for ep in proj.episodes:
    if ep.index in eps:
        print(f"  第{ep.index}集 {ep.title}："
              + "、".join(sorted({sc.location for sc in ep.scenes})))
