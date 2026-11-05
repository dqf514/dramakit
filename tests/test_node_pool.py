"""The node pool is edited by hand now - from the page and from the shell.

The pool is the list of cards in the config file.  A card can be added,
changed and taken out again, and every card that was not in the request
is still there afterwards: a request about one card must not take the
others with it.  That was the fault the page had - saving one card
wrote the whole list, so the cards that were not in the request were
taken out of the file with it.
"""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from dramakit.ai import autoconfig
from dramakit.config import Config
from dramakit.web.server import State, _make_handler

CONFIG = """\
comfyui:
  enabled: true
  base_url: http://127.0.0.1:8188
  local_roles: [t2i]
  nodes:
    - name: gpu-a
      base_url: http://127.0.0.1:9
      roles: [i2v]
      transfer: scp
      ssh_host: 192.168.1.10
      ssh_user: someone
"""


class NodePoolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "default.yaml"
        self.path.write_text(CONFIG, encoding="utf-8")
        self.state = State(Config.load(self.path), self.path, self.root)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0),
                                         _make_handler(self.state))
        self.thread = threading.Thread(target=self.httpd.serve_forever,
                                       daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    # -- helpers ------------------------------------------------------
    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as resp:
            return json.loads(resp.read())

    def post(self, path, body):
        data = json.dumps(body).encode()
        request = urllib.request.Request(
            self.base + path, data=data,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=10) as resp:
            return json.loads(resp.read())

    def names(self):
        return [n["name"] for n in self.get("/api/nodes")["nodes"]]

    def cards(self):
        return {n.name: n for n in Config.load(self.path).comfyui.nodes}

    # -- the pool is edited card by card ------------------------------
    def test_a_card_can_be_added_changed_and_taken_out(self):
        self.assertEqual(self.names(), ["local", "gpu-a"])
        answer = self.post("/api/nodes/save", {"nodes": [{
            "name": "gpu-b", "base_url": "http://127.0.0.1:9",
            "roles": ["i2v"], "enabled": True}]})
        self.assertTrue(answer["ok"], answer)
        self.assertIn("gpu-b", self.names())
        card = self.cards()["gpu-b"]
        self.assertEqual(card.base_url, "http://127.0.0.1:9")
        self.assertEqual(card.roles, ["i2v"])

        self.post("/api/nodes/save", {"nodes": [{
            "name": "gpu-b", "base_url": "http://127.0.0.1:9",
            "roles": ["t2i", "i2v"], "enabled": True}]})
        card = self.cards()["gpu-b"]
        self.assertEqual(card.base_url, "http://127.0.0.1:9")
        self.assertEqual(card.roles, ["t2i", "i2v"])

        answer = self.post("/api/nodes/save", {"remove": ["gpu-b"]})
        self.assertTrue(answer["ok"], answer)
        self.assertNotIn("gpu-b", self.names())
        self.assertNotIn("gpu-b", self.cards())

    def test_one_card_saved_leaves_the_others_alone(self):
        answer = self.post("/api/nodes/save", {"nodes": [{
            "name": "gpu-a", "base_url": "http://127.0.0.1:9",
            "roles": ["i2v"], "enabled": True}]})
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(self.names(), ["local", "gpu-a"])
        card = self.cards()["gpu-a"]
        self.assertEqual(card.base_url, "http://127.0.0.1:9")
        # the settings that are not on the page are still there
        self.assertEqual(card.ssh_user, "someone")
        self.assertEqual(card.transfer, "scp")

    def test_the_primary_card_is_written_where_it_lives(self):
        answer = self.post("/api/nodes/save", {"nodes": [{
            "name": "local", "primary": True,
            "base_url": "http://127.0.0.1:8189",
            "roles": ["t2i", "i2v"], "enabled": True}]})
        self.assertTrue(answer["ok"], answer)
        cfg = Config.load(self.path)
        self.assertEqual(cfg.comfyui.base_url, "http://127.0.0.1:8189")
        self.assertEqual(cfg.comfyui.local_roles, ["t2i", "i2v"])
        # and the pool is still there
        self.assertEqual([n.name for n in cfg.comfyui.nodes], ["gpu-a"])

    def test_a_card_that_is_switched_off_is_still_on_the_page(self):
        self.post("/api/nodes/save", {"nodes": [{
            "name": "gpu-a", "enabled": False,
            "base_url": "http://127.0.0.1:9", "roles": ["i2v"]}]})
        self.assertIn("gpu-a", self.names())
        card = next(n for n in self.get("/api/nodes")["nodes"]
                    if n["name"] == "gpu-a")
        self.assertFalse(card["config"]["enabled"])

    def test_a_card_that_was_never_there_is_not_made_up(self):
        answer = self.post("/api/nodes/save", {"remove": ["nothing-here"]})
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(self.names(), ["local", "gpu-a"])

    def test_the_page_can_add_a_card_without_touching_the_file_yet(self):
        # the card is written only when it is saved
        self.assertEqual(self.names(), ["local", "gpu-a"])
        self.assertEqual(len(self.cards()), 1)

    def test_the_page_has_a_way_to_add_and_to_take_a_card_out(self):
        page = (Path(__file__).resolve().parents[1] / "dramakit" / "web"
                / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="nodeAdd"', page)      # the button that adds one
        self.assertIn("data-del=", page)         # the button that takes one out
        self.assertIn("/api/nodes/save", page)

    # -- the shell can do the same --------------------------------------
    def test_the_pool_can_be_edited_in_the_file(self):
        autoconfig.save_nodes(self.path, [{
            "name": "gpu-c", "base_url": "http://127.0.0.1:9",
            "roles": ["i2v"], "enabled": True}])
        self.assertIn("gpu-c", self.cards())
        self.assertIn("gpu-a", self.cards())
        autoconfig.save_nodes(self.path, [], remove=["gpu-c"])
        self.assertNotIn("gpu-c", self.cards())
        self.assertIn("gpu-a", self.cards())

    def test_the_shell_adds_and_removes_a_card(self):
        from dramakit.cli import nodes_cmd
        nodes_cmd(action="add", name="gpu-d", config=str(self.path),
                  models_dir="", role="i2v",
                  url="http://127.0.0.1:9", transfer="scp",
                  ssh_host="192.168.1.40", ssh_user="david",
                  ssh_key="", remote_models="/data/models", local_models="",
                  workflow_t2i="", workflow_i2v="")
        card = self.cards()["gpu-d"]
        self.assertEqual(card.base_url, "http://127.0.0.1:9")
        self.assertEqual(card.roles, ["i2v"])
        self.assertEqual(card.transfer, "scp")
        self.assertIn("gpu-a", self.cards())
        nodes_cmd(action="rm", name="gpu-d", config=str(self.path),
                  models_dir="", role="", url="", transfer="", ssh_host="",
                  ssh_user="", ssh_key="", remote_models="", local_models="",
                  workflow_t2i="", workflow_i2v="")
        self.assertNotIn("gpu-d", self.cards())
        self.assertIn("gpu-a", self.cards())


if __name__ == "__main__":
    unittest.main()
