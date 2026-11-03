"""The stages that were not asked whether to stop.

The stop was wired into six stages and missed these two, so a run in the
analysis or the casting ignored it completely: the event was set, nobody
looked, and the pictures kept coming - into a folder for a season that
should not have been drawing at all.

Both now ask. The casting asks between views rather than between
characters, because a view is twenty seconds of a card and a character is
five views - a stop should land in seconds, not at the end of a face.
"""
from pathlib import Path

# ------------------------------------------------------- character ------
c = Path(r"E:\\dramakit\\dramakit\\pipeline\\character.py")
s = c.read_text(encoding="utf-8")

if "ctx.check_stop()" not in s:
    # before each expensive step of the stage
    old = '''    anchors = build_anchors(ctx, chars)'''
    new = '''    ctx.check_stop()   # 一步一问：停止能在下一个动作生效
    anchors = build_anchors(ctx, chars)'''
    assert old in s, "build_anchors 锚点没找到"
    s = s.replace(old, new, 1)

    old2 = '''    anchors += differentiate_characters(ctx, [c for c in chars if not c.locked])'''
    new2 = '''    ctx.check_stop()
    anchors += differentiate_characters(ctx, [c for c in chars if not c.locked])'''
    assert old2 in s, "differentiate 锚点没找到"
    s = s.replace(old2, new2, 1)

    old3 = '''    casted = cast_voices(ctx, chars)'''
    new3 = '''    ctx.check_stop()
    casted = cast_voices(ctx, chars)'''
    assert old3 in s, "cast_voices 锚点没找到"
    s = s.replace(old3, new3, 1)

    # and between views: one face is five pictures, twenty seconds each
    old4 = '''    for view in views:
        out = ctx.store.character_ref_path(c.name, view, "png", season=season)'''
    new4 = '''    for view in views:
        ctx.check_stop()   # 一图一问：一张约 24 秒
        out = ctx.store.character_ref_path(c.name, view, "png", season=season)'''
    assert old4 in s, "views 循环锚点没找到"
    s = s.replace(old4, new4, 1)

    c.write_text(s, encoding="utf-8")
    print("character.py: 加了停止检查（阶段内 + 每张图）")
else:
    print("character.py: 已有检查")

# --------------------------------------------------------- analyze -------
a = Path(r"E:\\dramakit\\dramakit\\pipeline\\analyze.py")
t = a.read_text(encoding="utf-8")
if "ctx.check_stop()" not in t:
    old = '''    llm = ctx.providers.llm_for("analyze")'''
    new = '''    ctx.check_stop()
    llm = ctx.providers.llm_for("analyze")'''
    assert old in t, "analyze 的 llm 锚点没找到"
    t = t.replace(old, new, 1)
    # and after the call, before anything is written
    old2 = '''    # art direction: this season's, falling back to what the canon holds'''
    new2 = '''    ctx.check_stop()
    # art direction: this season's, falling back to what the canon holds'''
    assert old2 in t, "analyze 写入前锚点没找到"
    t = t.replace(old2, new2, 1)
    a.write_text(t, encoding="utf-8")
    print("analyze.py: 加了停止检查")
else:
    print("analyze.py: 已有检查")
