from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from urllib.parse import quote
from pathlib import Path

from dramakit.ai.autoconfig import save_settings
from dramakit.config import Config
from dramakit.config_history import restore, versions
from dramakit.web.jobs import JobStore
from dramakit.web.server import State, _make_handler


class JobStoreTests(unittest.TestCase):
    def test_roundtrip_and_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = JobStore(Path(tmp) / "jobs.db")
            now = time.time()
            store.save({"id": "j1", "kind": "run_pipeline", "project": "demo",
                        "status": "running", "created_at": now,
                        "progress": {"done": 2, "total": 5}})
            self.assertEqual(store.get("j1")["progress"]["done"], 2)
            self.assertEqual(len(store.list(project="demo", status="running")), 1)
            self.assertEqual(store.settle_leftovers(), 1)
            recovered = store.get("j1")
            self.assertEqual(recovered["status"], "interrupted")
            self.assertIn("重启", recovered["error"])

    def test_project_jobs_are_serialized_and_queued_job_can_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = State(Config(), None, Path(tmp))
            first_started = threading.Event()
            release_first = threading.Event()
            order = []

            def first(stop):
                first_started.set()
                release_first.wait(2)
                order.append("first")
                return {"ok": True}

            def second(stop):
                order.append("second")
                return {"ok": True}

            first_id = state.start_job("test", first, "demo")
            second_id = state.start_job("test", second, "demo")
            self.assertTrue(first_started.wait(1))
            time.sleep(.05)
            self.assertEqual(state.get_job(first_id)["status"], "running")
            self.assertEqual(state.get_job(second_id)["status"], "queued")
            self.assertTrue(state.stop_job(second_id))
            release_first.set()
            self._wait_job(state, first_id)
            self._wait_job(state, second_id)
            self.assertEqual(state.get_job(first_id)["status"], "done")
            self.assertEqual(state.get_job(second_id)["status"], "interrupted")
            self.assertEqual(order, ["first"])
            self.assertIsNotNone(state.get_job(first_id)["finished_at"])

    @staticmethod
    def _wait_job(state, job_id):
        deadline = time.time() + 3
        while time.time() < deadline:
            job = state.get_job(job_id)
            if job["status"] not in ("queued", "running"):
                return
            time.sleep(.02)
        raise AssertionError(f"job did not finish: {job_id}")


class ConfigHistoryTests(unittest.TestCase):
    def test_save_creates_version_and_restore_returns_to_previous_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "default.yaml"
            original = Config()
            original.llm.model = "original-model"
            original.dump_yaml(path)
            save_settings(path, {"llm": {"model": "changed-model"}})
            self.assertEqual(Config.load(path).llm.model, "changed-model")
            history = versions(path)
            self.assertTrue(history)
            restore(path, history[0]["id"])
            self.assertEqual(Config.load(path).llm.model, "original-model")
            self.assertGreaterEqual(len(versions(path)), 2)


class WebRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = Config()
        self.cfg.llm.api_key = "test-secret-that-must-not-leak"
        self.state = State(self.cfg, None, self.root)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(self.state))
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def request(self, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.base + path, data=data,
            headers={"Content-Type": "application/json"} if data else {})
        with urllib.request.urlopen(request, timeout=10) as response:
            return response, json.loads(response.read())

    def wait_job(self, job_id):
        deadline = time.time() + 5
        while time.time() < deadline:
            _, data = self.request(f"/api/jobs?id={job_id}")
            if data["job"]["status"] not in ("queued", "running"):
                return data["job"]
            time.sleep(.03)
        self.fail("background job did not finish")

    def test_config_is_public_and_security_headers_exist(self):
        response, data = self.request("/api/config")
        serialized = json.dumps(data)
        self.assertNotIn("test-secret-that-must-not-leak", serialized)
        self.assertNotIn('"api_key"', serialized)
        self.assertTrue(data["config"]["llm"]["api_key_set"])
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_project_management_lifecycle(self):
        _, created = self.request("/api/new", {"name": "验收项目"})
        self.assertTrue(created["ok"])
        slug = created["slug"]
        _, renamed = self.request("/api/projects/manage", {
            "action": "rename", "project": slug, "name": "验收项目新名"})
        self.assertTrue(renamed["ok"])
        new_slug = renamed["project"]
        _, progress = self.request(f"/api/progress?project={quote(new_slug)}")
        self.assertEqual(progress["project"]["episodes"], [])
        self.assertIn("updated_at", progress["project"])
        _, duplicated = self.request("/api/projects/manage", {
            "action": "duplicate", "project": new_slug, "name": "验收项目副本"})
        self.assertTrue(duplicated["ok"])
        job = self.wait_job(duplicated["job"])
        self.assertEqual(job["status"], "done", job.get("error"))
        copy_slug = job["result"]["project"]
        self.assertTrue((self.root / copy_slug / "project.json").is_file())
        _, deleted = self.request("/api/projects/delete", {"project": new_slug})
        self.assertTrue(deleted["ok"])
        self.assertTrue((self.root / "_trash" / new_slug / "project.json").is_file())
        _, restored = self.request("/api/projects/manage", {
            "action": "restore", "project": new_slug})
        self.assertTrue(restored["ok"])
        self.assertTrue((self.root / new_slug / "project.json").is_file())

    def test_upload_uses_original_filename_and_returns_project_slug(self):
        _, uploaded = self.request("/api/upload", {
            "name": "上传验收项目", "file": "我的小说.txt",
            "text": "第一章 归来\n他回到了这座城市。\n"})
        self.assertTrue(uploaded["ok"])
        self.assertEqual(uploaded["project"], "上传验收项目")
        source = self.root / uploaded["project"] / "source" / "我的小说.txt"
        self.assertTrue(source.is_file())
        self.assertIn("他回到了这座城市", source.read_text(encoding="utf-8"))
        self.assertEqual(uploaded["slug"], uploaded["project"])

    def test_job_list_and_static_enhancements(self):
        _, created = self.request("/api/new", {"name": "任务列表项目"})
        _, response = self.request("/api/projects/manage", {
            "action": "duplicate", "project": created["slug"], "name": "任务列表副本"})
        job = self.wait_job(response["job"])
        self.assertEqual(job["status"], "done", job.get("error"))
        _, listing = self.request("/api/jobs?limit=10")
        self.assertTrue(any(j["id"] == job["id"] for j in listing["jobs"]))
        with urllib.request.urlopen(self.base + "/modern.css", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"prefers-reduced-motion", response.read())
        with urllib.request.urlopen(self.base + "/modern.js", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"runPreflight", response.read())


class BrowserSourceTests(unittest.TestCase):
    def test_all_inline_and_external_scripts_parse(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed")
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", text, re.S)
        scripts.append((root / "dramakit/web/static/modern.js").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            for index, script in enumerate(scripts):
                path = Path(tmp) / f"script-{index}.js"
                path.write_text(script, encoding="utf-8")
                result = subprocess.run([node, "--check", str(path)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0,
                                 f"script {index} failed: {result.stderr}")


if __name__ == "__main__":
    unittest.main()
