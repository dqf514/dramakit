"""The frame and the look you see are the ones the run makes.

The panel shows a shape, a size and a style, and the run has to agree
with it: the stills, the clips and the film are all made in that shape,
and every prompt carries that style.  This checks the whole way round -
the project's settings, the settings the run works from, and the text
that goes to the model.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config  # noqa: E402
from dramakit.pipeline.base import Context  # noqa: E402
from dramakit.pipeline.promptgen import _ensure_look  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402


class FrameAndLookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _project(self, name: str):
        store = ProjectStore.create(self.root, name)
        project = store.load()
        return store, project

    def test_a_vertical_project_is_made_vertical(self):
        store, project = self._project("竖屏")
        project.art_direction.aspect_ratio = "9:16"
        project.art_direction.frame_width = 720
        project.art_direction.frame_height = 1280
        store.save(project)

        ctx = Context(Config(), store)
        # the stills, the clips and the film are all made in this shape
        self.assertEqual(ctx.cfg.comfyui.width, 720)
        self.assertEqual(ctx.cfg.comfyui.height, 1280)
        self.assertEqual(ctx.cfg.compose.width, 720)
        self.assertEqual(ctx.cfg.compose.height, 1280)

    def test_a_landscape_project_is_made_landscape(self):
        store, project = self._project("横屏")
        project.art_direction.aspect_ratio = "16:9"
        project.art_direction.frame_width = 1920
        project.art_direction.frame_height = 1080
        store.save(project)

        ctx = Context(Config(), store)
        # the film is cut to the size that was asked for
        self.assertEqual(ctx.cfg.compose.width, 1920)
        self.assertEqual(ctx.cfg.compose.height, 1080)
        # the models are given whole steps, and the difference is cropped
        self.assertEqual(ctx.cfg.comfyui.width, 1920)
        self.assertEqual(ctx.cfg.comfyui.height % 16, 0)

    def test_the_size_the_models_are_given_is_on_whole_steps(self):
        store, project = self._project("对齐")
        project.art_direction.aspect_ratio = "9:16"
        project.art_direction.frame_width = 720
        project.art_direction.frame_height = 1280
        store.save(project)

        ctx = Context(Config(), store)
        for value in (ctx.cfg.comfyui.width, ctx.cfg.comfyui.height):
            self.assertEqual(value % 16, 0, value)

    def test_the_style_reaches_the_prompt(self):
        store, project = self._project("风格")
        project.art_direction.style = "仙侠唯美"
        project.art_direction.style_prompt_prefix = (
            "Chinese xianxia fantasy still, ethereal rim light")
        store.save(project)

        ctx = Context(Config(), store)
        out = _ensure_look(ctx, "a woman in white robes on a stone step")
        self.assertIn("Chinese xianxia fantasy still", out)

    def test_one_project_does_not_change_the_next(self):
        store_a, project_a = self._project("甲")
        project_a.art_direction.aspect_ratio = "9:16"
        project_a.art_direction.frame_width = 720
        project_a.art_direction.frame_height = 1280
        store_a.save(project_a)

        store_b, project_b = self._project("乙")
        project_b.art_direction.aspect_ratio = "16:9"
        project_b.art_direction.frame_width = 1920
        project_b.art_direction.frame_height = 1080
        store_b.save(project_b)

        ctx_a = Context(Config(), store_a)
        ctx_b = Context(Config(), store_b)
        self.assertEqual(ctx_a.cfg.compose.width, 720)
        self.assertEqual(ctx_b.cfg.compose.width, 1920)


if __name__ == "__main__":
    unittest.main(verbosity=2)
