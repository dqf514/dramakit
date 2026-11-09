"""The handoff frame must be told what it is.

The picture list carries the frame the shot before this one ended on, so
the cut lands on the same picture.  The prompt has to say that is what it
is: called a prop, the model was told to keep the shape and the material
of a thing, and the shot before it landed somewhere else entirely.
"""
from __future__ import annotations

import unittest

from dramakit.pipeline.promptgen import _r2v_header


def _plan(*kinds):
    """A picture list: (path, role, kind)."""
    roles = {
        "frame": "the frame this shot continues from",
        "handoff": "the last frame of the shot before this one",
        "character": "the character sheet",
        "room": "the room",
        "prop": "the prop",
    }
    return [(f"/pics/{i}.png", roles[k], k) for i, k in enumerate(kinds, 1)]


class HandoffDescriptionTests(unittest.TestCase):
    def test_the_handoff_is_not_called_a_prop(self):
        header = _r2v_header(_plan("frame", "handoff", "character", "room"))
        self.assertNotIn("(the prop)", header)

    def test_the_handoff_is_named_as_the_frame_the_last_shot_ended_on(self):
        header = _r2v_header(_plan("frame", "handoff", "character", "room"))
        self.assertIn("the frame the shot before this one ended on", header)

    def test_the_summary_says_the_shot_starts_from_it(self):
        header = _r2v_header(_plan("frame", "handoff", "character", "room"))
        summary = header.split("summary:\n")[1].split("\n\n")[0]
        self.assertIn("<Picture 2>", summary)
        self.assertIn("starts from that same picture", summary)

    def test_a_prop_is_still_called_a_prop(self):
        header = _r2v_header(_plan("frame", "character", "room", "prop"))
        self.assertIn("(the prop)", header)

    def test_a_shot_without_a_handoff_says_nothing_about_one(self):
        header = _r2v_header(_plan("frame", "character", "room"))
        self.assertNotIn("the shot before this one", header)
        summary = header.split("summary:\n")[1].split("\n\n")[0]
        self.assertNotIn("starts from that same picture", summary)

    def test_the_first_shot_of_a_scene_has_no_handoff(self):
        header = _r2v_header(_plan("frame", "character", "room"))
        self.assertIn("<Picture 1>", header)


if __name__ == "__main__":
    unittest.main()
