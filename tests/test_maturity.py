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

    def test_file_picker_precedes_and_autofills_editable_project_name(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed")
        text = (Path(__file__).parents[1] /
                "dramakit/web/static/index.html").read_text(encoding="utf-8")
        self.assertLess(text.index('id="gFilePicker"'), text.index('id="gName"'))
        start = text.index("function projectNameFromFilename")
        end = text.index("\nasync function probeHealth", start)
        script = text[start:end] + r"""
const assert = require("assert");
const picker = {files: [], value: ""};
const source = {value: ""};
const name = {value: "", dataset: {}};
const fileName = {textContent: ""};
bindGuideSourcePicker(picker, source, name, fileName);
picker.files = [{name: "归来.最终版.txt", size: 2048}];
picker.onchange();
assert.strictEqual(source.value, "归来.最终版.txt");
assert.strictEqual(name.value, "归来.最终版");
picker.files = [{name: "第二卷.md", size: 2048}];
picker.onchange();
assert.strictEqual(name.value, "第二卷");
name.value = "手动项目";
name.oninput();
picker.files = [{name: "另一本书.txt", size: 2048}];
picker.onchange();
assert.strictEqual(name.value, "手动项目");
name.value = "";
picker.files = [{name: "重新开始.txt", size: 2048}];
picker.onchange();
assert.strictEqual(name.value, "重新开始");
"""
        result = subprocess.run([node, "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_sidebar_toggle_stays_at_bottom_and_remains_available_when_collapsed(self):
        # The column of projects can always be got back.  The header used
        # to have a button that opened it on a phone, and the button did
        # nothing: the class it turned on, the scrim it was meant to show,
        # and the close button it was meant to add had no rules in the
        # stylesheet anywhere.  So the column is above the work on a
        # narrow screen instead of hidden behind a button, and the toggle
        # at the bottom of the column stays where it is.
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        header = text[text.index("<header>"):text.index("</header>")]
        aside = text[text.index('<aside id="side">'):text.index("</aside>")]
        self.assertNotIn('id="sideToggle"', header)
        self.assertNotIn('id="mobileSideToggle"', text)
        self.assertLess(aside.index('class="side-content"'), aside.index('id="sideToggle"'))
        self.assertIn("#side.hide{display:flex", text)
        self.assertIn("#side.hide .side-content{display:none}", text)
        # and on a narrow screen the column is above the work, not gone
        narrow = text[text.index("@media(max-width:1180px)"):]
        self.assertIn("#body{flex-direction:column}", narrow)
        self.assertIn("#side{display:block", narrow)
        modern = (root / "dramakit/web/static/modern.js").read_text(encoding="utf-8")
        self.assertIn("updateSideToggle();", modern)
        self.assertIn('sideToggle.setAttribute("aria-expanded", String(!collapsed))', modern)

    def test_palette_is_declared_once_and_both_themes_cover_it(self):
        """Two palettes is how a console ends up with two greens."""
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        modern = (root / "dramakit/web/static/modern.css").read_text(encoding="utf-8")
        self.assertFalse(re.search(r"^\s*--[a-z0-9-]+\s*:", modern, re.M),
                         "modern.css re-declares colour tokens")
        light = text[text.index(":root{"):text.index("html[data-theme=\"dark\"]")]
        dark = text[text.index("html[data-theme=\"dark\"]{"):text.index("*{box-sizing:border-box}")]
        declared = lambda block: set(re.findall(r"--[a-z0-9-]+(?=\s*:)", block))
        # a token that only exists in one theme is a component that goes
        # colourless when the theme is switched
        self.assertTrue(declared(dark) <= declared(light),
                        declared(dark) - declared(light))
        for token in ("--fg", "--fg2", "--fg3", "--confirm", "--go", "--danger2",
                      "--warn", "--on-accent", "--count-bg", "--count-fg", "--monitor"):
            self.assertIn(token, light)
        # everything the second sheet paints with has to be declared
        used = set(re.findall(r"var\((--[a-z0-9-]+)", modern))
        self.assertTrue(used <= declared(light), used - declared(light))
        self.assertEqual(text.count("<style"), 1)
        self.assertEqual(text.count("</style>"), 1)

    def test_text_floor_and_target_size_are_not_below_the_readable_minimum(self):
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        css = text[text.index("<style>"):text.index("</style>")]
        sizes = sorted({float(s) for s in re.findall(r"font-size:\s*([\d.]+)px", css)})
        self.assertTrue(all(s >= 11.5 for s in sizes), [s for s in sizes if s < 11.5])
        self.assertIn("font:14px/1.5", css)
        for rule in (".btn{", ".btn.sm{", ".btn.xs{", ".tg{", ".chip{", ".proj-del{",
                     ".sk-pick{", ".badge{"):
            body = css[css.index(rule):css.index(rule) + 340]
            size = re.search(r"(?:min-)?height:\s*(\d+)", body)
            self.assertTrue(size and int(size.group(1)) >= 22, rule)
        # a token with a raw hex fallback is a colour that exists in one
        # sheet and not in the palette
        self.assertFalse(re.findall(r"var\(--[a-z0-9-]+\s*,\s*#", text))

    def test_stage_state_reports_interrupted_and_failed(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed")
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        script = text[text.index("function stageState(stage){"):
                      text.index("\nfunction epProgress(")] + r"""
const assert = require("assert");
const run = (proj, eps) => { global.S = {detail: {stage_status: proj, episodes: eps}};
  return stageState("script"); };
// a stopped stage is not a pending one: a console that calls it pending
// tells the reader to start over instead of resuming
assert.strictEqual(run({script: "interrupted"}, [{}]), "interrupted");
assert.strictEqual(run({script: "failed"}, [{}]), "failed");
assert.strictEqual(run({script: "running"}, [{}]), "running");
assert.strictEqual(run({}, [{stage_status: {script: "interrupted"}}]), "interrupted");
assert.strictEqual(run({}, [{stage_status: {script: "done"}},
                            {stage_status: {script: "interrupted"}}]), "interrupted");
assert.strictEqual(run({}, [{stage_status: {script: "done"}},
                            {stage_status: {script: "failed"}}]), "partial");
assert.strictEqual(run({}, [{stage_status: {script: "done"}},
                            {stage_status: {script: "done"}}]), "done");
assert.strictEqual(run({}, [{stage_status: {}}]), "pending");
"""
        result = subprocess.run([node, "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_escaping_covers_single_quotes_and_handlers_carry_no_values(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed")
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        esc = text[text.index("const esc = s =>"):text.index("\nconst num =")]
        script = esc + r"""
const assert = require("assert");
// a slug or skill name with an apostrophe in it used to close the string
// around the handler and break the click
assert.strictEqual(esc("O'Brien"), "O&#39;Brien");
assert.strictEqual(esc(`<a"b'c&d>`), "&lt;a&quot;b&#39;c&amp;d&gt;");
"""
        result = subprocess.run([node, "-e", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        # the values are passed as data attributes rather than into the
        # handler text, so a quote in a name is data and not syntax
        self.assertFalse(re.findall(r"on[a-z]+=\"[^\"]*'\$\{", text))
        self.assertIn('data-del="${esc(p.slug)}"', text)
        self.assertIn('data-skill="${esc(x.name)}"', text)

    def test_delete_leaves_the_pages_that_named_the_project(self):
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        body = text[text.index("async function deleteProject(slug){"):
                    text.index("\n}\n", text.index("async function deleteProject(slug){"))]
        for call in ("renderProjects()", "renderCmdProj()", "renderHeader()", "switchPage("):
            self.assertIn(call, body)
        self.assertIn('S.detail=null', body)
        # deleting is a named button, so it can be reached by keyboard
        self.assertIn('class="proj-del"', text)
        self.assertIn('aria-label="删除项目 ', text)

    def test_media_is_named_and_a_running_job_is_not_given_an_invented_percent(self):
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        modern = (root / "dramakit/web/static/modern.js").read_text(encoding="utf-8")
        for tag in re.findall(r"<img [^>]*>", text):
            self.assertIn("alt=", tag, tag)
        for tag in re.findall(r"<video [^>]*>", text):
            self.assertIn("aria-label", tag, tag)
        # the crawl bar is the honest answer to "how far along is it"
        self.assertIn("job-progress indet", modern)
        self.assertNotIn('? 8 : 0', modern)
        self.assertIn("known ? `<div class=\"job-progress\">", modern)
        # a preview must answer the keyboard and a tap, not only the mouse
        self.assertIn("wireVideoPreview", text)
        self.assertNotIn("onmouseenter=\"this.play()\"", text)

    def test_overlays_are_dialogs_that_keep_and_return_the_caret(self):
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        for anchor in ("renderLightbox", "openReader"):
            body = text[text.index(f"function {anchor}(") if anchor == "renderLightbox"
                        else text.index(f"async function {anchor}("):]
            body = body[:body.index("\n}\n")]
            self.assertIn("aria-modal", body, anchor)
            self.assertIn("trapFocus", body, anchor)
        # each one puts the caret back where it was opened from
        self.assertIn("lightbox.last?.focus?.()", text)
        self.assertIn("_rdLast?.focus?.()", text)
        # arrows belong to the field being typed in or the chapter being read
        for handler in ("function lightboxKeys(e){", "function _rdKey(e){"):
            body = text[text.index(handler):text.index(handler) + 420]
            # the guard may sit in the handler or in the helper it calls
            self.assertTrue("isContentEditable" in body or "_rdTyping(e)" in body,
                            handler)
        # and the helper itself knows what counts as typing
        typing = text[text.index("function _rdTyping(e){"):]
        typing = typing[:typing.index("\n}\n")]
        self.assertIn("isContentEditable", typing)

    def test_pages_keep_their_frame_and_their_state_between_polls(self):
        modern = (Path(__file__).parents[1] / "dramakit/web/static/modern.js").read_text(encoding="utf-8")
        # the jobs frame is drawn once; a rebuild every poll closed the log
        # panel and dropped the scroll position
        self.assertIn("if (!jobsShell)", modern)
        self.assertIn("jobsShell = true", modern)
        # the config history card lived inside the tab that loadSettings
        # rewrites whole, so it was thrown away on every visit
        self.assertIn('getElementById("page-settings")', modern)
        self.assertNotIn('getElementById("tab-settings")', modern)
        # a trash list read once never shows what was deleted afterwards
        self.assertIn('details.addEventListener("toggle", () => { if (details.open) renderTrash(); })',
                      modern)
        self.assertNotIn("renderTrash(); }, {once: true})", modern)
        # the accessibility pass marks what it has already done
        self.assertIn('node.dataset.dkA11y = "1"', modern)
        self.assertNotIn("Math.random().toString(36)", modern)

    def test_one_button_starts_the_work_and_the_scope_says_what_it_is(self):
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        # There were four ways to start, and one of them only ticked the
        # steps off.  There is one button now, and it runs the steps that
        # are picked.
        self.assertIn('id="runGo"', text)
        self.assertNotIn('data-act="run-all"', text)
        self.assertNotIn('data-chap="season"', text)
        self.assertNotIn('data-chap="script"', text)
        self.assertNotIn("async function chooseChapters(", text)
        self.assertNotIn("async function startSeason(", text)
        # the chapters are the scope of the run, and the switch says which
        self.assertIn('id="chapScope"', text)
        self.assertIn("body.chapters=chosen", text)
        self.assertIn("body.season=window.__nextSeason||1", text)
        # and the button next to it says what the run is about
        self.assertIn("function drawChapScope()", text)
        self.assertIn('id="runScope"', text)
        # the tick list still has its helpers
        self.assertIn('data-chap="mode"', text)
        self.assertIn('else if(a==="mode") toggleChapMode();', text)
        self.assertIn('data-chap="all"', text)
        self.assertIn('data-chap="none"', text)

    def test_every_page_is_reachable_and_the_bottom_bar_stays_short(self):
        root = Path(__file__).parents[1]
        text = (root / "dramakit/web/static/index.html").read_text(encoding="utf-8")
        modern = (root / "dramakit/web/static/modern.js").read_text(encoding="utf-8")
        css = (root / "dramakit/web/static/modern.css").read_text(encoding="utf-8")
        # skills configure the stages, and had no way in except a button
        # buried in Settings. They are a tab of Settings, and they are
        # also on the workbench, where the steps that use them are.
        self.assertIn('["skills","技能"]', text)
        self.assertIn('skillsPanelHtml()', text)
        self.assertIn('id="page-skills"', text)
        narrow = css[css.index("@media (max-width: 700px)"):]
        # a phone's bottom bar keeps what it can: the node pool stays in
        # the rail, so the header has nothing the rail does not have
        hidden = re.search(r"([^{}]*#rail \.brand[^{}]*)\{", narrow).group(1)
        self.assertIn("#healthBtn", hidden)
        self.assertNotIn('#rail [data-page="nodes"]', hidden)
        self.assertNotIn(".header-nodes", narrow)
        self.assertNotIn('id="nodesBtnHeader"', text)
        self.assertNotIn('getElementById("nodesBtnHeader").onclick', modern)
        # and the rail still has it
        self.assertIn('data-page="nodes"', text)


if __name__ == "__main__":
    unittest.main()
