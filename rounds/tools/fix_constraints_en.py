"""The constraints in English.

The description is written in English and the constraints that close it
were in Chinese - a model reading a nine thousand character prompt should
not be asked to switch language at the end of it.  The dialogue stays in
Chinese: those are the words somebody has to say.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")

old_start = s.find('H3_CONSTRAINTS = (')
assert old_start > 0, "没找到 H3_CONSTRAINTS"
old_end = s.find('\n)\n', old_start)
assert old_end > 0, "没找到结尾"
old = s[old_start:old_end + 2]

new = '''H3_CONSTRAINTS = (
    "Keep the identity of every person exactly as in the reference pictures - "
    "the face, the hair and the clothes. No new text appears anywhere in the "
    "frame, no captions and no watermark. No extra people, no extra limbs and "
    "no malformed hands. The camera does not shake, the picture does not jump "
    "and there is no slow motion. Do not cut to another room or to another "
    "camera position inside this shot. The proportions of every face stay "
    "the same: the face does not lengthen, narrow or fatten, and the shape of "
    "the eyes and the mouth does not change. The people move little - small "
    "expressions, glances and breaths, no large turns, no walking, no violent "
    "action. The camera moves smoothly: no sudden acceleration and no whip.")'''

s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py: H3 的约束块改成英文")

# and the prompt that tells the model to write it
t = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
u = t.read_text(encoding="utf-8")
if "- **integrated_multimodal_description 的最后要原样带上这些约束**（写在描述的结尾）" in u:
    u = u.replace(
        "- **integrated_multimodal_description 的最后要原样带上这些约束**（写在描述的结尾）",
        "- **the constraints go at the end of the description, unchanged (in English)**",
        1)
    t.write_text(u, encoding="utf-8")
    print("templates.py: 那条要求也改成英文")
