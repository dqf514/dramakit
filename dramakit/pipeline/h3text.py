"""The description is English, except for the line that is spoken.

The model has a habit of ending the description with a Chinese
paragraph of constraints - "不要出现多余人物、多余肢体或畸形的手、镜头
不抖动…" - and the sampler has no negative branch, so every one of
those words goes into the picture.  It is in the model's weights, not
in our files: deleting it from every file we have does not stop it.

So it is taken out of the answer.  The Chinese that is allowed is the
line the character speaks, and that is inside the <d> tags.
"""
import re

# the dialogue, which is the only Chinese that belongs in the description
_D_TAG = re.compile(r"(<d>\[zh-CN\].*?</d>)", re.S)

# Chinese characters and the punctuation that goes with them
_CJK = re.compile(r"[\u4e00-\u9fff　-〿＀-￯]+")


def english_only(desc: str) -> str:
    """The description without the Chinese that is not the dialogue."""
    if not desc:
        return ""
    parts = _D_TAG.split(desc)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # inside the <d> tags: the line itself, verbatim
            out.append(part)
        else:
            out.append(_CJK.sub(" ", part))
    text = "\n".join(out)
    # the empty lines the removal leaves behind
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
