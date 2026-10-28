"""The timeline H3 gets has to be the real one.

The segments were divided evenly among the lines, so a shot with one long
line and one short one put the action in the wrong place: the three
fingers went up while the other sentence was being said. The recording's
own length is the truth.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")

# 1) the dialogue map carries the measured length
old = """                    out.setdefault(ts.shot.id, []).append(
                        (tl_line.line.speaker, tl_line.line.text))"""
new = """                    out.setdefault(ts.shot.id, []).append(
                        (tl_line.line.speaker, tl_line.line.text,
                         float(tl_line.line.duration or 0.0)))"""
assert old in s, "对话表锚点没找到"
s = s.replace(old, new, 1)

old = """def _dialogue_by_shot(ctx: Context, ep) -> dict[str, list[tuple[str, str]]]:"""
new = """def _dialogue_by_shot(ctx: Context, ep) -> dict[str, list[tuple[str, str, float]]]:"""
assert old in s, "签名锚点没找到"
s = s.replace(old, new, 1)

# 2) the timeline uses it
old = '''def _shot_timeline(shot, lines) -> str:
    """The beat by beat timeline, matching the length of the clip."""
    dur = _shot_seconds(shot)
    if not lines:
        return (f"0-{dur:.1f}秒：{shot.action[:40]}，角色不说话，"
                "只用表情、眼神和动作推进")
    seg = dur / len(lines)
    out = []
    for i, (spk, _txt) in enumerate(lines[:4]):
        out.append(f"{i*seg:.1f}-{(i+1)*seg:.1f}秒：{spk} 开口说这句台词")
    if len(lines) > 4:
        out.append(f"之后到 {dur:.1f}秒：保持情绪与姿态")
    return "；".join(out)'''
new = '''def _shot_timeline(shot, lines) -> str:
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
        out.append(f"{at:.1f}-{at + length:.1f}秒：{spk} 开口说这句台词")
        at += length
    if at < dur - 0.05:
        out.append(f"{at:.1f}-{dur:.1f}秒：保持情绪与姿态")
    return "；".join(out)'''
assert old in s, "时间轴锚点没找到"
s = s.replace(old, new, 1)

# 3) the helpers that unpack the lines
old = """def _numbered_dialogue(lines: list[tuple[str, str]]) -> tuple[str, dict[str, str]]:
    \"\"\"Render dialogue with stable (Sx) speaker ids; return text + id map.\"\"\"
    ids: dict[str, str] = {}
    parts = []
    for speaker, text in lines:"""
new = """def _numbered_dialogue(lines: list[tuple]) -> tuple[str, dict[str, str]]:
    \"\"\"Render dialogue with stable (Sx) speaker ids; return text + id map.\"\"\"
    ids: dict[str, str] = {}
    parts = []
    for speaker, text, _d in lines:"""
assert old in s, "编号对话锚点没找到"
s = s.replace(old, new, 1)

old = """    speakers: list[str] = []
    for spk, _ in lines or []:"""
new = """    speakers: list[str] = []
    for spk, _t, _d in lines or []:"""
assert old in s, "说话人锚点没找到"
s = s.replace(old, new, 1)

old = """def _speaker_note(shot: Shot, lines) -> str:"""
new = """def _speaker_note(shot: Shot, lines) -> str:"""
assert old in s
p.write_text(s, encoding="utf-8")
print("promptgen.py 已改（时间轴用真实台词时长）")
