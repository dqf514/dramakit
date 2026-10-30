"""Put the two skills' rules where the models actually read them."""
from pathlib import Path

# 1) the script prompt carries the screenwriter's rules
p = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
s = p.read_text(encoding="utf-8")
old = """原文：
\\"\\"\\"
{{text}}
\\"\\"\\"

输出JSON格式：
{"scenes":[{"location":"","time_of_day":"日","summary":"","mood":"","lines":[{"kind":"dialogue","speaker":"","text":"","emotion":"平静"}]}]}\"\"\""""
new = """原文：
\\"\\"\\"
{{text}}
\\"\\"\\"

{{screenwriter_rules}}

输出JSON格式：
{"scenes":[{"location":"","time_of_day":"日","summary":"","mood":"","lines":[{"kind":"dialogue","speaker":"","text":"","emotion":"平静"}]}]}\"\"\""""
assert old in s, "SCRIPT_USER 尾部锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("templates.py: 编剧规矩进了剧本提示词")

# 2) the storyboard prompt carries the director's rules
p = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
s = p.read_text(encoding="utf-8")
old = """输出JSON格式：
{"shots":[{"shot_type":"中景","camera_move":"固定","duration":3.0,"action":"","characters":[""],"lines":[1]}]}\"\"\""""
new = """{{director_rules}}

输出JSON格式：
{"shots":[{"shot_type":"中景","camera_move":"固定","duration":3.0,"action":"","characters":[""],"lines":[1]}]}\"\"\""""
assert old in s, "STORYBOARD_USER 尾部锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("templates.py: 导演规矩进了分镜提示词")

# 3) the two stages pass the rules in
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\script.py")
s = p.read_text(encoding="utf-8")
old = """        user = T.render(T.SCRIPT_USER, genre=genre, min_scenes=2, max_scenes=8,"""
new = """        from ..skills.film import SCREENWRITER_RULES
        user = T.render(T.SCRIPT_USER, genre=genre, min_scenes=2, max_scenes=8,
                        screenwriter_rules=SCREENWRITER_RULES,"""
assert old in s, "script render 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("script.py: 编剧规矩传进去了")

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
