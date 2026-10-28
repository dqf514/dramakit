"""One table, one colour scheme.

The location's own description said "warm wood and dark marble table",
so every shot picked one and the couple's table changed material from
one cut to the next. The description has to name one of everything and
say where the fixed things are.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
proj = store.load()
for loc in proj.locations:
    loc.visual_prompt = (
        "Upscale modern city cafe meeting area, one single dark walnut "
        "wood table with a matte finish, floor-to-ceiling windows along the "
        "right side of the frame, a grey upholstered banquette along the "
        "left, two white ceramic cups of black coffee on the table, a silver "
        "diamond ring lying on the table between the two seats, soft "
        "afternoon daylight through the windows, restrained luxury, "
        "photorealistic")
    print(f"{loc.name}: 场景设定已改成一个材质")
store.save(proj)
