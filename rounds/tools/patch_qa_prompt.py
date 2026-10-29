"""The prompt has to ask for the performance.

When the H3 prompt went missing, the video stage fell back to the picture
prompt - a scene description with no dialogue tag - and the model read
the actions out loud as a voice over. The check is simple: a shot with a
line has to have the line in its prompt.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\qa.py")
s = p.read_text(encoding="utf-8")

old = """def check_framing(ctx, ep, tl, issues):"""
new = '''def check_prompt_has_line(ctx, ep, tl, issues):
    """A shot with a line has to ask for it in the prompt.

    Without the dialogue tag the model gets a scene description and
    narrates it - the actions come out as a voice over.
    """
    rows = []
    for ts in tl.shots:
        shot = ts.shot
        if not shot.video_prompt:
            continue
        has_line = any(t.line.kind.value == "dialogue"
                       and ts.start - 0.02 <= t.start < ts.start + ts.duration
                       for t in tl.lines)
        if not has_line:
            continue
        if "<d>" not in shot.video_prompt:
            rows.append({"shot": shot.id,
                         "same_as_picture": shot.video_prompt == (shot.prompt or "")})
    if rows:
        same = sum(1 for r in rows if r["same_as_picture"])
        issues.append(("story", "prompt_without_line", "-",
                       f"{len(rows)} 个镜头的提示词里没有台词标签"
                       f"（其中 {same} 个直接用了出图提示词），"
                       "模型会把动作当旁白念出来"))
    return {"missing": len(rows), "rows": rows[:8]}


def check_framing(ctx, ep, tl, issues):'''
assert old in s, "锚点没找到"
s = s.replace(old, new, 1)

old = """        e["framing"] = check_framing(ctx, ep, tl, issues)"""
new = """        e["framing"] = check_framing(ctx, ep, tl, issues)
        e["prompt_line"] = check_prompt_has_line(ctx, ep, tl, issues)"""
assert old in s, "调用锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("qa.py 已改（提示词里必须有台词标签）")
