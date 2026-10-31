"""The stages write with the skills.

The rules used to live in code, written by hand and improved one round at
a time.  They are documents now - the skills in `skills/` and the
screenwriting theory beside them - and the stages load them at run time,
so a new skill is a new file and not a new patch.

The stage asks for what the config names; the genre asks for the theory
that suits the drama.
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


# --------------------------------------------------------------------------- #
# 1. script: the screenwriter's rules come from the skill
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/script.py", [
    ('''        from ..skills.film import SCREENWRITER_RULES
        user = T.render(T.SCRIPT_USER, genre=genre, min_scenes=2, max_scenes=8,
                        screenwriter_rules=SCREENWRITER_RULES,''',
     '''        from ..skills import loader
        from ..skills.film import SCREENWRITER_RULES
        rules = SCREENWRITER_RULES + loader.for_stage(ctx, "script")
        user = T.render(T.SCRIPT_USER, genre=genre, min_scenes=2, max_scenes=8,
                        screenwriter_rules=rules,'''),
])

# --------------------------------------------------------------------------- #
# 2. storyboard: the director's rules come from the skill
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/storyboard.py", [
    ('''            from ..skills.film import DIRECTOR_RULES
            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            director_rules=DIRECTOR_RULES,''',
     '''            from ..skills import loader
            from ..skills.film import DIRECTOR_RULES
            rules = DIRECTOR_RULES + loader.for_stage(ctx, "storyboard")
            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            director_rules=rules,'''),
])

# --------------------------------------------------------------------------- #
# 3. analyze: the reader's rules come from the skill
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/analyze.py", [
    ("""    llm = ctx.providers.llm_for("analyze")
    user = T.render(T.ANALYZE_USER, text=sample, max_characters=12,
                    max_locations=10, max_props=8)""",
     """    llm = ctx.providers.llm_for("analyze")
    from ..skills import loader
    extra = loader.for_stage(ctx, "analyze")
    user = T.render(T.ANALYZE_USER, text=sample, max_characters=12,
                    max_locations=10, max_props=8) + extra"""),
])

# --------------------------------------------------------------------------- #
# 4. promptgen: the prompt writers' rules come from the skill
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/promptgen.py", [
    ("""        h3_user = T.render(
            T.H3_VIDEO_USER,""",
     """        from ..skills import loader as _loader
        _extra = _loader.for_stage(ctx, "promptgen")
        h3_user = T.render(
            T.H3_VIDEO_USER,"""),
    ("""            constraints=H3_CONSTRAINTS)""",
     """            constraints=H3_CONSTRAINTS + _extra)"""),
])
