"""A skill's name is the path with forward slashes, and a project can choose.

Two things. The catalog built names with str(Path), which on Windows is
backslashes - so a skill chosen in the page would not match the name in
the config, which uses the forward slash every other place does. And a
choice was global or nothing: every project with the same genre got the
same rules, which is wrong for a revenge thriller and a sweet romance
that happen to share a word.

A project can now say which skills a stage writes with, and for_stage
asks the project first. An empty list means none, which is a real answer
and not the same as not having decided.
"""
from pathlib import Path

# --------------------------------------------------- 1. forward slashes --
c = Path(r"E:\\dramakit\\dramakit\\skills\\catalog.py")
s = c.read_text(encoding="utf-8")
old = '            "name": str(rel),'
new = '            "name": rel.as_posix(),'
assert old in s, "name 那行没找到"
c.write_text(s.replace(old, new, 1), encoding="utf-8")
print("catalog.py: name 用正斜杠")

# ------------------------------------- 2. a project can hold its choice --
m = Path(r"E:\\dramakit\\dramakit\\models.py")
t = m.read_text(encoding="utf-8")
if "skills: dict[str, list[str]]" not in t:
    anchor = "    segmented_chapters: list[int] = []"
    assert anchor in t, "meta 锚点没找到"
    t = t.replace(anchor, anchor + '''
    # which skills each stage writes with, for this project alone. Empty
    # means none for that stage - a decision, not an absence - and a stage
    # with no entry here falls back to the config's list.
    skills: dict[str, list[str]] = {}''', 1)
    m.write_text(t, encoding="utf-8")
    print("models.py: meta.skills 字段")

# ------------------------------------- 3. for_stage asks the project ----
l = Path(r"E:\\dramakit\\dramakit\\skills\\loader.py")
u = l.read_text(encoding="utf-8")
old_for = '''    cfg = getattr(ctx.cfg, "skills", None)
    names = list(getattr(cfg, stage, None) or [])'''
new_for = '''    cfg = getattr(ctx.cfg, "skills", None)
    # The project's own choice first: two dramas that share a genre word
    # need not share their rules, and a project that decided against a
    # skill for this stage means none - which is why the check is for a
    # key that exists rather than for a list that is full.
    project_sel = {}
    try:
        project_sel = ctx.project.meta.skills or {}
    except Exception:  # noqa: BLE001
        project_sel = {}
    if stage in project_sel:
        names = list(project_sel.get(stage) or [])
    else:
        names = list(getattr(cfg, stage, None) or [])'''
assert old_for in u, "for_stage 锚点没找到"
l.write_text(u.replace(old_for, new_for, 1), encoding="utf-8")
print("loader.py: 项目级技能选择优先")
