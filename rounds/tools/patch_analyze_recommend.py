"""The analysis recommends the skills, and the summary is kept.

Two things the project should have once the book has been read: what
the book is about, in a sentence, and which skills suit it.  The first
is written by the analysis; the second is asked for afterwards, from
the catalogue's own words beside what the analysis found.

A project that has already chosen its skills keeps them: the
recommendation is what a project starts with, not what it is given.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\pipeline\analyze.py")
text = PATH.read_text(encoding="utf-8")

old = '''    if data.get("title") and not ctx.project.meta.title:
        ctx.project.meta.title = data["title"]
    if data.get("synopsis"):
        season.synopsis = str(data["synopsis"])
    if data.get("genre"):
        ctx.project.art_direction.genre = data["genre"]
'''

new = '''    if data.get("title") and not ctx.project.meta.title:
        ctx.project.meta.title = data["title"]
    if data.get("synopsis"):
        season.synopsis = str(data["synopsis"])
        # the book in a sentence: the console shows it beside the cover,
        # and the skill recommendation is read from it
        if not ctx.project.meta.synopsis:
            ctx.project.meta.synopsis = str(data["synopsis"])
    if data.get("genre"):
        ctx.project.art_direction.genre = data["genre"]

    # the skills this book wants.  A project that has already chosen
    # its own keeps them - the recommendation is where a project starts,
    # not what it is given.
    if not ctx.project.meta.skills:
        try:
            from ..skills import recommend as _recommend
            got = _recommend.recommend(ctx)
            if got.get("selection"):
                ctx.project.meta.skills = got["selection"]
                ctx.project.meta.skills_recommended = True
                ctx.log.info("analyze: 按这本书推荐了 %d 个阶段的技能",
                             len(got["selection"]))
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("analyze: 技能推荐失败(%s)", str(e)[:140])
'''
assert old in text, "没找到分析的那一段"
text = text.replace(old, new, 1)
PATH.write_text(text, encoding="utf-8")
print("analyze 改好了")
