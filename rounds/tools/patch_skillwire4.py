"""The director's rules into the storyboard prompt, and the stages pass them."""
from pathlib import Path

T = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
s = T.read_text(encoding="utf-8")
old = """输出JSON：
{"shots":[{"shot_type":"近景","camera_move":"推","duration":3.0,"action":"","characters":[],"lines":[1,2]}]}\"\"\""""
new = """{{director_rules}}

输出JSON：
{"shots":[{"shot_type":"近景","camera_move":"推","duration":3.0,"action":"","characters":[],"lines":[1,2]}]}\"\"\""""
assert old in s, "STORYBOARD_USER 尾部锚点没找到"
s = s.replace(old, new, 1)
T.write_text(s, encoding="utf-8")
print("templates.py: 导演规矩进了分镜提示词")

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\storyboard.py")
s = p.read_text(encoding="utf-8")
old = """            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景","""
new = """            from ..skills.film import DIRECTOR_RULES
            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            director_rules=DIRECTOR_RULES,"""
assert old in s, "storyboard render 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("storyboard.py: 导演规矩传进去了")
