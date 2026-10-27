"""Give the H3 prompt the three things the official guide insists on.

  * a timeline that matches the length of the clip
  * the references each given a job
  * the rules that stop the drift, written at the end where they work
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\prompts\templates.py")
s = p.read_text(encoding="utf-8")

old = """镜头：{{shot_type}} / 运镜 {{camera_move}}
画面：{{action}}"""
new = """镜头：{{shot_type}} / 运镜 {{camera_move}}（本镜约 {{duration}} 秒）
画面：{{action}}"""
assert old in s, "镜头行锚点没找到"
s = s.replace(old, new, 1)

old = """{{dialogue_note}}

要求："""
new = """{{dialogue_note}}

**参考图的分工**：
{{references}}

**时间轴（必须与 {{duration}} 秒一致）**：
{{timeline}}

要求："""
assert old in s, "dialogue_note 锚点没找到"
s = s.replace(old, new, 1)

old = """- 描述里不要提及画幅比例，"TARGET CANVAS" 之类的词也不要出现
{% if end_frame %}- end_prompt:"""
new = """- 描述里不要提及画幅比例，"TARGET CANVAS" 之类的词也不要出现
{% if end_frame %}- end_prompt:"""
assert old in s, "要求锚点没找到"

# the constraints go at the very end of the description, where they stop the
# drift best
old = """输出JSON：
{"integrated_multimodal_description":"","overall_soundscape":"","non_diegetic_music":""}"""


def new_block(marker):
    return marker + """

{{constraints}}"""


assert old in s, "输出JSON 锚点没找到"
s = s.replace(old, new_block(old), 1)

p.write_text(s, encoding="utf-8")
print("templates.py 已打补丁")
