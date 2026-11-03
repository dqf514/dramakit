"""A character whose pictures already exist does not have them drawn again.

generate_refs skipped only locked characters, so every other one had its
pictures redrawn whenever the stage ran - which is how a resume threw away
sixty-three good reference pictures to make sixty-three new ones, at
twenty-four seconds each, overwriting the set the rest of the project was
made with.

A lock was the wrong test. The question is not whether the user decided
the look should not change; it is whether the look is already there. A
character with pictures on disk keeps them, whether or not they are
locked, and a character without them gets drawn - which is what the stage
is for.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\character.py")
s = p.read_text(encoding="utf-8")

old = '''    if c.locked and _has_refs_on_disk(ctx, c):
        ctx.log.info("character: %s 已锁定且参考图在，跳过重画", c.name)
        return 0'''
new = '''    # The pictures are already there, so there is nothing to make - and
    # drawing them again would replace the set the rest of the project was
    # made with. A lock is not the test: a look that exists is kept, a look
    # that does not is drawn, which is what the stage is for.
    if _has_refs_on_disk(ctx, c):
        ctx.log.info("character: %s 参考图已在，跳过重画", c.name)
        return 0'''
assert old in s, "generate_refs 的跳过锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("character.py: 有参考图就跳过（不再看锁）")
