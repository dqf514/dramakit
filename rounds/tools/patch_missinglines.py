"""A line that is not in the prompt is a line nobody says.

The model that writes the H3 description drops a line now and then: three
of the thirty-three segments of the first episode came back without the
words they were supposed to speak, and the video model had nothing to say
in them.

So the code checks, and the code fixes: every line the shot carries has to
be in the prompt, inside the dialogue tag, and the ones the model left out
are written back in with the moment they belong to.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")

# --------------------------------------------------------------------------- #
# 1. the windows the lines get inside the segment
# --------------------------------------------------------------------------- #
old = '''def _shot_timeline(shot, lines) -> str:
    """The beat by beat timeline, matching the length of the clip.

    The segments follow the length of each recording, not an even split:
    a gesture has to happen while its own sentence is being said.
    """
    dur = _shot_seconds(shot)
    if not lines:
        return (f"0-{dur:.1f}秒：{shot.action[:40]}，角色不说话，"
                "只用表情、眼神和动作推进")
    out = []
    at = 0.0
    for spk, _txt, d in lines[:4]:
        length = float(d) if d and d > 0 else 0.0
        if length <= 0:
            length = dur / len(lines)
        # the model speaks slower than the recording, so the line gets a
        # little more room than it needs, and it is told to finish in it
        window = length * 1.15 + 0.15
        out.append(f"{at:.1f}-{at + window:.1f}秒：{spk} 开口说这句台词"
                   f"（**在这段时间里说完，不要拖到后面**）")
        at += window'''

new = '''def _line_windows(shot, lines) -> list[tuple[float, float, str, str]]:
    """When each line is spoken inside the segment: (start, end, who, what).

    The lines follow the length of their own recording, not an even split:
    a gesture has to happen while its own sentence is being said.
    """
    dur = _shot_seconds(shot)
    out: list[tuple[float, float, str, str]] = []
    at = 0.0
    for spk, txt, d in (lines or [])[:4]:
        length = float(d) if d and d > 0 else 0.0
        if length <= 0:
            length = dur / max(1, len(lines))
        # the model speaks slower than the recording, so the line gets a
        # little more room than it needs, and it is told to finish in it
        window = length * 1.15 + 0.15
        out.append((round(at, 2), round(at + window, 2), spk, txt))
        at += window
    return out


def _bare(text: str) -> str:
    """The words of a line, without the punctuation and the spacing."""
    return re.sub(r"[^0-9A-Za-z\\u4e00-\\u9fff]+", "", text or "")


def _said(desc: str, text: str) -> bool:
    """Is this line already in the description?"""
    if not text:
        return True
    if text in desc:
        return True
    return bool(_bare(text)) and _bare(text) in _bare(desc)


def _shot_timeline(shot, lines) -> str:
    """The beat by beat timeline, matching the length of the clip."""
    dur = _shot_seconds(shot)
    if not lines:
        return (f"0-{dur:.1f}秒：{shot.action[:40]}，角色不说话，"
                "只用表情、眼神和动作推进")
    out = []
    at = 0.0
    for spk, _txt, d in lines[:4]:
        length = float(d) if d and d > 0 else 0.0
        if length <= 0:
            length = dur / len(lines)
        # the model speaks slower than the recording, so the line gets a
        # little more room than it needs, and it is told to finish in it
        window = length * 1.15 + 0.15
        out.append(f"{at:.1f}-{at + window:.1f}秒：{spk} 开口说这句台词"
                   f"（**在这段时间里说完，不要拖到后面**）")
        at += window'''
assert old in s, "shot_timeline 锚点没找到"
s = s.replace(old, new, 1)

# --------------------------------------------------------------------------- #
# 2. the lines the model left out are written back in
# --------------------------------------------------------------------------- #
old = """        desc = str(h3.get("integrated_multimodal_description") or "").strip()
        soundscape = str(h3.get("overall_soundscape") or "").strip()
        music = str(h3.get("non_diegetic_music") or "").strip()
        if desc:"""
new = """        desc = str(h3.get("integrated_multimodal_description") or "").strip()
        soundscape = str(h3.get("overall_soundscape") or "").strip()
        music = str(h3.get("non_diegetic_music") or "").strip()
        # A line that is not in the prompt is a line nobody says.  The model
        # that writes the description drops one now and then, so the ones it
        # left out are written back in with the moment they belong to.
        if desc and ctx.cfg.comfyui.native_audio and lines:
            windows = _line_windows(shot, lines)
            add = []
            for (start, end, spk, txt) in windows:
                if _said(desc, txt):
                    continue
                add.append(f"From {start:.1f} to {end:.1f} seconds, {spk} opens "
                           f"their mouth and speaks, the lips moving with every "
                           f"syllable: <d>[zh-CN]{txt}</d>")
            if add:
                desc = desc.rstrip() + "\\n" + "\\n".join(add)
        if desc:"""
assert old in s, "H3 描述锚点没找到"
s = s.replace(old, new, 1)

if "\nimport re\n" not in s:
    s = s.replace("import json\n", "import json\nimport re\n", 1)

p.write_text(s, encoding="utf-8")
print("promptgen.py: 漏掉的台词会按时间点补回提示词")
