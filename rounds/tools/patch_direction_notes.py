"""The performance notes do not go in the text.

The polish pass was taught with examples that had the stage direction
inside the line - "（环顾四周）" - and it copied them.  The text is
what the voice model says and what the subtitle shows, so a note in it
is a note the audience reads out loud.

So the examples carry the note in the emotion field where it belongs,
and the parser takes any that slip through out of the text: what is
left of the line is what gets said.
"""
import pathlib
import re

ROOT = pathlib.Path(r"E:\dramakit")


def edit(path, old, new, what):
    p = ROOT / path
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    assert old in text, "没找到：%s（%s）" % (what, path)
    text = text.replace(old, new, 1)
    if crlf:
        text = text.replace("\n", "\r\n")
    p.write_bytes(text.encode("utf-8"))


# 1. the examples: the note goes in the emotion field
edit("dramakit/prompts/templates.py",
     """对照着磨（这是要达到的效果，不是要照抄）：

差：「这是哪儿？」「您自己的卧室。」
好：「这是哪儿……（环顾）这不是我房间。」「太太，这是您的卧室。」

差：「沈总是谁？」「您丈夫，沈律。」
好：「沈总？」（她心口一跳）「谁姓沈。」「太太，您说笑了，夫人也姓沈。」

差：「程菲是谁？」「沈总的新秘书。」
好：「程菲？」（她攥紧杯壁）「这个名字……她是谁？」
「新来的秘书，沈总很看重。」「看重？」陈嫂的手顿了一下，「太太，您今天问得太多了。」""",
     """对照着磨（这是要达到的效果，不是要照抄）：

差：「这是哪儿？」「您自己的卧室。」
好：「这不是我房间……」「太太，这是您的卧室。」

差：「沈总是谁？」「您丈夫，沈律。」
好：「沈总？谁姓沈。」「太太，您说笑了，夫人也姓沈。」

差：「程菲是谁？」「沈总的新秘书。」
好：「这个名字……她是谁？」「新来的秘书，沈总很看重。」
「看重？」陈嫂的手顿了一下，「太太，您今天问得太多了。」

**表演提示（端着、躲开、攥紧、发抖）写进 emotion 字段，不要写进 text**——
text 会被配音念出来，也会变成字幕。""",
     "the examples")

# 2. and the parser takes any that slip through out of the text
edit("dramakit/pipeline/script.py",
     """def _to_kind(v: str) -> LineKind:""",
     '''# A note in brackets is a note for the actor: 端着、躲开、攥紧.  The text
# is what the voice says and what the subtitle shows, so a note that
# slipped into it is taken back out.  What is left is what gets said.
_DIRECTION = re.compile(r"[（(][^）)]{0,40}[）)]")


def _strip_direction(text: str) -> str:
    out = _DIRECTION.sub("", text or "")
    return out.strip()


def _to_kind(v: str) -> LineKind:''',
     "the stripper")

edit("dramakit/pipeline/script.py",
     """            for li, l in enumerate(s.get("lines", []) or [], 1):
                txt = (l.get("text") or "").strip()
                if not txt:
                    continue
                sc.lines.append(Line(id=_id("ln"), kind=_to_kind(l.get("kind", "dialogue")),
                                     speaker=(l.get("speaker") or "旁白").strip(),
                                     text=txt, emotion=l.get("emotion", "平静")))""",
     """            for li, l in enumerate(s.get("lines", []) or [], 1):
                txt = _strip_direction(l.get("text") or "")
                if not txt:
                    continue
                emotion = (l.get("emotion") or "平静").strip()
                # a note that was in the text is not lost: it goes into the
                # emotion field, where the performance notes belong
                for note in _DIRECTION.findall(l.get("text") or ""):
                    note = note.strip("（）() ")
                    if note and note not in emotion:
                        emotion = (emotion + "，" + note) if emotion != "平静" else note
                sc.lines.append(Line(id=_id("ln"), kind=_to_kind(l.get("kind", "dialogue")),
                                     speaker=(l.get("speaker") or "旁白").strip(),
                                     text=txt, emotion=emotion))""",
     "the parser")

print("表演提示回到 emotion 里了")
