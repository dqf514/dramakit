"""Make a cover, for real, and look at it.

A scratch project with a title, a world and a cast goes through the
cover stage: the model writes the picture in words, the picture model
draws it, and the title is put on afterwards.
"""
import pathlib
import sys
import time

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.models import ArtDirection, Character
from dramakit.pipeline import cover as cover_stage
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

SLUG = "封面自检"


def main():
    cfg = Config.load(r"E:\dramakit\config\default.yaml")
    root = pathlib.Path(r"E:\dramakit\projects") / SLUG
    if root.exists():
        import shutil
        shutil.rmtree(root)
    store = ProjectStore.create(root.parent, SLUG)
    proj = store.load()
    proj.meta.title = "铁血军魂"
    proj.meta.synopsis = ("末世里，一个被逐出师门的废柴少年发现自己是失落的"
                          "黑甲骑士，背负着整支舰队的追杀。")
    proj.art_direction = ArtDirection(
        genre="科幻末世", style="写实电影感", aspect_ratio="9:16",
        era="当代", color_palette="暗红与冷蓝")
    proj.characters = [
        Character(name="林远", role="主角", gender="男", age="24",
                  appearance="短黑发，左颊一道旧疤，眼神沉而亮"),
        Character(name="苏念", role="女主", gender="女", age="23",
                  appearance="黑色长发束起，军装外套，目光锐利"),
    ]
    store.save(proj)

    ctx = Context(cfg, store)
    t0 = time.time()
    res = cover_stage.run(ctx)
    print(f"\n结果: {res}   （{time.time() - t0:.1f} 秒）")
    out = store.project_cover_path()
    print("封面文件:", out, "存在:", out.exists(),
          "大小:", out.stat().st_size if out.exists() else 0, "字节")
    if out.exists():
        proj2 = store.load()
        print("记在工程里的封面:", proj2.meta.cover_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
