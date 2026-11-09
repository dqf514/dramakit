"""The workflow check must not call a working file broken.

The node map in the config serves every file of a kind: the reference
stills workflow has a LoadImage node, the plain one does not.  The id
belongs to the sibling file, so the plain file was reported as broken
even though it renders - and the health panel said the stills were
dead while they worked.

The same file also carried values where node ids belong (a width of
1024 instead of the node that carries the width), which the automatic
mapping had to repair on every run.
"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config  # noqa: E402
from dramakit.providers.comfyui import ComfyUIClient  # noqa: E402
from dramakit.providers.workflow_map import infer_workflow  # noqa: E402

ROOT = pathlib.Path(r"E:\dramakit")
WF_DIR = ROOT / "config" / "comfyui"


def _graph(name: str) -> dict:
    return json.loads((WF_DIR / name).read_text(encoding="utf-8"))


class ValidatorTests(unittest.TestCase):
    """A file that can render must not be reported as broken."""

    def setUp(self):
        self.cfg = Config.load(ROOT / "config" / "default.yaml")
        self.client = ComfyUIClient(self.cfg.comfyui, ROOT)

    def _check(self, rel: str, nmap: dict, kind: str) -> dict:
        """Validate without a server: every node type the file uses counts
        as present, so only the node-id mapping is under test."""
        graph = _graph(pathlib.Path(rel).name)
        types = {(n.get("class_type") or "") for n in graph.values()}
        self.client.available_node_types = lambda: types
        return self.client.validate_workflow(rel, nmap, kind)

    def test_the_plain_stills_file_is_not_broken(self):
        rep = self._check("config/comfyui/t2i_krea2.json",
                          self.cfg.comfyui.t2i_nodes, "t2i")
        self.assertEqual(rep["problems"], [])
        self.assertTrue(rep["ok"], rep["problems"])

    def test_a_slot_the_file_does_not_have_is_a_note_not_a_fault(self):
        # ref_image lives in the sibling file; the plain file has no such
        # node and the render skips the write
        rep = self._check("config/comfyui/t2i_krea2.json",
                          self.cfg.comfyui.t2i_nodes, "t2i")
        self.assertTrue(any("ref_image" in w for w in rep["warnings"]), rep)

    def test_the_reference_stills_file_is_not_broken(self):
        rep = self._check("config/comfyui/t2i_krea2_ref.json",
                          self.cfg.comfyui.t2i_nodes, "t2i")
        self.assertEqual(rep["problems"], [])
        self.assertTrue(rep["ok"], rep["problems"])

    def test_the_video_file_is_not_broken(self):
        rep = self._check("config/comfyui/i2v_shortdrama.json",
                          self.cfg.comfyui.i2v_nodes, "i2v")
        self.assertEqual(rep["problems"], [])
        self.assertTrue(rep["ok"], rep["problems"])


class NodeMapTests(unittest.TestCase):
    """The node map holds node ids, not the values that go into them."""

    def setUp(self):
        self.cfg = Config.load(ROOT / "config" / "default.yaml")

    def test_every_configured_id_is_a_node_in_its_workflow(self):
        graph = _graph("t2i_krea2.json")
        for sem, nid in self.cfg.comfyui.t2i_nodes.items():
            if not nid:
                continue
            if sem == "ref_image":
                # the reference slot belongs to the sibling file
                continue
            self.assertIn(str(nid), graph, f"t2i_nodes.{sem}")

    def test_the_size_and_the_steps_are_nodes_not_numbers(self):
        graph = _graph("t2i_krea2.json")
        for sem in ("width", "height", "steps", "cfg"):
            nid = str(self.cfg.comfyui.t2i_nodes.get(sem) or "")
            self.assertTrue(nid.isdigit(), f"t2i_nodes.{sem} = {nid!r} 不是节点号")
            self.assertIn(nid, graph, f"t2i_nodes.{sem}")

    def test_the_video_frame_count_and_fps_are_nodes_not_numbers(self):
        graph = _graph("i2v_shortdrama.json")
        for sem in ("frames", "fps"):
            nid = str(self.cfg.comfyui.i2v_nodes.get(sem) or "")
            self.assertTrue(nid.isdigit(), f"i2v_nodes.{sem} = {nid!r} 不是节点号")
            self.assertIn(nid, graph, f"i2v_nodes.{sem}")

    def test_the_inferred_map_is_what_the_workflow_says(self):
        info = infer_workflow(_graph("t2i_krea2.json"))
        self.assertEqual(info["t2i"]["width"], self.cfg.comfyui.t2i_nodes["width"])
        self.assertEqual(info["t2i"]["steps"], self.cfg.comfyui.t2i_nodes["steps"])


if __name__ == "__main__":
    unittest.main()
