"""Does the genre card pick itself?

The cards were dead - one folder deeper than the loader reads - and now
they are skills and one of them is picked for the project.  This asks
the question the way the pipeline asks it.
"""
import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.skills import loader  # noqa: E402

cards = loader.genre_cards()
print("  索引里的类型：%d 张" % len(cards))


class _AD:
    genre = "都市/穿书/甜宠/豪门"


class _Meta:
    synopsis = ("林晚穿进一本豪门小说，成了前妻。她要演一个被抛弃的女人，"
                "一边在豪门里周旋，一边慢慢看清自己是谁。")


class _Proj:
    art_direction = _AD()
    meta = _Meta()


class _Ctx:
    project = _Proj()


print("  项目的题材：都市/穿书/甜宠/豪门")
print("  自动挑的卡：%s" % (loader.genre_for(_Ctx()) or "（没挑到）"))

rules = loader.genre_rules(_Ctx())
print("  卡的正文：%d 字" % len(rules))
print("  ---- 开头 ----")
for line in rules.split("\n")[:8]:
    print("  " + line)
