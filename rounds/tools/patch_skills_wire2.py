"""The two stages whose wiring did not land.

The patch that wired the four stages stopped at the first anchor it could
not find, so the reader and the prompt writers never got their skills.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")


def patch(path: str, pairs: list[tuple[str, str]]) -> None:
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s and old not in s:
            print(f"  {path}: 已经打过补丁了")
            continue
        assert old in s, f"{path}: 锚点没找到\n{old[:160]}"
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"  {path}: 改好了")


# analyze: the reader's rules come from the skill
patch("dramakit/pipeline/analyze.py", [
    ("""    user = T.render(T.ANALYZE_USER, text=sample, max_characters=12,
                    max_locations=10, max_props=8)""",
     """    from ..skills import loader
    user = T.render(T.ANALYZE_USER, text=sample, max_characters=12,
                    max_locations=10, max_props=8) + loader.for_stage(ctx, "analyze")"""),
])

# promptgen: the prompt writers' rules come from the skill
patch("dramakit/pipeline/promptgen.py", [
    ("""        h3_user = T.render(
            T.H3_VIDEO_USER,""",
     """        from ..skills import loader as _loader
        h3_user = T.render(
            T.H3_VIDEO_USER,"""),
    ("""            constraints=H3_CONSTRAINTS)""",
     """            constraints=H3_CONSTRAINTS + _loader.for_stage(ctx, "promptgen"))"""),
])
