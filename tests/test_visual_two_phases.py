"""A shot with a picture and no clip is not finished.

The visual stage makes two things - a picture and a clip - and it used
to count a shot as done when it had either of them.  So every shot
drawn in an earlier run was skipped the next time the stage ran, and
its clip was never made: the film was missing it.  On a run carried on
after a restart, that is most of the film.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from dramakit.models import Shot  # noqa: E402
from dramakit.pipeline.visual import _what_is_missing  # noqa: E402


class WhatIsMissingTests(unittest.TestCase):
    def test_a_picture_without_a_clip_still_wants_the_clip(self):
        shot = Shot(id="sh-1", image_path="images/sh-1.png")
        need_img, need_vid = _what_is_missing(shot, True, True)
        self.assertFalse(need_img, "图已经有了，不该再要图")
        self.assertTrue(need_vid, "没有视频，这一段还没做")

    def test_a_clip_without_a_picture_still_wants_the_picture(self):
        shot = Shot(id="sh-2", video_path="video/sh-2.mp4")
        need_img, need_vid = _what_is_missing(shot, True, True)
        self.assertTrue(need_img, "没有图，这一张还没画")
        self.assertFalse(need_vid, "视频已经有了")

    def test_a_shot_with_both_wants_neither(self):
        shot = Shot(id="sh-3", image_path="images/sh-3.png", video_path="video/sh-3.mp4")
        need_img, need_vid = _what_is_missing(shot, True, True)
        self.assertFalse(need_img)
        self.assertFalse(need_vid)

    def test_a_shot_with_neither_wants_both(self):
        shot = Shot(id="sh-4")
        need_img, need_vid = _what_is_missing(shot, True, True)
        self.assertTrue(need_img)
        self.assertTrue(need_vid)

    def test_a_stage_that_only_draws_pictures_asks_for_no_clips(self):
        shot = Shot(id="sh-5", image_path="images/sh-5.png")
        need_img, need_vid = _what_is_missing(shot, True, False)
        self.assertFalse(need_img)
        self.assertFalse(need_vid, "这一轮只出图，不该惦记视频")

    def test_a_stage_that_only_makes_clips_asks_for_no_pictures(self):
        shot = Shot(id="sh-6")
        need_img, need_vid = _what_is_missing(shot, False, True)
        self.assertFalse(need_img)
        self.assertTrue(need_vid)


if __name__ == "__main__":
    unittest.main()
