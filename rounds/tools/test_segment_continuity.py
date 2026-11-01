"""Does a second batch of chapters append, or wipe the first?

A project is made a few chapters at a time.  So segment has to turn only
the not-yet-cut picked chapters into episodes, number them after the ones
that already exist, and leave the old episodes - and their scenes, shots
and rendered media - exactly as they were.  This runs segment twice, with
a second batch picked after the first, against a stub LLM.
"""
import sys, tempfile, json, shutil
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.models import Chapter, Episode, Scene, Shot, Status
from dramakit.pipeline.base import Context
from dramakit.pipeline import segment
from dramakit.project import ProjectStore


class StubLLM:
    """Says the same harmless thing every time, so no network is involved."""
    def complete_json(self, system, user):
        return {"title": "标题", "logline": "一句话", "hook": "钩子",
                "recap": "", "key_beats": [" beat "]}


class StubProviders:
    def llm_for(self, stage):
        return StubLLM()


def make_book(root: Path, n_chapters: int) -> list[Chapter]:
    src = root / "source"
    src.mkdir(parents=True, exist_ok=True)
    chapters = []
    for i in range(1, n_chapters + 1):
        body = f"第{i}章正文。" + ("这是故事的一段内容，用来占位，"*40)
        f = src / f"ch_{i:03d}.txt"
        f.write_text(body, encoding="utf-8")
        chapters.append(Chapter(volume="第一卷", index=i, title=f"第{i}章",
                                chars=len(body), file=f.name))
    return chapters


def run_segment(store, cfg):
    ctx = Context(cfg, store, providers=StubProviders())
    res = segment.run(ctx)
    return ctx, res


def main():
    tmp = Path(tempfile.mkdtemp(prefix="dk_continuity_"))
    try:
        store = ProjectStore.create(tmp, "连续性测试")
        cfg = Config()

        # the book has 4 chapters; the user picks 1-2 first
        proj = store.load()
        proj.meta.chapters = make_book(store.root, 4)
        proj.meta.chosen_chapters = [1, 2]
        store.save(proj)

        ctx, res1 = run_segment(store, cfg)
        eps1 = [(e.index, e.title, len(e.scenes)) for e in ctx.project.episodes]
        seg1 = list(ctx.project.meta.segmented_chapters)
        print("批次1 结果:", res1)
        print("批次1 集数:", len(eps1), " 集号:", [e[0] for e in eps1])
        print("批次1 已切章节:", seg1)

        # pretend episode 1 was already shot: a scene, a shot, a rendered file
        ctx.project.episodes[0].scenes = [
            Scene(id="sc1", index=1, title="开场",
                  shots=[Shot(id="sh1", index=1, duration=6.0, video_path="clip.mp4")])]
        ctx.project.episodes[0].status = Status.DONE
        ctx.save()

        # the user comes back and picks chapters 3-4 too
        proj = store.load()
        proj.meta.chosen_chapters = [1, 2, 3, 4]
        store.save(proj)

        ctx2, res2 = run_segment(store, cfg)
        eps2 = [(e.index, e.title, len(e.scenes), e.status) for e in ctx2.project.episodes]
        seg2 = list(ctx2.project.meta.segmented_chapters)
        print()
        print("批次2 结果:", res2)
        print("批次2 集数:", len(eps2))
        for e in eps2:
            print("   第%d集  %-8s 场景=%d 状态=%s" % e)

        # --- the assertions that matter ---
        ok = True
        def check(label, cond):
            nonlocal ok
            print(("  OK  " if cond else "  FAIL") + "  " + label)
            ok = ok and cond

        print()
        idxs2 = [e.index for e in ctx2.project.episodes]
        check("批次2 的集号接在批次1之后（不从1重来）",
              idxs2 == sorted(idxs2) and len(set(idxs2)) == len(idxs2))
        check("旧集没有被清掉（集数只增不减）",
              len(ctx2.project.episodes) >= len(eps1))
        ep1_after = next(e for e in ctx2.project.episodes if e.index == eps1[0][0])
        check("旧集的场景/镜头还在（资产复用）",
              len(ep1_after.scenes) == 1 and len(ep1_after.scenes[0].shots) == 1)
        check("旧集的成片路径还在",
              ep1_after.scenes[0].shots[0].video_path == "clip.mp4")
        check("旧集状态没被重置", ep1_after.status == Status.DONE)
        check("已切章节记录了4个", seg2 == [1, 2, 3, 4])
        # re-running with no new chapters must be a no-op
        ctx3, res3 = run_segment(store, cfg)
        check("没有新章节时跳过（不重复切）", res3.get("skipped") is True)
        check("跳过时集数不变", len(ctx3.project.episodes) == len(ctx2.project.episodes))

        print()
        print("=== 连续性测试:", "全部通过" if ok else "有失败", "===")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
