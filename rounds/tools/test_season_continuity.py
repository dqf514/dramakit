"""Two seasons, run in order.  Continuity in, isolation out.

The point of a season is that the second one starts where the first
stopped: it reads the canon, keeps the voices, keeps the locations, and
gets a look that may differ from the first season's - without touching
anything the first season already made.  This runs analyze twice, with
the second season's chapters, against a stub LLM, and checks both.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.models import (Chapter, Character, Location, Project,
                             ProjectMeta, Status)
from dramakit.pipeline import analyze
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore


class StubLLM:
    """The analysis, scripted.  Season 1's 余飞 is a scholar; by season 2
    the story has made him a tree, and that change has to come through.

    Each call's prompt is kept, not just the last one: season 1's
    assertions have to read season 1's prompt, and a single overwritten
    field made them read season 2's - which is how a first season with no
    history appeared to be told about its own future.
    """
    def __init__(self, reply):
        self.reply = reply
        self.prompts: list[str] = []

    @property
    def last_user(self) -> str:
        return self.prompts[-1] if self.prompts else ""

    def prompt(self, n: int) -> str:
        return self.prompts[n] if n < len(self.prompts) else ""

    def complete_json(self, system, user):
        self.prompts.append(user)
        return self.reply


class StubProviders:
    def __init__(self, llm):
        self._llm = llm

    def llm_for(self, stage):
        return self._llm


S1_ANALYSIS = {
    "title": "树神",
    "genre": "穿越",
    "synopsis": "落榜生穿越成一棵树",
    "characters": [
        {"name": "余飞", "role": "男主", "gender": "男", "age": "18",
         "personality": "倔强", "appearance": "清秀书生，布衣",
         "visual_prompt": "young chinese scholar, plain robe"},
        {"name": "艾薇儿", "role": "女主", "gender": "女",
         "appearance": "精灵弓箭手，绿衣",
         "visual_prompt": "elven archer, green dress"},
    ],
    "locations": [{"name": "风语之森", "description": "精灵森林",
                   "visual_prompt": "enchanted forest, ancient trees"}],
    "props": [],
    "art_direction": {"style": "高奇幻电影感"},
}

S2_ANALYSIS = {
    "title": "树神",
    "genre": "奇幻",
    "synopsis": "古树觉醒，统御森林",
    "characters": [
        {"name": "余飞", "role": "男主", "gender": "男", "age": "外观千年古树",
         "personality": "沉稳", "appearance": "参天古树，树皮如甲，树心有光",
         "visual_prompt": "ancient towering tree, glowing heartwood"},
        {"name": "艾薇儿", "role": "女主", "gender": "女",
         "appearance": "精灵弓箭手，绿衣，负伤",
         "visual_prompt": "elven archer, green dress, wounded"},
    ],
    "locations": [{"name": "风语之森", "description": "被战火波及的精灵森林",
                   "visual_prompt": "enchanted forest, ancient trees"}],
    "props": [],
    "art_direction": {"style": "高奇幻电影感"},
}


def make_book(root: Path) -> None:
    vdir = root / "source" / "volumes"
    vdir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 13):
        body = f"第{i}章。" + "这是本章正文，用来给分析读的。" * 30
        (vdir / f"vol第一卷_ch{i:03d}.txt").write_text(body, encoding="utf-8")


def chapters_meta() -> list[Chapter]:
    # file is project-relative, the way catalog.run writes it
    return [Chapter(volume="第一卷", index=i, title=f"第{i}章", chars=100,
                    file=f"source/volumes/vol第一卷_ch{i:03d}.txt")
            for i in range(1, 13)]


def run_analyze(store, cfg, llm, season, chosen):
    proj = store.load()
    proj.meta.chosen_chapters = chosen
    store.save(proj)
    ctx = Context(cfg, store, providers=StubProviders(llm))
    ctx.use_season(season)
    ctx.seed_season(chosen)
    ctx.mark_chapter_season(chosen)
    res = analyze.run(ctx)
    return ctx, res


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="dk_season_"))
    try:
        cfg = Config()
        store = ProjectStore.create(tmp, "季连续性")
        make_book(store.root)
        proj = store.load()
        proj.meta.title = "树神"
        proj.meta.chapters = chapters_meta()
        store.save(proj)

        checks = []
        def ck(label, cond):
            checks.append((label, bool(cond)))

        # ---- season 1: chapters 1-6 ----
        llm1 = StubLLM(S1_ANALYSIS)
        ctx1, res1 = run_analyze(store, cfg, llm1, 1, [1, 2, 3, 4, 5, 6])
        chars_s1 = {c.name: c for c in ctx1.project.characters}
        ck("S1 analyze 读的是本季章节", "第1章" in llm1.last_user)
        ck("S1 没读到第10章", "第10章" not in llm1.last_user)
        ck("S1 canon 未注入（首季无前情）", "此前已制作内容" not in llm1.last_user)
        ck("S1 余飞是书生", "书生" in chars_s1["余飞"].appearance)
        ck("S1 记录了造型演变",
           len(ctx1.project.canon.character_looks["余飞"]) == 1)

        # close season 1 the way the runner does once its stages finish,
        # so season 2 has a canon to inherit from
        from dramakit.pipeline.runner import _complete_canon
        _complete_canon(ctx1, ctx1.season)

        # ---- season 2: chapters 7-12, with the canon now populated ----
        llm2 = StubLLM(S2_ANALYSIS)
        ctx2, res2 = run_analyze(store, cfg, llm2, 2, [7, 8, 9, 10, 11, 12])
        chars_s2 = {c.name: c for c in ctx2.project.characters}
        ck("S2 canon 注入了前情", "此前已制作内容" in llm2.last_user)
        ck("S2 canon 带了上一季造型", "书生" in llm2.last_user)
        # The progress line carries what the last season was about, quoted
        # from its own synopsis - not a phrase invented here. Season 1 was
        # 落榜生穿越成一棵树, and that is what season 2 should inherit.
        ck("S2 canon 带了剧情进度",
           "剧情进度" in llm2.last_user and "落榜生穿越成一棵树" in llm2.last_user)
        ck("S2 余飞变了造型（古树）", "古树" in chars_s2["余飞"].appearance)
        ck("S2 造型演变累积到 2 段",
           len(ctx2.project.canon.character_looks["余飞"]) == 2)
        ck("S2 第1季造型仍在第1位",
           ctx2.project.canon.character_looks["余飞"][0]["appearance"]
           .find("书生") >= 0)
        ck("S2 艾薇儿保留音色字段", "voice_id" in chars_s2["艾薇儿"].model_dump())
        ck("S2 场景沿用参考图字段", "ref_images" in
           ctx2.project.locations[0].model_dump())
        # Season 2's own analysis is not season 2: it has been read, not
        # closed. What the canon inherited from season 1 is chapters 1-6,
        # and that is what it should still say - a season claims its
        # chapters when it is closed, not when its text is first read.
        ck("S2 canon 带了已完成章节",
           ctx2.project.canon.done_chapters == list(range(1, 7)))
        ck("S2 的章节还没写进已完成",
           7 not in ctx2.project.canon.done_chapters)
        ck("S1 季记录仍在", ctx2.project.season(1) is not None)
        ck("S2 季记录已建", ctx2.project.season(2) is not None)

        # ---- re-running season 2 must not create a third season ----
        ctx3, _ = run_analyze(store, cfg, StubLLM(S2_ANALYSIS), 2,
                              [7, 8, 9, 10, 11, 12])
        ck("重跑 S2 不新建季", ctx3.project.season(3) is None)
        ck("重跑 S2 造型演变仍是 2 段",
           len(ctx3.project.canon.character_looks["余飞"]) == 2)

        width = max(len(l) for l, _ in checks)
        for label, ok in checks:
            print(f"  [{'PASS' if ok else 'FAIL'}] {label:<{width}}")
        failed = [l for l, ok in checks if not ok]
        print()
        print(f"季连续性: {len(checks) - len(failed)}/{len(checks)} 通过")
        if failed:
            print("失败: " + ", ".join(failed))
            return 1
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
