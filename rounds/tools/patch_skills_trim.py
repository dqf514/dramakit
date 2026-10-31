"""One theory skill per genre, not two.

The skills came to 55K characters a call - the craft rules plus two theory
documents per genre - and a prompt that big makes every call slower for
what it adds.  The craft is what carries the work; the theory is a nudge
on top, and one document is a nudge.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")

old_start = s.find('    by_genre: dict[str, list[str]] = {')
old_end = s.find('    }', old_start)
assert old_start > 0 and old_end > 0, "没找到 by_genre"
block = '''    by_genre: dict[str, list[str]] = {
        "复仇": ["screenwriting-theory/sw-character-conflict"],
        "甜宠": ["screenwriting-theory/ozu-screenplay-style"],
        "悬疑": ["screenwriting-theory/sw-story-structure"],
        "战神": ["screenwriting-theory/sw-genre-anatomy"],
'''
s = s[:old_start] + block + s[old_end:]
p.write_text(s, encoding="utf-8")
print("config.py: 每个题材只留一个理论 skill")
