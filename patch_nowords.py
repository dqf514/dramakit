"""Take the spoken words out of the picture description.

The video model draws what it reads: a line of dialogue in the prompt
comes out as a caption burned into the picture - "我来", "就是撑给你看",
"三个月" in the middle of the frame. The words are the post-production
voice track's job; the picture only has to show the performance.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")

old = """def _speaker_note(shot: Shot, lines) -> str:"""
new = '''_QUOTED = re.compile(r"[“"\\"'‘’「」][^“”"\\"'‘’「」]{0,80}[”"\\"'‘’「」]")


def _action_without_words(action: str) -> str:
    """The action, with the spoken words taken out.

    The storyboard writes what the character says inside quotes, and both
    picture models draw those quotes as captions on the picture. The
    performance is what the picture needs; the words come from the voice
    track later.
    """
    text = _QUOTED.sub("", action or "")
    text = re.sub(r"(说|说道|问|问道|喊|答道|回答)\\s*[:：]?\\s*$", "", text)
    text = re.sub(r"[:：]\\s*$", "", text)
    text = re.sub(r"[，,]\\s*[，,]+", "，", text)
    text = re.sub(r"\\s{2,}", " ", text)
    return text.strip("，,、 ")


def _speaker_note(shot: Shot, lines) -> str:'''
assert old in s, "助手锚点没找到"
s = s.replace(old, new, 1)

if "\nimport re\n" not in s:
    s = s.replace("import time\n", "import re\nimport time\n", 1)

old = """                    camera_move=shot.camera_move, action=shot.action,"""
new = """                    camera_move=shot.camera_move,
                    action=_action_without_words(shot.action),"""
assert old in s, "出图锚点没找到"
s = s.replace(old, new, 1)

old = """            action=shot.action, character_anchors=visuals,"""
new = """            action=_action_without_words(shot.action), character_anchors=visuals,"""
assert old in s, "H3 锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("promptgen.py 已改（画面描述里去掉台词）")
