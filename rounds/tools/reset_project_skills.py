"""This project was carrying a list the machine picked a long time ago.

The list named skills that are gone, and it was shorter than the
config's - so the stages were writing with less than the repo's craft.
An empty list means the config's choice, which is the right default
until a person ticks something.
"""
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore  # noqa: E402

PROJ = r"E:\dramakit\projects\穿成亿万总裁他前妻"

store = ProjectStore.open(PROJ)
proj = store.load()
print("  原来:", proj.meta.skills)
proj.meta.skills = {}
proj.meta.skills_recommended = False
store.save(proj)
print("  现在: {}（配置说了算）")
