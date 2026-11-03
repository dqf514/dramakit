from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request
from urllib.parse import quote
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from dramakit.config import Config
from dramakit.media import ffmpeg as ff
from dramakit.pipeline.base import Context
from dramakit.pipeline.runner import ORDER
from dramakit.project import ProjectStore
from dramakit.prompts import templates as T
from dramakit.web.server import State, _make_handler


def _media(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, errors="replace")
    if result.returncode:
        raise RuntimeError(result.stderr[-500:])


class FakeLLM:
    def __init__(self, calls: Counter):
        self.calls = calls

    def complete_json(self, system: str, user: str, **_kwargs):
        self.calls["llm"] += 1
        if system == T.ANALYZE_SYSTEM:
            return {
                "title": "归来", "synopsis": "林远回到旧城，赴一场迟到的约定。",
                "genre": "都市情感",
                "art_direction": {"style": "写实电影感", "era": "当代",
                                  "color_palette": "暖色"},
                "characters": [{"name": "林远", "role": "主角", "gender": "男",
                                "age": "30", "personality": "坚定",
                                "appearance": "短发，深色外套",
                                "visual_prompt": "short black hair, dark coat"}],
                "locations": [{"name": "旧城车站", "description": "傍晚的安静车站",
                               "visual_prompt": "quiet old railway station at dusk"}],
                "props": [],
            }
        if system == T.CHARACTER_SHEET_SYSTEM:
            return {"characters": [{"name": "林远",
                                    "anchor_prompt": "30-year-old Chinese man, short black hair, dark coat",
                                    "negative_prompt": "extra fingers, deformed face"}]}
        if system == T.VOICE_CAST_SYSTEM:
            return {"characters": [{"name": "林远", "voice_id": "male-fake",
                                    "pitch": "+0Hz", "rate": "+0%"}]}
        if system == T.SEGMENT_SYSTEM:
            return {"title": "车站重逢", "logline": "林远赶回旧城车站。",
                    "hook": "熟悉的声音从身后响起。", "key_beats": ["归来", "重逢"]}
        if system == T.SCRIPT_SYSTEM:
            return {"scenes": [{
                "location": "旧城车站", "time_of_day": "傍晚", "mood": "感动",
                "bgm_mood": "温暖", "summary": "林远在车站听见故人的呼唤。",
                "lines": [
                    {"kind": "dialogue", "speaker": "林远", "text": "我终于回来了。",
                     "emotion": "感慨"},
                    {"kind": "dialogue", "speaker": "林远", "text": "这一次，我不会再走。",
                     "emotion": "坚定"},
                ],
            }]}
        if system == T.STORYBOARD_SYSTEM:
            return {"shots": [
                {"shot_type": "中景", "camera_move": "推镜", "duration": 1.0,
                 "action": "林远拖着行李走出车站，停下脚步。", "characters": ["林远"],
                 "lines": [1]},
                {"shot_type": "近景", "camera_move": "固定", "duration": 1.0,
                 "action": "林远转身，眼神坚定地看向车站入口。", "characters": ["林远"],
                 "lines": [2]},
            ]}
        if system in (T.PROMPT_SYSTEM, getattr(T, "FLUX3_IMAGE_SYSTEM", T.PROMPT_SYSTEM)):
            return {"prompt": "cinematic shot of a man at an old railway station at dusk",
                    "negative_prompt": "blurry, watermark"}
        return {}


class FakeTTS:
    def __init__(self, calls: Counter):
        self.calls = calls

    def list_voices(self):
        return ["male-fake", "female-fake"]

    def synthesize(self, text: str, voice: str, out_path: str, **_kwargs) -> float:
        self.calls["tts"] += 1
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        duration = 0.7
        _media([ff.ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i",
                f"sine=frequency=440:duration={duration}", "-c:a", "libmp3lame",
                "-b:a", "32k", out_path])
        return duration


