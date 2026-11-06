"""The dialogue of a short drama, and the two things that go wrong with it.

One: a note in brackets is a note for the actor, not for the audience.
The text is what the voice model says and what the subtitle shows, so
a note that slipped into it is taken back out - and put into the
emotion field, where the notes belong.

Two: a script that is one long interrogation reads like a form being
filled in.  The questions answered straight are counted, so the
flatness can be seen rather than felt.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from dramakit.models import Line, Scene  # noqa: E402
from dramakit.pipeline.script import _flatness, _strip_direction  # noqa: E402


def scene(*pairs) -> Scene:
    sc = Scene(id="sc-1", index=1, location="客厅", time_of_day="日")
    for i, (who, what) in enumerate(pairs, 1):
        sc.lines.append(Line(id=f"ln-{i}", speaker=who, text=what, emotion="平静"))
    return sc


class StripDirectionTests(unittest.TestCase):
    def test_a_note_in_the_text_is_taken_out(self):
        self.assertEqual(_strip_direction("太太，您怎么一身酒味！（端着早餐进门）"),
                         "太太，您怎么一身酒味！")

    def test_a_half_width_note_is_taken_out_too(self):
        self.assertEqual(_strip_direction("这不是我房间。(环顾四周)"),
                         "这不是我房间。")

    def test_a_line_without_a_note_is_untouched(self):
        self.assertEqual(_strip_direction("我结婚了？"), "我结婚了？")

    def test_a_note_that_is_the_whole_line_leaves_nothing(self):
        self.assertEqual(_strip_direction("（沉默）"), "")


class FlatnessTests(unittest.TestCase):
    def test_a_question_answered_in_one_line_is_counted(self):
        sc = scene(("甲", "这是哪儿？"), ("乙", "您自己的卧室。"))
        pairs, lines = _flatness([sc])
        self.assertEqual(lines, 2)
        self.assertEqual(pairs, 1)

    def test_a_question_answered_at_length_is_not_counted(self):
        sc = scene(("甲", "这是哪儿？"),
                   ("乙", "太太，这是您的卧室，您昨晚喝了很多酒，"
                          "回来就一头栽在床上，叫都叫不醒。"))
        pairs, lines = _flatness([sc])
        self.assertEqual(pairs, 0)
        self.assertEqual(lines, 2)

    def test_a_question_answered_with_a_question_is_not_counted(self):
        sc = scene(("甲", "这是哪儿？"), ("乙", "您说呢？"))
        pairs, _lines = _flatness([sc])
        self.assertEqual(pairs, 0)

    def test_a_line_that_is_not_a_question_is_never_counted(self):
        sc = scene(("甲", "我结婚了。"), ("乙", "三年了。"))
        pairs, lines = _flatness([sc])
        self.assertEqual(pairs, 0)
        self.assertEqual(lines, 2)

    def test_the_count_is_over_the_whole_episode(self):
        sc = scene(("甲", "这是哪儿？"), ("乙", "您的卧室。"),
                   ("甲", "沈总是谁？"), ("乙", "您丈夫。"))
        pairs, lines = _flatness([sc])
        self.assertEqual(pairs, 2)
        self.assertEqual(lines, 4)


if __name__ == "__main__":
    unittest.main()
