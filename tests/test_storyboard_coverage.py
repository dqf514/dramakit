"""The coverage of a scene, and the sound that comes with the picture.

Two things went wrong for a long time and neither of them showed up in a
test, because both are about what the shot list *looks* like:

  - every line of dialogue got its own close-up of the person saying it,
    square to the lens, so the episode played like a series of interviews
  - the sound of the film was the H3 clip's own voice and room and music,
    with a score and a library track laid under it on top

The first is now enforced in code as well as asked for in the prompt, and
the second is decided in one place: the clip's own sound is the whole
soundtrack.
"""
from __future__ import annotations

import unittest

from dramakit.config import Config
from dramakit.models import Line, Scene, Shot, ShotType
from dramakit.pipeline import storyboard as sb
from dramakit.pipeline.qc import _coverage_metrics
from dramakit.skills import loader


def _scene() -> Scene:
    sc = Scene(id="sc-1", index=1, location="客厅", time_of_day="日",
               summary="两人对峙")
    sc.lines = [
        Line(id="l1", speaker="苏念", text="你到底想怎样", emotion="愤怒"),
        Line(id="l2", speaker="陆沉", text="我想要你签了这份合同", emotion="冷"),
        Line(id="l3", speaker="苏念", text="做梦", emotion="怒"),
        Line(id="l4", speaker="陆沉", text="你没得选", emotion="冷"),
    ]
    return sc


def _shot(i: int, size: str, angle: str, who: list[str],
          lines: list[int], subject: str = "") -> Shot:
    return Shot(id=f"sh-{i}", index=i, shot_type=ShotType(size), angle=angle,
                height="平视", lens="标准", subject=subject or (who[0] if who else "环境"),
                action="", characters=list(who), line_indices=list(lines))


class CoverageTests(unittest.TestCase):
    def test_a_talking_head_is_never_square_to_the_lens(self):
        sc = _scene()
        sc.shots = [_shot(0, "近景", "正面", ["苏念"], [1]),
                    _shot(1, "近景", "斜侧", ["苏念"], [2])]
        sb._enforce_coverage(sc)
        self.assertEqual(sc.shots[0].angle, "斜侧")

    def test_an_establishing_shot_may_stay_square(self):
        # a wide shot of the room is not a face in an interview
        sc = _scene()
        sc.shots = [_shot(0, "全景", "正面", ["苏念", "陆沉"], [1])]
        sb._enforce_coverage(sc)
        self.assertEqual(sc.shots[0].angle, "正面")

    def test_two_shots_in_a_row_are_never_the_same_picture(self):
        sc = _scene()
        sc.shots = [_shot(0, "近景", "斜侧", ["苏念"], [1]),
                    _shot(1, "近景", "斜侧", ["苏念"], [2])]
        sb._enforce_coverage(sc)
        a, b = sc.shots
        self.assertFalse(a.shot_type == b.shot_type and a.angle == b.angle,
                         "相邻两镜的景别和角度完全一样")

    def test_three_shots_of_one_face_in_a_row_become_a_reverse_shot(self):
        sc = _scene()
        sc.shots = [_shot(0, "近景", "斜侧", ["苏念"], [1]),
                    _shot(1, "近景", "斜侧", ["苏念"], [2]),
                    _shot(2, "近景", "斜侧", ["苏念"], [3])]
        sb._enforce_coverage(sc)
        middle = sc.shots[1]
        self.assertEqual(middle.shot_type, ShotType.OVER_SHOULDER)
        self.assertIn("陆沉", middle.characters)

    def test_good_coverage_is_left_alone(self):
        # a plan that already reverse-cuts is not touched
        sc = _scene()
        sc.shots = [_shot(0, "中景", "斜侧", ["苏念", "陆沉"], [1]),
                    _shot(1, "过肩", "后斜侧", ["陆沉", "苏念"], [2]),
                    _shot(2, "近景", "斜侧", ["苏念"], [3]),
                    _shot(3, "特写", "正侧", ["陆沉"], [4])]
        before = [(s.shot_type.value, s.angle, tuple(s.characters))
                  for s in sc.shots]
        sb._enforce_coverage(sc)
        after = [(s.shot_type.value, s.angle, tuple(s.characters))
                 for s in sc.shots]
        self.assertEqual(before, after)

    def test_a_reaction_shot_keeps_the_listener_in_frame(self):
        # the line belongs to the speaker's own shot, so the reaction shot
        # is left showing the person who is listening
        sc = _scene()
        sc.shots = [_shot(0, "近景", "斜侧", ["苏念"], [1]),
                    _shot(1, "近景", "斜侧", ["陆沉"], [], subject="陆沉")]
        sb._repair_line_casts(sc)
        self.assertEqual(sc.shots[0].line_indices, [1])
        self.assertEqual(sc.shots[1].line_indices, [])
        self.assertEqual(sc.shots[1].characters, ["陆沉"])

    def test_the_action_does_not_point_a_face_at_the_lens(self):
        out = sb._strip_facing_camera("苏念直视镜头，眼眶发红")
        self.assertNotIn("镜头", out)
        self.assertIn("画外", out)

    def test_the_angles_the_model_writes_are_understood(self):
        self.assertEqual(sb._to_angle("四分之三"), "斜侧")
        self.assertEqual(sb._to_angle("过肩"), "后斜侧")
        self.assertEqual(sb._to_angle("侧面"), "正侧")
        self.assertEqual(sb._to_height("俯拍"), "高")
        self.assertEqual(sb._to_lens("长焦"), "长")
        # anything it does not know falls back to a three-quarter view
        self.assertEqual(sb._to_angle("随便什么"), "斜侧")


