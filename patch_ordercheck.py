"""Check that the dialogue is played back in the order it was written."""
from pathlib import Path

p = Path(r"E:\dramakit\qa.py")
s = p.read_text(encoding="utf-8")

old = """def check_speaker_on_screen(ctx, ep, tl, issues):"""
new = '''def check_line_order(ctx, ep, tl, issues):
    """The lines have to be spoken in the order they were written.

    The shots carry the lines, and the timeline places each line inside its
    shot, so a storyboard that hands a later line to an earlier shot plays
    the scene back with the answer before the question.
    """
    bad = []
    for sc in ep.scenes:
        order = [l for l in sc.lines if l.kind.value == "dialogue"]
        pos = {id(l): i for i, l in enumerate(order)}
        seq = [pos.get(id(t.line), -1) for t in tl.lines
               if t.line.kind.value == "dialogue"]
        seq = [s for s in seq if s >= 0]
        if seq != sorted(seq):
            bad.append(sc.scene.index)
    if bad:
        issues.append(("story", "lines_out_of_order", "-",
                       f"{len(bad)} 个场的台词顺序被打乱了（回答跑到了问题前面）："
                       + "、".join(f"场景{b}" for b in bad[:3])))
    return {"scenes_out_of_order": len(bad)}


def check_speaker_on_screen(ctx, ep, tl, issues):'''
assert old in s, "锚点没找到"
s = s.replace(old, new, 1)

old = """        e["story"] = check_speaker_on_screen(ctx, ep, tl, issues)"""
new = """        e["story"] = check_speaker_on_screen(ctx, ep, tl, issues)
        e["line_order"] = check_line_order(ctx, ep, tl, issues)"""
assert old in s, "story 调用锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("qa.py 已打补丁")
