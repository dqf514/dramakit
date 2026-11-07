import pathlib
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.project import ProjectStore  # noqa: E402
from dramakit.skills import loader  # noqa: E402
from types import SimpleNamespace  # noqa: E402

ROOT = pathlib.Path(r"E:\dramakit\projects")
projs = [d for d in sorted(ROOT.iterdir())
         if d.is_dir() and (d / "project.json").exists()]
projs.sort(key=lambda d: (d / "project.json").stat().st_mtime, reverse=True)
p = projs[0]
store = ProjectStore.open(str(p))
proj = store.load()

print("  项目：", proj.meta.title or p.name)
ad = proj.art_direction
print("  题材：", ad.genre)
print("  画风：", ad.style, "| 年代：", ad.era, "| 色调：", ad.color_palette)
print("  画幅：%s %sx%s" % (ad.aspect_ratio, ad.frame_width, ad.frame_height))
print("  风格提示词：", (ad.style_prompt_prefix or "")[:120])
print()
print("  自动挑的类型卡：", loader.genre_for(SimpleNamespace(project=proj)) or "（没挑到）")
print()
print("  角色 %d 个：" % len(proj.characters))
for c in proj.characters:
    print("    %-8s %-10s %s" % (c.name, c.role or "", (c.appearance or "")[:70]))
print()
print("  场景 %d 个：" % len(proj.locations))
for l in proj.locations:
    print("    %-16s %s" % (l.name, (l.description or "")[:60]))
