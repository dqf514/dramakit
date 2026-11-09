"""The health panel must not lie about what is working.

Two things used to make it lie:

  * The LLM probe asked for "OK" with a budget of five tokens.  A
    reasoning model spends the first tokens thinking, so the answer was
    always cut off and the panel said the model was broken while it was
    working perfectly.  The budget has to leave room for the thinking.

  * The ffmpeg lookup only looked at PATH.  The console is started as
    SYSTEM by the scheduled task, and SYSTEM's PATH is the machine's
    alone - ffmpeg lives in the user's PATH, so every length check and
    every voice sample came back "file not found".
"""
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, r"E:\dramakit")

from dramakit.ai.brain import Brain  # noqa: E402
from dramakit.config import Config  # noqa: E402
from dramakit.media import ffmpeg as ff  # noqa: E402


class ProbeBudgetTests(unittest.TestCase):
    """The probe must leave the model room to think."""

    def test_the_probe_budget_is_not_a_handful_of_tokens(self):
        # five tokens is what a reasoning model spends on thinking alone
        self.assertGreaterEqual(Brain.PROBE_MAX_TOKENS, 32)

    def test_the_budget_is_what_the_probe_actually_sends(self):
        sent = {}

        class FakeLLM:
            cfg = type("C", (), {"model": "m", "max_tokens": 1, "timeout": 1,
                                 "temperature": 0.0, "top_p": 1.0})()

            def complete(self, system, user, **kw):
                sent.update(kw)
                return type("R", (), {"text": "OK"})()

        brain = Brain(Config())
        brain._clients[("", True)] = FakeLLM()
        brain.probe()
        self.assertGreaterEqual(sent.get("max_tokens", 0), 32)


class FfmpegLookupTests(unittest.TestCase):
    """ffmpeg must be found however the program was started."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.bin = pathlib.Path(self.dir.name) / "bin"
        self.bin.mkdir()
        for name in ("ffmpeg.exe", "ffprobe.exe"):
            p = self.bin / name
            p.write_bytes(b"")
        self.saved_path = os.environ.get("PATH", "")
        self.saved_resolved = dict(ff._RESOLVED)
        self.saved_candidates = ff._candidate_dirs
        self.saved_registry = ff._registry_user_paths
        ff._RESOLVED.clear()
        # the machine's own copies must not answer for the test
        ff._candidate_dirs = lambda: []
        ff._registry_user_paths = lambda: []

    def tearDown(self):
        os.environ["PATH"] = self.saved_path
        os.environ.pop("FFMPEG_BIN", None)
        ff._candidate_dirs = self.saved_candidates
        ff._registry_user_paths = self.saved_registry
        ff._RESOLVED.clear()
        ff._RESOLVED.update(self.saved_resolved)
        self.dir.cleanup()

    def test_an_explicit_override_wins(self):
        os.environ["FFMPEG_BIN"] = str(self.bin / "ffmpeg.exe")
        self.assertEqual(ff.ffmpeg_bin(), str(self.bin / "ffmpeg.exe"))

    def test_the_binaries_are_found_without_the_path(self):
        # nothing on PATH and no known install folder: only the override
        # can answer, and it has to be honoured
        os.environ["PATH"] = ""
        os.environ["FFMPEG_BIN"] = str(self.bin / "ffmpeg.exe")
        os.environ["FFPROBE_BIN"] = str(self.bin / "ffprobe.exe")
        ff._RESOLVED.clear()
        self.assertEqual(ff.ffmpeg_bin(), str(self.bin / "ffmpeg.exe"))
        self.assertTrue(ff.check_available())

    def test_a_missing_binary_is_reported_as_missing(self):
        os.environ["PATH"] = ""
        os.environ.pop("FFMPEG_BIN", None)
        ff._RESOLVED.clear()
        self.assertIsNone(ff._resolve("definitely_not_a_real_binary_xyz"))

    def test_a_miss_is_not_remembered_forever(self):
        # the tool can be installed while the console is running: a
        # cached "not here" would keep saying so after it arrived
        os.environ["PATH"] = ""
        os.environ.pop("FFMPEG_BIN", None)
        ff._RESOLVED.clear()
        self.assertIsNone(ff._resolve("definitely_not_a_real_binary_xyz"))
        os.environ["FFMPEG_BIN"] = str(self.bin / "ffmpeg.exe")
        self.assertEqual(ff._resolve("ffmpeg"), str(self.bin / "ffmpeg.exe"))

    def test_check_available_uses_the_same_lookup(self):
        os.environ["FFMPEG_BIN"] = str(self.bin / "ffmpeg.exe")
        os.environ["FFPROBE_BIN"] = str(self.bin / "ffprobe.exe")
        ff._RESOLVED.clear()
        self.assertTrue(ff.check_available())
        self.assertEqual(ff.ffmpeg_bin(), str(self.bin / "ffmpeg.exe"))
        self.assertEqual(ff.ffprobe_bin(), str(self.bin / "ffprobe.exe"))


if __name__ == "__main__":
    unittest.main()
