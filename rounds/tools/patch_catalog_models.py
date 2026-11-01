"""The book's table of contents: volumes and chapters."""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\models.py")
s = p.read_text(encoding="utf-8")

if "class Chapter(BaseModel)" in s:
    print("models.py: 已经有了")
else:
    old = "class ProjectMeta(BaseModel):"
    new = '''class Chapter(BaseModel):
    """One chapter of the book, as the console lists it."""
    volume: str = ""
    index: int = 0
    title: str = ""
    chars: int = 0
    file: str = ""


class ProjectMeta(BaseModel):'''
    assert old in s
    s = s.replace(old, new, 1)

    old2 = """    synopsis: str = ""
    created_at: str = \"\""""
    new2 = """    synopsis: str = ""
    volumes: list[str] = []
    chapters: list[Chapter] = []
    chapter_pattern: str = ""
    volume_pattern: str = ""
    chosen_chapters: list[int] = []
    episodes_wanted: int = 0
    created_at: str = \"\""""
    assert old2 in s, "meta 字段锚点没找到"
    s = s.replace(old2, new2, 1)
    p.write_text(s, encoding="utf-8")
    print("models.py: Chapter + meta 字段")
