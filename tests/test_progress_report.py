"""What the run is doing right now, as the console sees it.

The console shows how many requests are in flight, how many are done
and how many failed.  This is that tally: a stage says how much work it
has, every job says when it starts and when it ends, and the console
reads the whole lot.
"""
from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from dramakit.pipeline.progress import Progress, read


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".progress.json"
        self.prog = Progress(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_stage_says_how_much_work_it_has(self):
        self.prog.begin("script", 12, 4)
        snap = self.prog.snapshot()
        self.assertEqual(snap["stages"]["script"]["total"], 12)
        self.assertEqual(snap["stages"]["script"]["concurrency"], 4)

    def test_the_requests_in_flight_are_counted(self):
        self.prog.begin("script", 3, 3)
        for _ in range(3):
            self.prog.began("script")
        self.assertEqual(self.prog.snapshot()["inflight"], 3)
        self.prog.finished("script")
        self.assertEqual(self.prog.snapshot()["inflight"], 2)
        self.assertEqual(self.prog.snapshot()["done"], 1)

    def test_a_failure_is_counted_as_a_failure(self):
        self.prog.begin("script", 2, 2)
        self.prog.began("script")
        self.prog.finished("script", ok=False)
        snap = self.prog.snapshot()
        self.assertEqual(snap["failed"], 1)
        self.assertEqual(snap["done"], 0)
        self.assertEqual(snap["inflight"], 0)

    def test_the_lanes_are_named(self):
        self.prog.lane("写作", "storyboard")
        self.prog.lane("绘制", "visual")
        self.assertEqual(self.prog.snapshot()["lanes"]["写作"], "storyboard")
        self.prog.lane_done("绘制")
        self.assertNotIn("绘制", self.prog.snapshot()["lanes"])

    def test_the_file_can_be_read_by_the_console(self):
        self.prog.begin("promptgen", 50, 4)
        self.prog.began("promptgen")
        self.prog.finished("promptgen")
        data = read(self.path)
        # the shape the console already knew is still there
        self.assertEqual(data["promptgen"]["done"], 1)
        self.assertEqual(data["promptgen"]["total"], 50)
        # and the rest is beside it
        self.assertEqual(data["promptgen"]["running"], 0)
        self.assertEqual(data["promptgen"]["started"], 1)
        self.assertEqual(data["_inflight"], 0)

    def test_many_threads_reporting_at_once(self):
        self.prog.begin("storyboard", 40, 8)

        def _one(i):
            self.prog.began("storyboard")
            time.sleep(0.01)
            self.prog.finished("storyboard", ok=(i % 10 != 0))

        threads = [threading.Thread(target=_one, args=(i,)) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        snap = self.prog.snapshot()
        self.assertEqual(snap["done"], 36)
        self.assertEqual(snap["failed"], 4)
        self.assertEqual(snap["inflight"], 0)
        self.assertEqual(snap["started"], 40)

    def test_a_broken_file_is_not_a_crash(self):
        self.path.write_text("{ not json", encoding="utf-8")
        self.assertEqual(read(self.path), {})


if __name__ == "__main__":
    unittest.main()
