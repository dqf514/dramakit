"""How much the writing rules weigh, and what they are made of.

A stage sends its rules with every call, and the script stage now asks
once per scene - so the rules go out six or eight times an episode.
The number is worth knowing before the list is settled.
"""
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.skills import loader  # noqa: E402

sets = {
    "只写手（写手+分镜+机器拍法）": ["short-drama-write", "short-drama-storyboard",
                                    "short-drama-ai-film"],
    "再加改编手艺": ["short-drama-write", "short-drama-storyboard",
                      "short-drama-ai-film", "short-drama-develop"],
}

for name, names in sets.items():
    total = 0
    print("===", name)
    for n in names:
        t = loader.load(n)
        total += len(t)
        print("    %-24s %6d 字" % (n, len(t)))
    # the documents that ride along with them
    docs = [("short-drama-develop", "adaptation-craft.md"),
            ("short-drama-storyboard", "production-shot-grammar.md"),
            ("short-drama-storyboard", "blocking-playbooks.md"),
            ("short-drama-ai-film", "beats.md"),
            ("short-drama-ai-film", "segments.md")]
    for skill, doc in docs:
        if skill not in names:
            continue
        t = loader.load_refs(skill, [doc])
        total += len(t)
        print("    %-24s %6d 字" % (doc, len(t)))
    print("    合计 %d 字" % total)
