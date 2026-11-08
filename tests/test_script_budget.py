"""The scene gets its share of the episode, not the whole episode.

The merged script stage handed every scene the whole episode's budget,
so a 165-second episode came out with 74 lines and 402 seconds of
picture.  These tests hold the three things that stopped it:

1. Each scene is told its own share of the words and the seconds.
2. The episode's shots are fitted to the episode's length.
3. One scene that fails does not take the episode with it.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, r"E:\dramakit")

from dramakit.models import Line, LineKind, Scene, Shot, Status  # noqa: E402
from dramakit.pipeline import script as S  # noqa: E402


def _shot(i, dur, lines=()):
    return Shot(id=f"sh{i}", index=i, shot_type="中景", camera_move="固定",
                angle="斜侧", height="平视", lens="标准", purpose="",
                subject="人", duration=dur, action=f"第{i}镜",
                characters=["甲"], line_indices=list(lines), beats=[])


class SceneShareTests(unittest.TestCase):
    def test_the_shots_are_scaled_to_the_episode(self):
        """A shot list of 120 seconds becomes the episode's 40."""
        from dramakit.models import Episode
        ep = Episode(id="ep001", index=1, title="第1集")
        sc = Scene(id="sc1", index=1, location="内 · 房 · 日",
                   time_of_day="日", summary="", mood="平静")
        # eight shots of fifteen seconds: 120 seconds of picture
        sc.shots = [_shot(i, 15.0) for i in range(8)]
        ep.scenes = [sc]
        S._fit_episode_shots(ep, 40.0, 5.0, 15.0, cap=100)
        total = sum(sh.duration for sh in sc.shots)
        self.assertAlmostEqual(total, 40.0, delta=0.5)

    def test_a_shot_is_never_shorter_than_the_model_can_make(self):
        """A shot cannot be cut below the shortest one the card renders."""
        from dramakit.models import Episode
        ep = Episode(id="ep001", index=1, title="第1集")
        sc = Scene(id="sc1", index=1, location="内 · 房 · 日",
                   time_of_day="日", summary="", mood="平静")
        sc.shots = [_shot(i, 5.0) for i in range(8)]
        ep.scenes = [sc]
        S._fit_episode_shots(ep, 20.0, 5.0, 15.0, cap=100)
        for sh in sc.shots:
            self.assertGreaterEqual(sh.duration, 5.0)

    def test_the_shots_do_not_outlast_the_episode(self):
        """More shots than the episode has room for: the extras go."""
        from dramakit.models import Episode
        ep = Episode(id="ep001", index=1, title="第1集")
        sc = Scene(id="sc1", index=1, location="内 · 房 · 日",
                   time_of_day="日", summary="", mood="平静")
        sc.shots = [_shot(i, 5.0) for i in range(8)]
        ep.scenes = [sc]
        S._fit_episode_shots(ep, 20.0, 5.0, 15.0, cap=4)
        self.assertEqual(len(sc.shots), 4)

    def test_a_dropped_shot_leaves_its_lines_with_a_picture(self):
        """The lines the cut shots carried are not lost."""
        from dramakit.models import Episode
        ep = Episode(id="ep001", index=1, title="第1集")
        sc = Scene(id="sc1", index=1, location="内 · 房 · 日",
                   time_of_day="日", summary="", mood="平静")
        sc.shots = [_shot(i, 5.0, lines=[i + 1]) for i in range(8)]
        ep.scenes = [sc]
        S._fit_episode_shots(ep, 20.0, 5.0, 15.0, cap=2)
        covered = set()
        for sh in sc.shots:
            covered.update(sh.line_indices)
        self.assertEqual(covered, set(range(1, 9)))

    def test_the_shot_numbers_are_kept_in_order(self):
        from dramakit.models import Episode
        ep = Episode(id="ep001", index=1, title="第1集")
        sc = Scene(id="sc1", index=1, location="内 · 房 · 日",
                   time_of_day="日", summary="", mood="平静")
        sc.shots = [_shot(i, 5.0) for i in range(8)]
        ep.scenes = [sc]
        S._fit_episode_shots(ep, 20.0, 5.0, 15.0, cap=3)
        self.assertEqual([sh.index for sh in sc.shots], [0, 1, 2])


class PromptBudgetTests(unittest.TestCase):
    """The prompt says what the scene may have, and what the episode has."""

    def test_the_prompt_carries_the_scene_and_the_episode(self):
        from dramakit.prompts import templates as T
        user = T.render(T.SCRIPT_SCENE_USER,
                        genre="古装", ep_index=1, ep_total=30,
                        location="内 · 房 · 日", time_of_day="日", mood="平静",
                        action="她推门", summary="她推门",
                        beats_text="- 1. 她推门",
                        text="原文", character_anchors="甲：外貌",
                        screenwriter_rules="规则",
                        scene_seconds=33, scene_shots=7, scene_avg=4.7,
                        dur_min=5.0, dur_max=15.0,
                        budget_seconds=33, budget_chars=135, budget_lines=7,
                        episode_seconds=165, episode_chars=742,
                        episode_lines=36, episode_scenes=5)
        # the scene's own share
        self.assertIn("135", user)
        self.assertIn("这一场只管自己那一份", user)
        # the episode's whole, so the model knows where it sits
        self.assertIn("165", user)
        self.assertIn("742", user)
        # and the shot count is a count
        self.assertIn("7 个镜头", user)
        self.assertIn("不多不少", user)

    def test_the_prompt_does_not_say_the_whole_episode_every_time(self):
        """The old wording is gone: it is what made every scene spend it."""
        from dramakit.prompts import templates as T
        self.assertNotIn("这一集全部的台词加起来不超过", T.SCRIPT_SCENE_USER)


if __name__ == "__main__":
    unittest.main()
