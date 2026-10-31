"""The director's rules come from the skill, not from code."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\storyboard.py")
s = p.read_text(encoding="utf-8")

old = """            from ..skills.film import DIRECTOR_RULES
            # how long this scene is, and how long a segment of it is on"""
new = """            from ..skills import loader as _loader
            from ..skills.film import DIRECTOR_RULES
            _rules = DIRECTOR_RULES + _loader.for_stage(ctx, "storyboard")
            # how long this scene is, and how long a segment of it is on"""
assert old in s, "导入锚点没找到"
s = s.replace(old, new, 1)

old2 = """                            director_rules=DIRECTOR_RULES,"""
new2 = """                            director_rules=_rules,"""
assert old2 in s, "director_rules 锚点没找到"
s = s.replace(old2, new2, 1)

p.write_text(s, encoding="utf-8")
print("storyboard.py: 导演的规矩来自 skill")
