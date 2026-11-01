"""Does a project with seasons survive a save/load round trip?

The season model is new, so the first thing to prove is that a project
with seasons and a canon saves to project.json and comes back intact -
otherwise every season silently vanishes on the next load.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.models import (Canon, Chapter, Character, Episode, Project,
                             ProjectMeta, Season, Status)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        from dramakit.project import ProjectStore
        store = ProjectStore.create(Path(tmp), "季测试")

        proj = store.load()
        proj.meta.chapters = [
            Chapter(volume="第一卷", index=i, title=f"第{i}章", chars=100,
                    file=f"source/volumes/vol第一卷_ch{i:03d}.txt")
            for i in range(1, 21)]
        proj.characters = [Character(name="余飞", role="男主", gender="男",
                                     appearance="书生", voice_id="male-a")]
        proj.episodes = [
            Episode(id="ep001", index=1, season=1, title="第1集",
                    status=Status.DONE),
            Episode(id="ep002", index=2, season=1, title="第2集"),
            Episode(id="ep003", index=3, season=2, title="第3集"),
        ]
        proj.seasons = [
            Season(index=1, title="第一季", chapters=[1, 2, 3, 4, 5],
                   episode_range=[1, 2], status=Status.DONE,
                   character_looks={"余飞": {"appearance": "书生"}},
                   synopsis="穿越成树"),
            Season(index=2, title="第二季", chapters=[6, 7, 8],
                   episode_range=[3, 3], status=Status.RUNNING),
        ]
        proj.canon = Canon(
            characters={"余飞": {"role": "男主", "gender": "男"}},
            character_looks={"余飞": [{"appearance": "书生"},
                                      {"appearance": "参天大树"}]},
            voices={"余飞": "male-a"},
            progress="余飞已成为古树，风语之森被侵略",
            done_chapters=[1, 2, 3, 4, 5, 6, 7, 8],
        )
        proj.meta.chosen_chapters = [6, 7, 8]
        proj.meta.segmented_chapters = [1, 2, 3, 4, 5, 6, 7, 8]
        store.save(proj)

        # reload from disk, the way the server does on every request
        back = store.load()

        checks = []
        def ck(label, cond):
            checks.append((label, bool(cond)))

        ck("seasons 数量", len(back.seasons) == 2)
        ck("第1季章节", back.seasons[0].chapters == [1, 2, 3, 4, 5])
        ck("第1季状态", back.seasons[0].status == Status.DONE)
        ck("第1季造型", back.seasons[0].character_looks["余飞"]["appearance"] == "书生")
        ck("第2季状态", back.seasons[1].status == Status.RUNNING)
        ck("episode.season=1", back.episodes[0].season == 1)
        ck("episode.season=2", back.episodes[2].season == 2)
        ck("canon.characters", "余飞" in back.canon.characters)
        ck("canon 造型演变 2 段",
           len(back.canon.character_looks["余飞"]) == 2)
        ck("canon 第2段造型", back.canon.character_looks["余飞"][1]["appearance"] == "参天大树")
        ck("canon 剧情进度", "古树" in back.canon.progress)
        ck("canon 已完成章节", back.canon.done_chapters == [1, 2, 3, 4, 5, 6, 7, 8])
        ck("current_season", back.current_season == 3)
        ck("meta.segmented_chapters", back.meta.segmented_chapters == [1, 2, 3, 4, 5, 6, 7, 8])

        # season-scoped episode filtering, the thing that keeps a rerun of
        # season 2 from touching season 1's episodes
        s1 = [e.index for e in back.episodes if e.season == 1]
        s2 = [e.index for e in back.episodes if e.season == 2]
        ck("按季筛选 第1季", s1 == [1, 2])
        ck("按季筛选 第2季", s2 == [3])

        # and the whole thing must be plain JSON on disk
        raw = json.loads((store.root / "project.json").read_text(encoding="utf-8"))
        ck("落盘含 seasons", isinstance(raw.get("seasons"), list))
        ck("落盘含 canon", isinstance(raw.get("canon"), dict))

        width = max(len(l) for l, _ in checks)
        for label, ok in checks:
            print(f"  [{'PASS' if ok else 'FAIL'}] {label:<{width}}")
        failed = [l for l, ok in checks if not ok]
        print()
        print(f"季模型往返: {len(checks) - len(failed)}/{len(checks)} 通过")
        if failed:
            print("失败: " + ", ".join(failed))
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