class FakeVisual:
    def __init__(self, calls: Counter):
        self.calls = calls

    def ping(self):
        return True

    def generate_image(self, prompt: str, negative: str, *, width: int, height: int,
                       seed: int, steps: int, cfg: float, out_path: str,
                       extra=None, ref_images=None) -> str:
        self.calls["image"] += 1
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        color = "0x355c7d" if seed % 2 else "0x6c5b7b"
        _media([ff.ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i",
                f"color=c={color}:s={width}x{height}:d=0.1", "-frames:v", "1",
                "-update", "1", out_path])
        return out_path

    def generate_video(self, prompt: str, negative: str, *, image_path: str = "",
                       last_image_path: str = "", frames: int = 32, fps: int = 16,
                       seed: int = -1, out_path: str = "", extra=None) -> str:
        self.calls["video"] += 1
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        _media([ff.ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i",
                "testsrc=size=64x64:rate=8:duration=1", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", out_path])
        return out_path


class FakeMusic:
    def __init__(self, calls: Counter):
        self.calls = calls

    def get_track(self, mood: str, duration: float, out_path: str):
        self.calls["music"] += 1
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        _media([ff.ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i",
                f"sine=frequency=220:duration={max(1.0, duration)}",
                "-af", "volume=0.5", "-c:a", "libmp3lame", "-b:a", "32k", out_path])
        return out_path


class FakeProviders:
    def __init__(self):
        self.calls = Counter()
        self.llm = FakeLLM(self.calls)
        self.tts = FakeTTS(self.calls)
        self.visual = FakeVisual(self.calls)
        self.music = FakeMusic(self.calls)

    def llm_for(self, _stage):
        return self.llm

    def bind_stop(self, _event):
        pass


class FullPipelineSimulationTests(unittest.TestCase):
    def setUp(self):
        if not ff.check_available():
            self.skipTest("ffmpeg/ffprobe is required for the real compose and QC stages")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = Config()
        self.cfg.pipeline.fail_fast = True
        self.cfg.pipeline.stages_enabled = list(ORDER)
        self.cfg.ai.auto_tag = False
        self.cfg.segment.strategy = "by_chapter"
        self.cfg.storyboard.shot_duration_range = [1.0, 2.0]
        self.cfg.comfyui.mode = "image_then_video"
        self.cfg.comfyui.video_references = False
        self.cfg.comfyui.concurrency = 1
        self.cfg.comfyui.video_concurrency = 1
        self.cfg.compose.width = 160
        self.cfg.compose.height = 90
        self.cfg.compose.fps = 8
        self.cfg.compose.preset = "ultrafast"
        self.cfg.compose.grade_shots = False
        self.cfg.compose.lipsync = True
        self.cfg.compose.h3_audio = "discard"
        self.cfg.compose.burn_subtitles = False
        self.cfg.compose.generate_cover = False
        self.cfg.compose.ai_declaration = ""
        self.cfg.compose.voice_room = 0.0
        self.cfg.tts.concurrency = 1
        self.providers = FakeProviders()
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
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())

    def wait_job(self, job_id):
        deadline = time.time() + 120
        while time.time() < deadline:
            data = self.request(f"/api/jobs?id={job_id}")
            job = data["job"]
            if job["status"] not in ("queued", "running"):
                return job
            time.sleep(0.05)
        self.fail(f"pipeline job did not finish: {job_id}")

    @staticmethod
    def fake_lipsync(_ctx, jobs):
        results = {}
        for video, _wav, out in jobs:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(video, out)
            results[out] = True
        return results

    def test_all_stages_through_web_api_with_external_nodes_simulated(self):
        uploaded = self.request("/api/upload", {
            "name": "全流水线模拟验收", "file": "归来.txt",
            "text": "第一章 归来\n傍晚，林远拖着行李走出旧城车站。\n"
                    "他听见熟悉的声音，转身望向车站入口，终于决定留下。\n",
        })
        self.assertTrue(uploaded["ok"], uploaded)
        slug = uploaded["slug"]

        def make_context(cfg, store, providers=None):
            return Context(cfg, store, self.providers)

        with patch("dramakit.ai.actions.make_context", make_context), \
                patch("dramakit.pipeline.lipsync._musetalk",
                      wraps=self.fake_lipsync) as lipsync:
            started = self.request("/api/run", {
                "project": slug, "chapters": [1], "stages": ORDER,
            })
            self.assertTrue(started["ok"], started)
            job = self.wait_job(started["job"])

        self.assertEqual(job["status"], "done", job.get("error"))
        result = job["result"]
        self.assertTrue(result["ok"], result)
        self.assertEqual(set(result["results"]), set(ORDER))
        self.assertIn("'failed': 0", result["results"]["visual"])
        self.assertIn("'failed': 0", result["results"]["lipsync"])
        self.assertIn("'errors': 0", result["results"]["precheck"])
        self.assertIn("'blocked': 0", result["results"]["precheck"])
        self.assertIn("'episodes_rendered': 1", result["results"]["compose"])

        store = ProjectStore.open(self.root / slug)
        project = store.load()
        self.assertEqual(len(project.episodes), 1)
        episode = project.episodes[0]
        self.assertEqual(len(episode.scenes), 1)
        self.assertEqual(episode.total_shots, 2)
        self.assertTrue(all(value.value == "done" for value in project.stage_status.values()),
                        project.stage_status)
        self.assertEqual(episode.status.value, "done")
        self.assertEqual(project.seasons[0].status.value, "done")
        self.assertTrue(all(value.value == "done"
                            for value in project.seasons[0].stage_status.values()),
                        project.seasons[0].stage_status)
        self.assertTrue(episode.qc_report["ok"], episode.qc_report)
        self.assertFalse(episode.compose_blocked)

        master = store.abs(episode.video_path)
        self.assertTrue(master.is_file())
        streams = ff.probe_streams(master)
        self.assertIsNotNone(streams["video"])
        self.assertIsNotNone(streams["audio"])
        self.assertGreater(ff.probe_duration(master), 0)
        self.assertTrue(store.abs(episode.subtitle_path).is_file())
        self.assertTrue(store.abs(episode.bgm_path).is_file())
        self.assertTrue((store.root / "qc" / "ep_001.json").is_file())
        self.assertTrue((store.root / "nle" / "ep_001" / "ep_001.fcpxml").is_file())

        for scene in episode.scenes:
            for shot in scene.shots:
                self.assertEqual(shot.status.value, "done")
                self.assertTrue(store.abs(shot.image_path).is_file())
                self.assertTrue(store.abs(shot.video_path).is_file())
            for line in scene.lines:
                self.assertEqual(line.status.value, "done")
                self.assertTrue(store.abs(line.audio_path).is_file())

        self.assertGreaterEqual(self.providers.calls["image"], 7)
        self.assertEqual(self.providers.calls["video"], 2)
        # Two lines are spoken, and one sample is recorded for the one
        # character in the book: the video model takes a character's
        # timbre from a recording, so a character is recorded once, with
        # the rest of the cast.
        self.assertEqual(self.providers.calls["tts"], 3)
        self.assertEqual(self.providers.calls["music"], 1)
        self.assertGreater(self.providers.calls["llm"], 0)
        self.assertTrue(lipsync.called)

        detail = self.request(f"/api/projects/{quote(slug)}")
        self.assertTrue(detail["ok"], detail)
        self.assertTrue(detail["episodes"][0]["video"])
        self.assertEqual(detail["episodes"][0]["qc"]["ok"], True)


if __name__ == "__main__":
    unittest.main()
