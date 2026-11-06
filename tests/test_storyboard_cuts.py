"""A segment is a timeline of cuts, and the beats have to be filmed.

The film came out as one long take with people talking in it: the
question the storyboard was asked was answered with one camera setup
per segment.  A video model cuts inside one generation very well, but
it only does it if the segment is written as a timeline.

So the two things that make a film a film are counted: the segments
that are one take, and the beats of the novel that no shot filmed.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from dramakit.models import Beat, Scene, Shot  # noqa: E402
from dramakit.pipeline.storyboard import _beat_coverage, _cuts  # noqa: E402


class CutTests(unittest.TestCase):
    def test_a_timeline_has_one_setup_per_timestamp(self):
        action = ("0.0-2.5秒：全景，庄园门厅，夏一朵推门进来；"
                  "2.5-5秒：切近景，她的侧脸，焦点移到背景；"
                  "5-8秒：切茶几上的协议，特写")
        self.assertEqual(_cuts(action), 3)

    def test_a_segment_with_one_timestamp_is_one_take(self):
        self.assertEqual(_cuts("0.0-8秒：中景，陈嫂推门进来"), 1)

    def test_a_segment_without_a_timestamp_has_no_cuts(self):
        self.assertEqual(_cuts("固定机位拍完这场戏"), 0)

    def test_an_empty_action_has_no_cuts(self):
        self.assertEqual(_cuts(""), 0)


class BeatCoverageTests(unittest.TestCase):
    def scene(self, shots, beats):
        sc = Scene(id="sc-1", index=1, location="客厅")
        for i, b in enumerate(beats, 1):
            sc.beats.append(Beat(action=f"第{i}拍", lines=[]))
        for i, covers in enumerate(shots, 1):
            sc.shots.append(Shot(id=f"sh-{i}", index=i, beats=list(covers)))
        return sc

    def test_every_beat_filmed_is_counted(self):
        sc = self.scene([[1], [2], [3]], ["a", "b", "c"])
        filmed, total = _beat_coverage(sc)
        self.assertEqual(filmed, 3)
        self.assertEqual(total, 3)

    def test_a_beat_nobody_filmed_shows_up(self):
        sc = self.scene([[1], [2]], ["a", "b", "c"])
        filmed, total = _beat_coverage(sc)
        self.assertEqual(filmed, 2)
        self.assertEqual(total, 3)

    def test_a_scene_without_beats_has_nothing_to_cover(self):
        sc = self.scene([[1]], [])
        filmed, total = _beat_coverage(sc)
        self.assertEqual(filmed, 0)
        self.assertEqual(total, 0)


if __name__ == "__main__":
    unittest.main()
