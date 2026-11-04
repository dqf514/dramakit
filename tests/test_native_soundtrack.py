"""The sound of the film is the sound that came with the picture.

MiniMax H3 makes the voice, the room and the music in one go.  Laying a
score under that, or a library track on top of it, puts two more musics
on one picture - and the film comes out with three things playing at
once.

This builds an episode whose clips each carry one tone, gives it a
library track with a tone of its own, and then measures the tones in
the finished film.  The clips' tones are there.  The library track's
tone is not.

The ffmpeg work is real: the files are made, composed and measured.
"""
from __future__ import annotations

import math
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from dramakit.config import Config
from dramakit.media import ffmpeg as ff
from dramakit.models import Episode, Line, Scene, Shot, ShotType, Status
from dramakit.pipeline import compose as compose_stage
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore


def _tone(path: Path, freq: int, seconds: float = 2.0,
          rate: int = 8000) -> None:
    """A wav with one frequency in it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(rate * seconds)
    frames = bytearray()
    for i in range(n):
        v = int(12000 * math.sin(2 * math.pi * freq * i / rate))
        frames += struct.pack("<h", v)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def _clip(path: Path, freq: int, seconds: float = 2.0) -> None:
    """A video clip with a tone in it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    wav = path.with_suffix(".wav")
    _tone(wav, freq, seconds)
    ff._run([ff.ffmpeg_bin(), "-y", "-f", "lavfi", "-i",
             f"color=c=0x202020:s=160x90:r=8:d={seconds:.3f}",
             "-i", str(wav), "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
             "-pix_fmt", "yuv420p", "-c:a", "aac", str(path)], quiet=True)
    wav.unlink(missing_ok=True)


def _magnitude_at(wav: Path, freq: int) -> float:
    """How much of a frequency is in a wav file."""
    with wave.open(str(wav), "rb") as w:
        rate = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    samples = struct.unpack(f"<{n}h", raw)
    # one frequency, so the whole file can be walked once
    step = 2.0 * math.pi * freq / rate
    re = im = 0.0
    for i, s in enumerate(samples):
        a = step * i
        re += s * math.cos(a)
        im += s * math.sin(a)
    return math.hypot(re, im) / max(1, n)


class NativeSoundtrackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ff.check_available():
            raise unittest.SkipTest("ffmpeg/ffprobe is required")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _project(self, name: str):
        store = ProjectStore.create(self.root, name)
        project = store.load()
        project.meta.title = "音轨测试"
        ep = Episode(id="ep-1", index=1, title="第一集")
        sc = Scene(id="sc-1", index=1, location="客厅", time_of_day="日",
                   summary="两人对话")
        sc.lines = [Line(id="l1", speaker="苏念", text="你到底想怎样",
                         emotion="愤怒", duration=1.0),
                    Line(id="l2", speaker="陆沉", text="我没得选",
                         emotion="冷", duration=1.0)]
        for i, (name_, freq) in enumerate((("sh-1", 440), ("sh-2", 880))):
            clip = store.root / "video" / f"{name_}.mp4"
            _clip(clip, freq)
            shot = Shot(id=name_, index=i, shot_type=ShotType.MEDIUM,
                        duration=2.0, action="", characters=["苏念" if i == 0 else "陆沉"],
                        line_indices=[i + 1], status=Status.DONE,
                        video_path=store.rel(clip))
            sc.shots.append(shot)
        ep.scenes = [sc]
        project.episodes = [ep]
        store.save(project)
        return store, ep

    def test_only_the_clips_own_sound_is_in_the_film(self):
        store, ep = self._project("原生音轨")
        cfg = Config()
        cfg.comfyui.native_audio = True
        cfg.compose.native_audio_exclusive = True
        cfg.compose.width, cfg.compose.height = 160, 90
        cfg.compose.fps = 8
        cfg.compose.preset = "ultrafast"
        cfg.compose.grade_shots = False
        cfg.compose.burn_subtitles = False
        cfg.compose.generate_cover = False
        cfg.compose.ai_declaration = ""
        cfg.compose.transition = "none"
        # a library track with a tone of its own: if it is mixed in, the
        # film will have this frequency in it
        bgm = store.root / "bgm" / "bgm.mp3"
        bgm.parent.mkdir(parents=True, exist_ok=True)
        _tone(bgm.with_suffix(".wav"), 100, 4.0)
        ff._run([ff.ffmpeg_bin(), "-y", "-i", str(bgm.with_suffix(".wav")),
                 "-c:a", "libmp3lame", str(bgm)], quiet=True)
        ep.bgm_path = store.rel(bgm)

        ctx = Context(cfg, store)
        out = compose_stage.compose_episode(ctx, ep)
        self.assertTrue(Path(out).is_file())

        # the film says where the sound came from: the clips' tones are in
        # it, the library track's tone is not
        wav = self.root / "out.wav"
        ff._run([ff.ffmpeg_bin(), "-y", "-i", out, "-ac", "1", "-ar", "8000",
                 str(wav)], quiet=True)
        self.assertGreater(_magnitude_at(wav, 440), 50.0, "片段里的声音没了")
        self.assertGreater(_magnitude_at(wav, 880), 50.0, "片段里的声音没了")
        self.assertLess(_magnitude_at(wav, 100), 5.0,
                        "曲库 BGM 被混进了成片")

        # and the report says the same thing
        mix = (ep.qc_report or {}).get("mix") or {}
        self.assertTrue(mix.get("native_soundtrack"), mix)
        self.assertFalse(mix.get("library_bgm"), mix)
        self.assertEqual(mix.get("bed_segments", 0), 0)


if __name__ == "__main__":
    unittest.main()
