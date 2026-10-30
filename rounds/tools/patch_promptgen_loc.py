"""The prompt generator had the same literal-match bug as the reference gate.

The scene '酒店宴会厅·主舞台' never found its room asset, so the room
description never reached the prompt and the picture list stopped at the
character sheets - the prompt said "the style and place of <Picture 1>"
while the picture that actually held the place was not in the list at all.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")

old = """                loc = next((l for l in ctx.project.locations
                            if l.name == sc.location), None)"""
new = """                from .refs import find_location
                loc = find_location(ctx, sc.location)"""
assert old in s, "promptgen 的场景匹配锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py: 场景匹配改成解析式")
