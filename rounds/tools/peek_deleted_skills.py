"""Which of the deleted skills was about adapting a novel to a film.

    python rounds/tools/peek_deleted_skills.py
"""
import subprocess
import pathlib

REPO = r"E:\dramakit"
REV = "25d26dd^"

names = subprocess.run(
    ["git", "-C", REPO, "ls-tree", "-r", "--name-only", REV,
     "skills/screenwriting-theory/"],
    capture_output=True, text=True, encoding="utf-8").stdout.split()

skills = {}
for p in names:
    if not p.endswith("SKILL.md"):
        continue
    body = subprocess.run(["git", "-C", REPO, "show", f"{REV}:{p}"],
                          capture_output=True, text=True, encoding="utf-8").stdout
    name = p.split("/")[2]
    skills[name] = body

KEYS = ["改编", "连贯", "节奏", "结构", "场次", "人物", "伏笔", "悬念",
        "类型", "对白", "台词", "转场", "大纲", "短剧", "竖屏", "竖版"]
print("  %-38s %s" % ("技能", "命中"))
rows = []
for name, body in sorted(skills.items()):
    hits = [k for k in KEYS if k in body]
    rows.append((len(hits), name, hits))
for n, name, hits in sorted(rows, reverse=True):
    print("  %-38s %2d  %s" % (name, n, " ".join(hits)))
