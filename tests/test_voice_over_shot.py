"""A shot that carries a voice over must not be sent to the failed pile.

A voice over is the story told over the picture: it is shown as a caption
card and nobody says it.  The prompt deliberately leaves it out, and the
model must not be asked to speak it - otherwise it reads the action out
loud.  But the check before the card was spent counted *every* line the
shot carried, so a shot whose only line was a voice over was rejected
for having no dialogue tag.  Seven shots went down that way in one run.
"""
from __future__ import annotations

import unittest

from dramakit.models import Line, LineKind, Scene, Shot, Status, is_narration
from dramakit.pipeline import visual


def _scene() -> Scene:
    sc = Scene(id="sc-1", index=1, location="庭院", time_of_day="夜",
               summary="两人对峙")
    sc.lines = [
        Line(id="l1", kind=LineKind.NARRATION, speaker="旁白",
             text="这一夜，风雪未停", emotion="苍凉"),
        Line(id="l2", kind=LineKind.DIALOGUE, speaker="苏念",
             text="你到底想怎样", emotion="愤怒"),
    ]
    return sc


class VoiceOverTests(unittest.TestCase):
    def setUp(self):
        self.sc = _scene()

    def test_a_voice_over_is_a_voice_over(self):
        self.assertTrue(is_narration(self.sc.lines[0]))
        self.assertFalse(is_narration(self.sc.lines[1]))

    def test_the_helper_reads_the_scene_lines(self):
        self.assertTrue(visual._is_voice_over(None, self.sc, 1))
        self.assertFalse(visual._is_voice_over(None, self.sc, 2))

    def test_an_index_outside_the_scene_is_not_a_voice_over(self):
        self.assertFalse(visual._is_voice_over(None, self.sc, 0))
        self.assertFalse(visual._is_voice_over(None, self.sc, 9))

    def test_a_shot_with_only_a_voice_over_needs_no_dialogue_tag(self):
        # the count the gate uses: the voice over does not count
        shot = Shot(id="sh-1", index=0, line_indices=[1])
        need = len([n for n in (shot.line_indices or [])
                    if n > 0 and not visual._is_voice_over(None, self.sc, n)])
        self.assertEqual(need, 0)

    def test_a_shot_with_spoken_dialogue_still_needs_a_tag(self):
        shot = Shot(id="sh-2", index=1, line_indices=[2])
        need = len([n for n in (shot.line_indices or [])
                    if n > 0 and not visual._is_voice_over(None, self.sc, n)])
        self.assertEqual(need, 1)


if __name__ == "__main__":
    unittest.main()
