"""The skills in the config: which ones each stage writes with.

The skills come from `skills/` - the short-drama skills and the
screenwriting theory beside them.  A stage asks for the ones that make it
better at its own job, and a genre asks for the theory that suits the
drama: a revenge piece wants character conflict and a Chekhovian engine, a
sweet romance wants Ozu's staging.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")

if "class SkillsConfig" in s:
    print("config.py: 已经有了")
else:
    i = s.find("class CharacterConfig")
    assert i > 0, "没找到 CharacterConfig"
    block = '''class SkillsConfig(BaseModel):
    """Which skills each stage writes with (see skills/ for what is there)."""
    analyze: list[str] = ["short-drama-novel-analyze"]
    script: list[str] = ["short-drama-write"]
    storyboard: list[str] = ["short-drama-storyboard"]
    promptgen: list[str] = ["short-drama-video-prompts",
                            "short-drama-image-prompts"]
    # the screenwriting theory, by genre: the drama asks, the skills answer
    by_genre: dict[str, list[str]] = {
        "复仇": ["screenwriting-theory/sw-character-conflict",
                 "screenwriting-theory/chekhov-dramaturgy"],
        "甜宠": ["screenwriting-theory/ozu-screenplay-style",
                 "screenwriting-theory/sw-dialogue"],
        "悬疑": ["screenwriting-theory/sw-story-structure",
                 "screenwriting-theory/sw-genre-anatomy"],
        "战神": ["screenwriting-theory/sw-genre-anatomy",
                 "screenwriting-theory/sw-story-structure"],
    }


'''
    s = s[:i] + block + s[i:]

    k = s.find("    characters: CharacterConfig")
    assert k > 0, "没找到 characters 字段"
    s = s[:k] + "    skills: SkillsConfig = SkillsConfig()\n" + s[k:]
    p.write_text(s, encoding="utf-8")
    print("config.py: SkillsConfig + Config.skills")

# and the loader accepts a path with a folder in it (for the theory skills)
q = Path(r"E:\\dramakit\\dramakit\\skills\\loader.py")
t = q.read_text(encoding="utf-8")
old = """    folder = SKILLS / name
    md = folder / "SKILL.md\""""
new = """    folder = SKILLS / name
    md = folder / "SKILL.md\""""
q.write_text(t, encoding="utf-8")
print("loader.py: 就绪（支持 域/skill 名 的路径）")
