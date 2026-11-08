"""How much the writing rules weigh, and what they are made of.

A stage sends its rules with every call, and the script stage now asks
once per scene - so the rules go out six or eight times an episode.
The number is worth knowing before the list is settled.
"""
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.skills import loader  # noqa: E402

sets = {
    "写剧本": ["novel-script"],
    "写剧本+分镜（这一阶段一次写完两样）": ["novel-script", "novel-storyboard"],
    "再加改编手艺": ["novel-script", "novel-storyboard", "novel-outline"],
}

for name, names in sets.items():
    total = 0
    print("===", name)
    for n in names:
        t = loader.load(n)
        total += len(t)
        print("    %-24s %6d 字" % (n, len(t)))
    # the documents that ride along with them
    docs = [("novel-script", "script-pass.md"),
            ("novel-storyboard", "storyboard-pass.md"),
            ("novel-storyboard", "shot-writing.md"),
            ("novel-outline", "outline-pass.md")]
    for skill, doc in docs:
        if skill not in names:
            continue
        t = loader.load_refs(skill, [doc])
        total += len(t)
        print("    %-24s %6d 字" % (doc, len(t)))
    print("    合计 %d 字" % total)
