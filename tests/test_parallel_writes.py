"""The text stages do the episodes together, not one after another.

The writing work is the same kind of work for every job - a scene here,
a scene there - and the endpoints answer several calls at once.  So the
jobs are asked together, and this measures that they really are: a
model that takes a moment per call, asked four times at once, is done
in about one call's time and not four.
"""
from __future__ import annotations

import threading
import time
import unittest

from dramakit.config import Config
from dramakit.pipeline.base import run_jobs, write_workers


class _Clock:
    """Records when each call started and ended."""

    def __init__(self, seconds: float = 0.25):
        self.seconds = seconds
        self.lock = threading.Lock()
        self.started: list[float] = []
        self.ended: list[float] = []

    def call(self, _job):
        t0 = time.time()
        with self.lock:
            self.started.append(t0)
        time.sleep(self.seconds)
        with self.lock:
            self.ended.append(time.time())
        return "done"


class _Ctx:
    class log:
        @staticmethod
        def info(*_a, **_k):
            pass


class ParallelTests(unittest.TestCase):
    def test_the_jobs_overlap(self):
        clock = _Clock(0.25)
        jobs = list(range(8))
        t0 = time.time()
        out = run_jobs(_Ctx(), jobs, clock.call, workers=4, label="test")
        took = time.time() - t0
        self.assertEqual(len(out), 8)
        for _job, res, err in out:
            self.assertEqual(res, "done")
            self.assertEqual(err, "")
        # eight jobs of a quarter second, four at a time: two rounds, not eight
        self.assertLess(took, 0.25 * 8 * 0.6,
                        "看起来是串行跑的：%d 个任务用了 %.2f 秒" % (len(jobs), took))
        # and no more than four were in flight at once
        points = []
        for s, e in zip(clock.started, clock.ended):
            points.append((s, 1))
            points.append((e, -1))
        points.sort()
        live = peak = 0
        for _at, d in points:
            live += d
            peak = max(peak, live)
        self.assertLessEqual(peak, 4, "同时在跑的请求超过 4 个")

    def test_one_worker_is_the_old_way(self):
        clock = _Clock(0.05)
        out = run_jobs(_Ctx(), list(range(4)), clock.call, workers=1)
        self.assertEqual(len(out), 4)
        for _job, res, _err in out:
            self.assertEqual(res, "done")

    def test_a_job_that_fails_does_not_stop_the_others(self):
        def _one(job):
            if job == 2:
                raise RuntimeError("这个任务炸了")
            return job

        out = run_jobs(_Ctx(), list(range(5)), _one, workers=4)
        self.assertEqual(len(out), 5)
        errs = {job: err for job, _res, err in out}
        self.assertIn("这个任务炸了", errs[2])
        for job in (0, 1, 3, 4):
            self.assertEqual(errs[job], "")

    def test_the_results_come_back_in_the_order_the_jobs_were_given(self):
        out = run_jobs(_Ctx(), list(range(10)),
                       lambda job: job * 2, workers=5)
        self.assertEqual([job for job, _r, _e in out], list(range(10)))
        self.assertEqual([res for _job, res, _e in out],
                         [i * 2 for i in range(10)])


class WorkerCountTests(unittest.TestCase):
    def test_the_text_stages_use_the_configured_number(self):
        cfg = Config()
        cfg.llm.concurrency = 6

        class _C:
            pass

        c = _C()
        c.cfg = cfg
        self.assertEqual(write_workers(c), 6)

        cfg.pipeline.write_concurrency = 3
        self.assertEqual(write_workers(c), 3)


if __name__ == "__main__":
    unittest.main()