class CoverageReportTests(unittest.TestCase):
    def test_the_report_says_when_a_scene_never_cuts(self):
        ep = type("Ep", (), {})()
        sc = _scene()
        sc.shots = [_shot(0, "近景", "正面", ["苏念"], [1]),
                    _shot(1, "近景", "正面", ["苏念"], [2]),
                    _shot(2, "近景", "正面", ["苏念"], [3])]
        ep.scenes = [sc]
        metrics, warnings = _coverage_metrics(ep)
        self.assertEqual(metrics["head_on_shots"], 3)
        self.assertEqual(metrics["longest_same_subject_run"], 3)
        self.assertTrue(warnings)

    def test_a_covered_scene_is_quiet(self):
        ep = type("Ep", (), {})()
        sc = _scene()
        sc.shots = [_shot(0, "中景", "斜侧", ["苏念", "陆沉"], [1]),
                    _shot(1, "过肩", "后斜侧", ["陆沉"], [], subject="陆沉"),
                    _shot(2, "近景", "斜侧", ["苏念"], [3]),
                    _shot(3, "空镜", "斜侧", [], [], subject="合同")]
        ep.scenes = [sc]
        metrics, warnings = _coverage_metrics(ep)
        self.assertEqual(metrics["head_on_shots"], 0)
        self.assertEqual(warnings, [])


class SkillTests(unittest.TestCase):
    def test_the_stage_skills_come_with_their_references(self):
        cfg = Config.load()
        text = loader.load("short-drama-develop", refs=["adaptation-craft.md"])
        self.assertIn("改编", text)
        self.assertIn("adaptation-craft.md", text)

    def test_a_reference_that_was_not_asked_for_is_not_sent(self):
        text = loader.load("short-drama-develop", refs=[])
        self.assertNotIn("<!-- adaptation-craft.md -->", text)
        text = loader.load("short-drama-develop", refs=["adaptation-craft.md"])
        self.assertIn("<!-- adaptation-craft.md -->", text)

    def test_the_screenwriter_gets_the_adaptation_rules(self):
        cfg = Config.load()
        self.assertIn("short-drama-write", cfg.skills.script)
        self.assertIn("screenwriting-theory/sw-format-adaptation",
                      cfg.skills.script)
        # the adaptation craft comes with the writer, even though the
        # development skill itself is not its rulebook
        refs = cfg.skills.refs.get("script", {})
        self.assertIn("adaptation-craft.md", refs.get("short-drama-develop", []))

    def test_the_director_gets_the_shot_grammar(self):
        cfg = Config.load()
        self.assertIn("short-drama-storyboard", cfg.skills.storyboard)
        refs = cfg.skills.refs.get("storyboard", {})
        self.assertIn("production-shot-grammar.md",
                      refs.get("short-drama-storyboard", []))


class SoundTests(unittest.TestCase):
    def test_the_native_sound_is_the_whole_soundtrack(self):
        cfg = Config.load()
        cfg.comfyui.native_audio = True
        cfg.compose.native_audio_exclusive = True

        class FakeCtx:
            pass

        ctx = FakeCtx()
        ctx.cfg = cfg
        from dramakit.pipeline.compose import _soundtrack_is_native
        self.assertTrue(_soundtrack_is_native(ctx))

    def test_the_old_way_is_still_available(self):
        cfg = Config.load()
        cfg.comfyui.native_audio = True
        cfg.compose.native_audio_exclusive = False

        class FakeCtx:
            pass

        ctx = FakeCtx()
        ctx.cfg = cfg
        from dramakit.pipeline.compose import _soundtrack_is_native
        self.assertFalse(_soundtrack_is_native(ctx))


if __name__ == "__main__":
    unittest.main()
