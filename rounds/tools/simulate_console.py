"""Ten rounds of the console, driven the way the page drives it.

The page does not run the pipeline: it asks the server to.  So this drives
the server, over HTTP, with the same requests the page sends - upload,
look, skills, run - and then looks at what came out.

What each round checks:

* 连通 - every endpoint the page uses answers, and answers sanely
* 流水线 - the run reaches "done", every stage says "done", the film and
  its neighbours are on disk, and the film is in the size that was asked
  for
* 前后贯穿 - the ratio, the pixel size, the orientation and the look are
  in the prompts of every stage that draws a picture, and the picture
  model is finally given a prompt that still carries them
* 技能 - the skills chosen for a stage are in that stage's prompt, and
  the skills chosen for another stage are not
* 意外 - a model that fails, a card that fails and a run that is stopped
  all leave the console alive and honest about what happened

The providers are fake, so the round is the pipeline and the console and
not the GPU.  Everything else is the real thing: the real web server, the
real stages, the real ffmpeg.

    python rounds/tools/simulate_console.py            # the ten rounds
    python rounds/tools/simulate_console.py --rounds 3 # a shorter run
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from http.server import ThreadingHTTPServer

import yaml
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dramakit.ai import looks  # noqa: E402
from dramakit.config import Config  # noqa: E402
from dramakit.media import ffmpeg as ff  # noqa: E402
from dramakit.pipeline import frame as pframe  # noqa: E402
from dramakit.pipeline.base import Context  # noqa: E402
from dramakit.pipeline.runner import ORDER  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402
from dramakit.prompts import templates as T  # noqa: E402
from dramakit.web.server import State, _make_handler  # noqa: E402

SCRIPTS = ROOT / "rounds" / "scripts"

# --------------------------------------------------------------------------- #
# which stage a call belongs to
#
# The system prompts are templates: the storyboard's is rendered with the
# frame, so it is not the same string as the template.  What does not
# change is the head of the prompt, up to the first variable - so that is
# what the stage is read from.
# --------------------------------------------------------------------------- #

_SYSTEMS = [
    ("analyze", T.ANALYZE_SYSTEM),
    ("segment", T.SEGMENT_SYSTEM),
    ("character", T.CHARACTER_SHEET_SYSTEM),
    ("voice", T.VOICE_CAST_SYSTEM),
    ("script", T.SCRIPT_SYSTEM),
    ("storyboard", T.STORYBOARD_SYSTEM),
    ("promptgen", T.PROMPT_SYSTEM),
    ("promptgen", T.FLUX3_IMAGE_SYSTEM),
    ("promptgen", T.H3_VIDEO_SYSTEM),
    ("promptgen", T.H3_SCORE_SYSTEM),
]


def _head(tpl: str) -> str:
    """The part of a system prompt that is the same however it is rendered."""
    return re.split(r"\{\{|\{%", tpl)[0].strip()


HEADS = [(_head(tpl), stage) for stage, tpl in _SYSTEMS]
assert len({h for h, _ in HEADS}) == len(HEADS), "two system prompts share a head"


def stage_of(system: str) -> str:
    for head, stage in HEADS:
        if system.startswith(head):
            return stage
    return "?"


# --------------------------------------------------------------------------- #
# the fakes
# --------------------------------------------------------------------------- #


def _media(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True,
                            errors="replace")
    if result.returncode:
        raise RuntimeError(result.stderr[-500:])


class Fault(Exception):
    """A provider that is having a bad day."""


class Fakes:
    """The providers, standing in for the cards and the model.

    Everything they are asked is written down, because the point of the
    round is what was asked.  The model here is deliberately lazy: it
    writes the picture without the look, the way a real one does when it
    is in a hurry - so the round can see whether the console puts the look
    back.
    """

    def __init__(self):
        self.calls = Counter()
        self.llm_log: list[tuple[str, str, str]] = []   # stage, system, user
        self.image_log: list[dict] = []
        self.video_log: list[dict] = []
        self.lock = threading.Lock()
        self.fault: dict = {}

    # -- the model ------------------------------------------------------- #
    def fail_now(self, kind: str, where: str = "", nth: int = 1,
                 persistent: bool = False) -> None:
        """Make the next call of a kind fail.

        `where` is a stage name ("promptgen"), `nth` counts only the calls
        of that stage.  A persistent fault keeps failing: a card that is
        down is down, and the retry has to fail too.
        """
        self.fault = {"kind": kind, "where": where, "nth": nth,
                      "seen": 0, "persistent": persistent}

    def _maybe_fail(self, kind: str, where: str) -> None:
        f = self.fault
        if not f or f.get("kind") != kind:
            return
        if f.get("where") and f.get("where") != where:
            return
        f["seen"] += 1
        if f.get("persistent"):
            raise Fault(f"{kind} 失败了（模拟）")
        if f["seen"] >= int(f.get("nth") or 1):
            self.fault = {}
            raise Fault(f"{kind} 失败了（模拟）")

    def complete_json(self, system: str, user: str, **_kwargs):
        stage = stage_of(system)
        with self.lock:
            self.calls["llm"] += 1
            self.llm_log.append((stage, system, user))
        self._maybe_fail("llm", stage)
        if stage == "analyze":
            return {
                "title": "归来", "synopsis": "林远回到旧城，赴一场迟到的约定。",
                "genre": "都市情感",
                "art_direction": {"style": "写实电影感", "era": "当代",
                                  "color_palette": "暖色"},
                "characters": [{"name": "林远", "role": "主角", "gender": "男",
                                "age": "30", "personality": "坚定",
                                "appearance": "短发，深色外套",
                                "visual_prompt": "short black hair, dark coat"}],
                "locations": [{"name": "旧城车站",
                               "description": "傍晚的安静车站",
                               "visual_prompt": "quiet old railway station at dusk"}],
                "props": [],
            }
        if stage == "character":
            return {"characters": [{
                "name": "林远",
                "anchor_prompt": "30-year-old Chinese man, short black hair, dark coat",
                "negative_prompt": "extra fingers, deformed face"}]}
        if stage == "voice":
            return {"characters": [{"name": "林远", "voice_id": "male-fake",
                                    "pitch": "+0Hz", "rate": "+0%"}]}
        if stage == "segment":
            return {"title": "车站重逢", "logline": "林远赶回旧城车站。",
                    "hook": "熟悉的声音从身后响起。", "key_beats": ["归来", "重逢"]}
        if stage == "script":
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
        if stage == "storyboard":
            return {"shots": [
                {"shot_type": "中景", "camera_move": "推镜", "duration": 1.0,
                 "action": "林远拖着行李走出车站，停下脚步。", "characters": ["林远"],
                 "lines": [1]},
                {"shot_type": "近景", "camera_move": "固定", "duration": 1.0,
                 "action": "林远转身，眼神坚定地看向车站入口。", "characters": ["林远"],
                 "lines": [2]},
            ]}
        if stage == "promptgen":
            if system.startswith(_head(T.H3_VIDEO_SYSTEM)):
                return {"integrated_multimodal_description":
                        "A man in a dark coat walks out of an old station at dusk.",
                        "overall_soundscape": "Distant rain on a metal roof.",
                        "non_diegetic_music": "A slow piano line."}
            if system.startswith(_head(T.H3_SCORE_SYSTEM)):
                return {"integrated_multimodal_description":
                        "An empty railway platform at dusk.",
                        "overall_soundscape": "Wind through the hall.",
                        "non_diegetic_music": "A sparse string quartet."}
            # the still: the lazy answer, with no look and no frame in it
            return {"prompt": "A man in a dark coat at an old station at dusk.",
                    "negative_prompt": "blurry, watermark"}
        return {}

    # -- the card -------------------------------------------------------- #
    def generate_image(self, prompt: str, negative: str, *, width: int,
                       height: int, seed: int, steps: int, cfg: float,
                       out_path: str, extra=None, ref_images=None) -> str:
        with self.lock:
            self.calls["image"] += 1
            self.image_log.append({"prompt": prompt, "width": width,
                                   "height": height, "out": str(out_path)})
        self._maybe_fail("image", "shot" if "shot_" in str(out_path)
                         else "character")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        color = "0x355c7d" if seed % 2 else "0x6c5b7b"
        _media([ff.ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i",
                f"color=c={color}:s={width}x{height}:d=0.1", "-frames:v", "1",
                "-update", "1", out_path])
        return out_path

    def generate_video(self, prompt: str, negative: str, *, image_path: str = "",
                       last_image_path: str = "", frames: int = 32, fps: int = 16,
                       seed: int = -1, out_path: str = "", extra=None) -> str:
        with self.lock:
            self.calls["video"] += 1
            self.video_log.append({"prompt": prompt})
        self._maybe_fail("video", "shot")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        _media([ff.ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i",
                "testsrc=size=64x64:rate=8:duration=1", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", out_path])
        return out_path


class FakeTTS:
    def __init__(self, fakes: Fakes):
        self.fakes = fakes

    def list_voices(self):
        return ["male-fake", "female-fake"]

    def synthesize(self, text: str, voice: str, out_path: str, **_kwargs) -> float:
        with self.fakes.lock:
            self.fakes.calls["tts"] += 1
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        duration = 0.7
        _media([ff.ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i",
                f"sine=frequency=440:duration={duration}", "-c:a", "libmp3lame",
                "-b:a", "32k", out_path])
        return duration


class FakeMusic:
    def __init__(self, fakes: Fakes):
        self.fakes = fakes

    def get_track(self, mood: str, duration: float, out_path: str):
        with self.fakes.lock:
            self.fakes.calls["music"] += 1
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        _media([ff.ffmpeg_bin(), "-y", "-v", "error", "-f", "lavfi", "-i",
                f"sine=frequency=220:duration={max(1.0, duration)}",
                "-af", "volume=0.5", "-c:a", "libmp3lame", "-b:a", "32k", out_path])
        return out_path


class FakeProviders:
    """The provider bundle the stages ask for."""

    def __init__(self, fakes: Fakes):
        self.fakes = fakes
        self.llm = fakes
        self.tts = FakeTTS(fakes)
        self.music = FakeMusic(fakes)
        self.visual = fakes

    def llm_for(self, _stage):
        return self.llm

    def bind_stop(self, _event):
        pass

    def ping(self):
        return True


# --------------------------------------------------------------------------- #
# the console
# --------------------------------------------------------------------------- #


class Console:
    """The web console, on a port of its own."""

    def __init__(self, cfg: Config, root: Path, fakes: Fakes):
        self.fakes = fakes
        self.cfgs: list[Config] = []   # the settings each run was given
        self.providers = FakeProviders(fakes)
        # The console writes into the file it was given.  The harness
        # gives it a copy of its own settings, so that what a round
        # changes - the pool of cards, the look of a project - is
        # changed in the copy and not on this machine.
        self.cfg_path = root / "config" / "default.yaml"
        self.cfg_path.parent.mkdir(parents=True, exist_ok=True)
        self.cfg_path.write_text(
            yaml.safe_dump(cfg.model_dump(mode="json"), allow_unicode=True,
                           sort_keys=False), encoding="utf-8")
        self.state = State(cfg, self.cfg_path, root)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0),
                                         _make_handler(self.state))
        self.thread = threading.Thread(target=self.httpd.serve_forever,
                                       daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_port}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)

    def get(self, path: str, timeout: float = 30):
        req = urllib.request.Request(self.base + path)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    def post(self, path: str, body: dict, timeout: float = 60):
        data = json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    def wait_job(self, job_id: str, timeout: float = 600):
        deadline = time.time() + timeout
        job = {}
        while time.time() < deadline:
            job = self.get(f"/api/jobs?id={job_id}")["job"]
            if job.get("status") not in ("queued", "running"):
                return job
            time.sleep(0.05)
        raise TimeoutError(f"job {job_id} did not finish: {job}")


# --------------------------------------------------------------------------- #
# the report
# --------------------------------------------------------------------------- #


class Round:
    def __init__(self, number: int, name: str):
        self.number = number
        self.name = name
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, what: str, ok: bool, detail: str = ""):
        self.checks.append((what, bool(ok), detail))
        return ok

    @property
    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    def failures(self) -> list[str]:
        return [f"{what}：{detail}" for what, ok, detail in self.checks if not ok]

    def report(self, verbose: bool = False) -> str:
        mark = "✅" if self.ok else "❌"
        bad = [c for c in self.checks if not c[1]]
        lines = [f"{mark} 第{self.number}轮 {self.name}"
                 f"（{len(self.checks)} 项检查，{len(bad)} 项不通过）"]
        for what, ok, detail in self.checks:
            if not ok:
                lines.append(f"    × {what}" + (f" — {detail}" if detail else ""))
            elif verbose and detail:
                lines.append(f"    · {what} — {detail}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# the rounds
# --------------------------------------------------------------------------- #

# the skills each round asks for: every stage gets a different set every
# round, and one round asks for nothing at all - a project whose user
# unchecked everything still has to run.
SKILL_SETS = [
    {"analyze": ["short-drama-novel-analyze", "short-drama-develop"],
     "script": ["short-drama-write", "screenwriting-theory/sw-dialogue"],
     "storyboard": ["short-drama-storyboard"],
     "promptgen": ["short-drama-image-prompts", "short-drama-video-prompts"]},
    {"analyze": ["short-drama-novel-analyze"],
     "script": ["short-drama-write",
                "screenwriting-theory/sw-chinese-series-practice"],
     "storyboard": ["short-drama-storyboard",
                    "screenwriting-theory/sw-scene-craft"],
     "promptgen": ["short-drama-image-prompts"]},
    {"analyze": [], "script": [], "storyboard": [], "promptgen": []},
    {"analyze": ["short-drama-novel-analyze", "short-drama-develop",
                 "screenwriting-theory/sw-genre-anatomy"],
     "script": ["short-drama-write", "screenwriting-theory/sw-story-structure"],
     "storyboard": ["short-drama-storyboard",
                    "screenwriting-theory/sw-scene-craft"],
     "promptgen": ["short-drama-video-prompts"]},
    {"analyze": ["short-drama-develop"],
     "script": ["short-drama-write", "screenwriting-theory/sw-dialogue",
                "screenwriting-theory/sw-scene-craft"],
     "storyboard": ["short-drama-storyboard"],
     "promptgen": ["short-drama-image-prompts",
                   "screenwriting-theory/sw-scene-craft"]},
]

# the frame of each round: the two shapes, the four sizes of each
FRAMES = [
    ("9:16", "1080x1920"), ("16:9", "1920x1080"),
    ("9:16", "768x1344"), ("16:9", "1344x768"),
    ("9:16", "720x1280"), ("16:9", "1280x720"),
    ("9:16", "1440x2560"), ("16:9", "3840x2160"),
    ("9:16", "1080x1920"), ("16:9", "1920x1080"),
]


def _size(aspect_id: str, size_id: str) -> dict:
    for s in looks.aspect(aspect_id)["sizes"]:
        if s["id"] == size_id:
            return s
    raise KeyError(size_id)


def _check_workflow(rd: Round, aspect_id: str, size: dict, style: dict) -> None:
    """What the workflow file carries to ComfyUI.

    The frame is a setting in the workflow: the width and the height of
    the node that makes the picture are written into the file that goes
    to ComfyUI.  The look is not a setting at all - it is a sentence in
    the prompt, and the workflow must not carry it.
    """
    import copy as _copy

    from dramakit.models import ArtDirection
    from dramakit.providers.comfyui import ComfyUIClient

    art = ArtDirection(aspect_ratio=aspect_id, frame_width=size["w"],
                       frame_height=size["h"],
                       style_prompt_prefix=style["prompt"])
    cfg = pframe.apply_frame(Config(), art)
    client = ComfyUIClient(cfg.comfyui)
    want = (cfg.comfyui.width, cfg.comfyui.height)
    want_v = (cfg.comfyui.video_width, cfg.comfyui.video_height)
    head = style["prompt"].split(",")[0].strip()
    for kind, wf, sizes in (("出图", cfg.comfyui.t2i_workflow, want),
                            ("出视频", cfg.comfyui.i2v_workflow, want_v)):
        try:
            graph = _copy.deepcopy(client._load_workflow(wf))
            nm, _info, _refs = client._resolved_nodes(
                "t2i" if kind == "出图" else "i2v", graph)
            client._set(graph, nm, "width", "width", sizes[0])
            client._set(graph, nm, "height", "height", sizes[1])
        except Exception as e:  # noqa: BLE001
            rd.check(f"{kind} 工作流能读", False, repr(e)[:160])
            continue
        found = [(nid, (n.get("inputs") or {}).get("width"),
                  (n.get("inputs") or {}).get("height"))
                 for nid, n in graph.items()
                 if isinstance((n.get("inputs") or {}).get("width"), (int, float))
                 and isinstance((n.get("inputs") or {}).get("height"), (int, float))]
        rd.check(f"{kind} 工作流里带的是画幅的尺寸",
                 any(f[1] == sizes[0] and f[2] == sizes[1] for f in found),
                 f"要 {sizes[0]}x{sizes[1]}，工作流里有 {found}")
        rd.check(f"{kind} 工作流里没有画风词",
                 head not in json.dumps(graph, ensure_ascii=False), head)


def run_round(console: Console, number: int, script_path: Path,
              aspect_id: str, size_id: str, style_id: str,
              skills: dict, tmp_root: Path, h3: bool = False) -> Round:
    """One round: upload, look, skills, run, look at what came out."""
    size = _size(aspect_id, size_id)
    style = looks.style(style_id)
    rd = Round(number, f"{aspect_id} {size_id} · {style['name']}"
                        + (" · H3" if h3 else ""))
    # the video workflow decides whether the clips get an H3 prompt of
    # their own or borrow the picture's - both are worth walking through
    console.state.cfg.comfyui.i2v_workflow = (
        "config/comfyui/i2v_minimax_h3.json" if h3
        else "config/comfyui/i2v_animatediff.json")

    # ---- the endpoints the page leans on -------------------------------- #
    try:
        state = console.get("/api/state")
        rd.check("GET /api/state", state.get("ok") is not False
                 and "projects" in state, str(list(state))[:80])
    except Exception as e:  # noqa: BLE001
        rd.check("GET /api/state", False, repr(e))
        return rd
    try:
        lk = console.get("/api/looks")
        rd.check("GET /api/looks", lk.get("ok") and len(lk.get("aspects", [])) == 2
                 and len(lk.get("styles", [])) >= 16,
                 f"{len(lk.get('aspects', []))} 画幅 / {len(lk.get('styles', []))} 风格")
    except Exception as e:  # noqa: BLE001
        rd.check("GET /api/looks", False, repr(e))
    try:
        sk = console.get("/api/skills")
        rd.check("GET /api/skills", sk.get("ok") and len(sk.get("skills", [])) > 0,
                 f"{len(sk.get('skills', []))} 个技能")
    except Exception as e:  # noqa: BLE001
        rd.check("GET /api/skills", False, repr(e))

    # ---- upload --------------------------------------------------------- #
    text = script_path.read_text(encoding="utf-8", errors="replace")
    up = console.post("/api/upload", {"name": f"第{number}轮模拟", "file":
                                      script_path.name, "text": text})
    if not up.get("ok"):
        rd.check("POST /api/upload", False, str(up)[:160])
        return rd
    rd.check("POST /api/upload", True)
    slug = up["slug"]

    # ---- the look ------------------------------------------------------- #
    look = console.post("/api/project/look", {
        "project": slug, "aspect_ratio": aspect_id,
        "width": size["w"], "height": size["h"], "style": style_id})
    rd.check("POST /api/project/look", look.get("ok"), str(look)[:160])
    frame = (look.get("frame") or {})
    rd.check("画幅写进了项目", frame.get("width") == size["w"]
             and frame.get("height") == size["h"]
             and frame.get("aspect_ratio") == aspect_id,
             f"项目说 {frame.get('width')}x{frame.get('height')}")

    # ---- the skills ----------------------------------------------------- #
    # a name that does not exist must not break the save
    saved = console.post("/api/skills/save", {
        "project": slug,
        "selection": {k: list(v) + ["不存在的技能"] for k, v in skills.items()}})
    rd.check("POST /api/skills/save", saved.get("ok"), str(saved)[:160])
    eff = (saved.get("selection") or {})
    rd.check("不存在的技能被丢掉",
             all("不存在的技能" not in (eff.get(k) or [])
                 for k in ("analyze", "script", "storyboard", "promptgen")))
    for stage, names in skills.items():
        if stage in eff:
            rd.check(f"{stage} 的技能按项目存下来了",
                     list(eff.get(stage) or []) == list(names),
                     f"存了 {eff.get(stage)}，要的是 {list(names)}")

    # ---- the run -------------------------------------------------------- #
    console.fakes.llm_log.clear()
    console.fakes.image_log.clear()
    console.fakes.video_log.clear()
    console.cfgs.clear()

    def make_context(cfg, store, providers=None):
        ctx = Context(cfg, store, console.providers)
        # the settings the stages are given are what ComfyUI will be
        # asked for, so they are kept to be looked at
        console.cfgs.append(ctx.cfg)
        return ctx

    started = console.post("/api/run", {"project": slug, "chapters": [1],
                                         "stages": ORDER})
    if not started.get("ok"):
        rd.check("POST /api/run", False, str(started)[:160])
        return rd
    rd.check("POST /api/run", True)
    with patch("dramakit.ai.actions.make_context", make_context), \
            patch("dramakit.pipeline.lipsync._musetalk",
                  wraps=_fake_lipsync):
        job = console.wait_job(started["job"])

    rd.check("流水线跑完了", job.get("status") == "done",
             f"status={job.get('status')} error={str(job.get('error'))[:160]}")
    result = job.get("result") or {}
    results = result.get("results") or {}
    rd.check("每个阶段都跑了", set(results) >= set(ORDER),
             f"跑了 {sorted(results)}")
    for stage in ORDER:
        # the report gives each stage's result as a string of its counts
        val = results.get(stage)
        text = val if isinstance(val, str) else str(val)
        if "'error':" in text or '"error":' in text:
            rd.check(f"阶段 {stage} 没有报错", False, text[:160])

    # ---- the project on disk -------------------------------------------- #
    store = ProjectStore.open(tmp_root / slug)
    project = store.load()
    statuses = {k: v.value for k, v in (project.stage_status or {}).items()}
    rd.check("所有阶段的状态是 done",
             all(statuses.get(s) == "done" for s in ORDER),
             ", ".join(f"{s}={statuses.get(s)}" for s in ORDER
                       if statuses.get(s) != "done"))
    rd.check("成片存在", bool(project.episodes)
             and bool(project.episodes[0].video_path), "")
    if project.episodes:
        ep = project.episodes[0]
        rd.check("这一集的状态是 done", ep.status.value == "done", ep.status.value)
        rd.check("质检通过", bool((ep.qc_report or {}).get("ok")),
                 str(ep.qc_report)[:120])
        master = store.abs(ep.video_path)
        rd.check("成片在磁盘上", master.is_file(), str(master))
        if master.is_file():
            streams = ff.probe_streams(master)
            v = streams.get("video") or {}
            rd.check("成片就是那个画幅",
                     v.get("width") == size["w"] and v.get("height") == size["h"],
                     f"成片 {v.get('width')}x{v.get('height')}，"
                     f"要的是 {size['w']}x{size['h']}")
        rd.check("字幕存在", store.abs(ep.subtitle_path).is_file(), "")
        rd.check("配乐存在", store.abs(ep.bgm_path).is_file(), "")
        rd.check("质检报告存在", (store.root / "qc" / "ep_001.json").is_file(), "")
        rd.check("剪辑单存在",
                 (store.root / "nle" / "ep_001" / "ep_001.fcpxml").is_file(), "")
        shots = [sh for sc in ep.scenes for sh in sc.shots]
        rd.check("镜头都画完了",
                 bool(shots) and all(sh.status.value == "done" for sh in shots),
                 ", ".join(f"{sh.id}={sh.status.value}" for sh in shots
                           if sh.status.value != "done"))
        rd.check("每个镜头都有图有视频",
                 all(store.abs(sh.image_path).is_file()
                     and store.abs(sh.video_path).is_file() for sh in shots), "")
        # The still is made in the frame the project asked for: the same
        # shape and, as near as the models allow, the same size.  The
        # character portraits are square on purpose and are left out.
        imgs = [i for i in console.fakes.image_log if "shot_" in i["out"]]
        want_ratio = 16 / 9 if aspect_id == "16:9" else 9 / 16
        want_w, want_h = pframe.snap_size(size["w"], size["h"])
        rd.check("出图用的是画幅的画幅比",
                 bool(imgs) and all(abs(i["width"] / i["height"]
                                        - want_w / want_h) < 0.005 for i in imgs),
                 ", ".join(f"{i['width']}x{i['height']}" for i in imgs[:4]))
        rd.check("出图用的是画幅里的分辨率",
                 bool(imgs) and all(i["width"] == want_w and i["height"] == want_h
                                    for i in imgs),
                 f"要 {want_w}x{want_h}，拿到 "
                 + ", ".join(f"{i['width']}x{i['height']}" for i in imgs[:4]))
        # and the delivery size is that same shape, to within a hair
        rd.check("交付尺寸与画幅相符",
                 abs(size["w"] / size["h"] - want_ratio) / want_ratio < 0.02,
                 f"{size['w']}x{size['h']} 对 {aspect_id}")

    # ---- ComfyUI 被要求的是这个尺寸 ------------------------------------- #
    want_w, want_h = pframe.snap_size(size["w"], size["h"])
    rd.check("ComfyUI 出图尺寸就是画幅里的尺寸",
             bool(console.cfgs) and all(
                 c.comfyui.width == want_w and c.comfyui.height == want_h
                 for c in console.cfgs),
             ", ".join(f"{c.comfyui.width}x{c.comfyui.height}"
                       for c in console.cfgs[:3]))
    rd.check("ComfyUI 视频尺寸就是画幅里的尺寸",
             bool(console.cfgs) and all(
                 c.comfyui.video_width == want_w
                 and c.comfyui.video_height == want_h
                 for c in console.cfgs),
             ", ".join(f"{c.comfyui.video_width}x{c.comfyui.video_height}"
                       for c in console.cfgs[:3]))
    rd.check("成片尺寸就是画幅里的尺寸",
             bool(console.cfgs) and all(
                 c.compose.width == size["w"] and c.compose.height == size["h"]
                 for c in console.cfgs),
             ", ".join(f"{c.compose.width}x{c.compose.height}"
                       for c in console.cfgs[:3]))

    # ---- 工作流文件里带的是什么 ------------------------------------------ #
    _check_workflow(rd, aspect_id, size, style)

    # ---- 前后贯穿 ------------------------------------------------------- #
    _check_continuity(rd, console, style, aspect_id, size, project)

    # ---- 技能 ------------------------------------------------------------ #
    _check_skills(rd, console, skills)

    return rd


def _check_continuity(rd: Round, console: Console, style: dict,
                      aspect_id: str, size: dict, project) -> None:
    """The ratio, the size, the look - in every prompt that draws."""
    ratio = aspect_id
    px = f"{size['w']}×{size['h']}"
    orientation = "竖屏" if aspect_id == "9:16" else "横屏"
    prefix = style["prompt"]
    log = console.fakes.llm_log

    def calls(stage):
        return [(s, u) for st, s, u in log if st == stage]

    # -- the stages that draw a picture must say what shape it is -------- #
    for stage, need in (("character", ("ratio", "size")),
                        ("storyboard", ("ratio", "size", "orientation")),
                        ("promptgen", ("ratio", "size"))):
        cs = calls(stage)
        if not cs:
            rd.check(f"{stage} 阶段有提示词", False, "一次模型调用都没有")
            continue
        missing = []
        for _sys, user in cs:
            if "ratio" in need and ratio not in user:
                missing.append("画幅")
            if "size" in need and px not in user:
                missing.append(f"尺寸 {px}")
            if "orientation" in need and orientation not in user:
                missing.append("横竖")
        rd.check(f"{stage} 的提示词里带着{'、'.join(need)}",
                 not missing, "少了 " + "、".join(sorted(set(missing)))
                 if missing else f"{len(cs)} 次调用")

    # -- the look --------------------------------------------------------- #
    for stage in ("character", "promptgen"):
        cs = calls(stage)
        if not cs:
            continue
        missing = [s for s, u in cs if prefix not in u]
        rd.check(f"{stage} 的提示词里带着画风", not missing,
                 f"{len(missing)}/{len(cs)} 次调用没有画风"
                 if missing else f"{len(cs)} 次调用")

    # -- the picture model must finally get a prompt that carries it ----- #
    style_calls = [u for _s, u in calls("storyboard")]
    rd.check("分镜阶段知道画风",
             bool(style_calls) and any(prefix in u for u in style_calls),
             "分镜的提示词里没有画风"
             + (f"：{style_calls[0][style_calls[0].find('分镜规则'):][:260]!r}"
                if style_calls and "分镜规则" in style_calls[0] else ""))

    imgs = console.fakes.image_log
    if imgs:
        no_style = [i for i in imgs if prefix not in i["prompt"]]
        rd.check("出图模型拿到的提示词里有画风", not no_style,
                 f"{len(no_style)}/{len(imgs)} 张没有画风")
    vids = console.fakes.video_log
    if vids:
        no_style = [v for v in vids if prefix not in v["prompt"]]
        rd.check("出视频模型拿到的提示词里有画风", not no_style,
                 f"{len(no_style)}/{len(vids)} 段没有画风")


def _check_skills(rd: Round, console: Console, skills: dict) -> None:
    """The skills chosen for a stage are in that stage's prompt - and
    the ones chosen for another stage are not."""
    log = console.fakes.llm_log

    def calls(stage):
        return [u for st, _s, u in log if st == stage]

    for stage, names in skills.items():
        cs = calls(stage)
        if not cs:
            rd.check(f"{stage} 的技能进了提示词", False, "一次模型调用都没有")
            continue
        joined = "\n".join(cs)
        missing = [n for n in names
                   if f"=== 规矩（来自 skill：{n}）===" not in joined]
        rd.check(f"{stage} 的技能进了提示词", not missing,
                 "少了 " + "、".join(missing) if missing
                 else f"{len(names)} 个技能")
        # and nothing from another stage - a skill that was not chosen for
        # this stage must not turn up here, rules or reference documents
        chosen = set(names)
        came = set(re.findall(r"来自 skill：([^）\n]+)", joined))
        came = {c.strip().split(" ")[0] for c in came}
        leaked = sorted(c for c in came if c not in chosen)
        rd.check(f"{stage} 的提示词里没有没选的技能", not leaked,
                 "混进了 " + "、".join(leaked) if leaked else "")


def _counts(val) -> dict:
    """The counts a stage reported, which the job carries as a string."""
    if isinstance(val, dict):
        return val
    try:
        out = ast.literal_eval(val)
        return out if isinstance(out, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _fake_lipsync(_ctx, jobs):
    """The lip-sync, faked: the clip is copied over the mouth."""
    results = {}
    for video, _wav, out in jobs:
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(video, out)
        results[out] = True
    return results


# --------------------------------------------------------------------------- #
# the faults
# --------------------------------------------------------------------------- #


def run_node_pool(console: Console, number: int = 90) -> Round:
    """The pool of cards, added and taken out by hand.

    The pool is the list of cards in the config file.  A card is added,
    changed and taken out again here, and the cards that were there
    before are still there afterwards: a request about one card must
    not take the others with it.
    """
    rd = Round(number, "节点池：增删改")
    try:
        pool = console.get("/api/nodes")
    except Exception as e:  # noqa: BLE001
        rd.check("GET /api/nodes", False, repr(e))
        return rd
    before = [n["name"] for n in pool.get("nodes") or []]
    rd.check("GET /api/nodes", bool(pool.get("ok")) and len(before) >= 1,
             str(before))
    name = "harness-card"

    answer = console.post("/api/nodes/save", {"nodes": [{
        "name": name, "base_url": "http://127.0.0.1:8188",
        "roles": ["i2v"], "enabled": True}]})
    rd.check("新增一台节点", bool(answer.get("ok")), str(answer)[:160])
    now = [n["name"] for n in console.get("/api/nodes").get("nodes") or []]
    rd.check("新增的节点在列表里了", name in now, str(now))
    rd.check("原来的节点一个都没少", set(before) <= set(now),
             f"{before} -> {now}")

    cfg = Config.load(console.cfg_path)
    card = next((n for n in cfg.comfyui.nodes if n.name == name), None)
    rd.check("文件里记下了这台节点",
             card is not None and card.base_url == "http://127.0.0.1:8188",
             str(card))

    console.post("/api/nodes/save", {"nodes": [{
        "name": name, "base_url": "http://127.0.0.1:8199",
        "roles": ["t2i", "i2v"], "enabled": True}]})
    cfg = Config.load(console.cfg_path)
    card = next((n for n in cfg.comfyui.nodes if n.name == name), None)
    rd.check("改过的地址存住了",
             card is not None and card.base_url == "http://127.0.0.1:8199",
             str(getattr(card, "base_url", None)))
    rd.check("改过的角色存住了",
             card is not None and list(card.roles) == ["t2i", "i2v"],
             str(getattr(card, "roles", None)))

    answer = console.post("/api/nodes/save", {"remove": [name]})
    rd.check("删掉一台节点", bool(answer.get("ok")), str(answer)[:160])
    now = [n["name"] for n in console.get("/api/nodes").get("nodes") or []]
    rd.check("删掉的节点不在列表里了", name not in now, str(now))
    rd.check("删掉一台不影响别的", set(before) <= set(now),
             f"{before} -> {now}")
    cfg = Config.load(console.cfg_path)
    rd.check("文件里也没有这台节点了",
             all(n.name != name for n in cfg.comfyui.nodes),
             str([n.name for n in cfg.comfyui.nodes]))
    primary = next((n for n in console.get("/api/nodes").get("nodes") or []
                    if (n.get("config") or {}).get("primary")), None)
    rd.check("本机节点还在", bool(primary), str(primary)[:120])
    return rd


def run_faults(console: Console, tmp_root: Path) -> list[Round]:
    """What happens when something breaks."""
    out: list[Round] = []
    script = SCRIPTS / "round01.txt"
    styles = [s["id"] for s in looks.looks()["styles"]]

    # ---- a model that gives up mid-prompt ------------------------------- #
    rd = Round(101, "意外一：出图提示词阶段模型报错")
    console.fakes.fail_now("llm", "promptgen", nth=1)
    out.append(_fault_round(console, rd, script, "9:16", "720x1280",
                             styles[0], SKILL_SETS[0], tmp_root,
                             expect="done"))

    # ---- a card that gives up ------------------------------------------- #
    rd = Round(102, "意外二：出图时显卡报错")
    console.fakes.fail_now("image", "shot", nth=1, persistent=True)
    out.append(_fault_round(console, rd, script, "16:9", "1280x720",
                             styles[1], SKILL_SETS[0], tmp_root,
                             expect="degraded"))

    # ---- a run that is stopped ------------------------------------------ #
    rd = Round(103, "意外三：跑到一半被人叫停")
    out.append(_fault_stop(console, rd, script, styles[2], tmp_root))
    return out


def _fault_round(console: Console, rd: Round, script: Path, aspect_id: str,
                 size_id: str, style_id: str, skills: dict, tmp_root: Path,
                 expect: str) -> Round:
    size = _size(aspect_id, size_id)
    up = console.post("/api/upload", {"name": rd.name, "file": script.name,
                                      "text": script.read_text(encoding="utf-8",
                                                              errors="replace")})
    slug = up["slug"]
    console.post("/api/project/look", {
        "project": slug, "aspect_ratio": aspect_id, "width": size["w"],
        "height": size["h"], "style": style_id})
    console.post("/api/skills/save", {"project": slug, "selection": skills})
    started = console.post("/api/run", {"project": slug, "chapters": [1],
                                         "stages": ORDER})
    rd.check("POST /api/run", started.get("ok"), str(started)[:120])

    def make_context(cfg, store, providers=None):
        return Context(cfg, store, console.providers)

    with patch("dramakit.ai.actions.make_context", make_context), \
            patch("dramakit.pipeline.lipsync._musetalk", wraps=_fake_lipsync):
        job = console.wait_job(started["job"], timeout=300)

    # the console is still there
    try:
        alive = console.get("/api/state")
        rd.check("控制台还活着", alive is not None)
    except Exception as e:  # noqa: BLE001
        rd.check("控制台还活着", False, repr(e))

    if expect == "done":
        # the prompt fell back to the template, and the look survived it
        rd.check("流水线没有被一次报错打断", job.get("status") == "done",
                 f"status={job.get('status')} {str(job.get('error'))[:120]}")
        store = ProjectStore.open(tmp_root / slug)
        project = store.load()
        prefix = looks.style(style_id)["prompt"]
        shots = [sh for ep in project.episodes for sc in ep.scenes
                 for sh in sc.shots]
        rd.check("报错的镜头用兜底的提示词", bool(shots), "没有镜头")
        no_style = [sh for sh in shots if prefix not in (sh.prompt or "")]
        rd.check("兜底的提示词也带着画风", not no_style,
                 f"{len(no_style)} 个镜头没有画风")
    else:
        # the card failed: the run says so, and the console still works
        results = (job.get("result") or {}).get("results") or {}
        failed = _counts(results.get("visual"))
        rd.check("出图失败被记下来了", int(failed.get("failed") or 0) > 0,
                 str(results.get("visual"))[:120])
        rd.check("流水线没有假装成功", job.get("status") != "done"
                 or int(failed.get("failed") or 0) > 0,
                 f"status={job.get('status')}")
        store = ProjectStore.open(tmp_root / slug)
        project = store.load()
        shots = [sh for ep in project.episodes for sc in ep.scenes
                 for sh in sc.shots]
        rd.check("画不出来的镜头被记下来了",
                 any(sh.status.value != "done"
                     or not (sh.image_path or "").strip() for sh in shots),
                 ", ".join(f"{sh.id}={sh.status.value}"
                           f"/img={bool(sh.image_path)}" for sh in shots))
        try:
            again = console.post("/api/upload", {"name": rd.name + " 之后",
                                                 "file": "x.txt",
                                                 "text": "第一章 测试\n一行字。\n"})
            rd.check("控制台还能接新的活", again.get("ok"), str(again)[:120])
        except Exception as e:  # noqa: BLE001
            rd.check("控制台还能接新的活", False, repr(e))
    return rd


def _fault_stop(console: Console, rd: Round, script: Path, style_id: str,
                tmp_root: Path) -> Round:
    size = _size("9:16", "720x1280")
    up = console.post("/api/upload", {"name": rd.name, "file": script.name,
                                      "text": script.read_text(encoding="utf-8",
                                                              errors="replace")})
    slug = up["slug"]
    console.post("/api/project/look", {
        "project": slug, "aspect_ratio": "9:16", "width": size["w"],
        "height": size["h"], "style": style_id})
    started = console.post("/api/run", {"project": slug, "chapters": [1],
                                         "stages": ORDER})

    def make_context(cfg, store, providers=None):
        return Context(cfg, store, console.providers)

    # let it get going, then stop it
    with patch("dramakit.ai.actions.make_context", make_context), \
            patch("dramakit.pipeline.lipsync._musetalk", wraps=_fake_lipsync):
        time.sleep(1.5)
        stopped = console.post("/api/jobs/stop", {"id": started["job"]})
        rd.check("POST /api/jobs/stop", stopped.get("ok"), str(stopped)[:120])
        job = console.wait_job(started["job"], timeout=300)
    rd.check("被叫停的运行没有说成功",
             job.get("status") in ("stopped", "interrupted", "failed", "error"),
             f"status={job.get('status')}")
    store = ProjectStore.open(tmp_root / slug)
    project = store.load()
    statuses = {k: v.value for k, v in (project.stage_status or {}).items()}
    rd.check("停下来的那一段记的是 interrupted",
             "interrupted" in statuses.values()
             or job.get("status") == "interrupted",
             ", ".join(f"{k}={v}" for k, v in statuses.items()))
    rd.check("没跑到的阶段没有被记成完成",
             not all(statuses.get(s) == "done" for s in ORDER),
             ", ".join(f"{k}={v}" for k, v in statuses.items()))
    try:
        alive = console.get("/api/state")
        rd.check("控制台还活着", alive is not None)
    except Exception as e:  # noqa: BLE001
        rd.check("控制台还活着", False, repr(e))
    # and the console can start another run afterwards
    try:
        again = console.post("/api/run", {"project": slug, "chapters": [1],
                                          "stages": ["ingest"]})
        rd.check("停掉之后还能再开一个任务", again.get("ok"), str(again)[:120])
    except Exception as e:  # noqa: BLE001
        rd.check("停掉之后还能再开一个任务", False, repr(e))
    return rd


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def build_config() -> Config:
    cfg = Config()
    cfg.pipeline.fail_fast = True
    cfg.pipeline.stages_enabled = list(ORDER)
    cfg.ai.auto_tag = False
    cfg.segment.strategy = "by_chapter"
    cfg.storyboard.shot_duration_range = [1.0, 2.0]
    cfg.comfyui.mode = "image_then_video"
    cfg.comfyui.video_references = False
    cfg.comfyui.concurrency = 1
    cfg.comfyui.video_concurrency = 1
    cfg.compose.fps = 8
    cfg.compose.preset = "ultrafast"
    cfg.compose.grade_shots = False
    cfg.compose.lipsync = True
    cfg.compose.h3_audio = "discard"
    cfg.compose.burn_subtitles = False
    cfg.compose.generate_cover = False
    cfg.compose.ai_declaration = ""
    cfg.compose.voice_room = 0.0
    cfg.tts.concurrency = 1
    cfg.llm.concurrency = 1
    return cfg


def main() -> int:
    # the console on this machine is GBK; the report is Chinese
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--faults", action="store_true", default=True)
    ap.add_argument("--no-faults", dest="faults", action="store_false")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not ff.check_available():
        print("需要 ffmpeg/ffprobe")
        return 2

    styles = [s["id"] for s in looks.looks()["styles"]]
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    fakes = Fakes()
    console = Console(build_config(), root, fakes)
    rounds: list[Round] = []
    t0 = time.time()
    try:
        scripts = sorted(SCRIPTS.glob("round*.txt"))
        for i in range(args.rounds):
            script = scripts[i % len(scripts)]
            aspect_id, size_id = FRAMES[i % len(FRAMES)]
            style_id = styles[i % len(styles)]
            skills = SKILL_SETS[i % len(SKILL_SETS)]
            rd = run_round(console, i + 1, script, aspect_id, size_id,
                           style_id, skills, root, h3=(i % 3 == 2))
            rounds.append(rd)
            print(rd.report(args.verbose), flush=True)
        rd = run_node_pool(console, 90)
        rounds.append(rd)
        print(rd.report(args.verbose), flush=True)
        if args.faults:
            for rd in run_faults(console, root):
                rounds.append(rd)
                print(rd.report(args.verbose), flush=True)
    finally:
        console.close()
        tmp.cleanup()

    total = sum(len(r.checks) for r in rounds)
    bad = sum(1 for r in rounds for _, ok, _ in r.checks if not ok)
    print("\n" + "=" * 68)
    print(f"{len(rounds)} 轮，{total} 项检查，{bad} 项不通过，"
          f"{time.time() - t0:.0f} 秒")
    for rd in rounds:
        for f in rd.failures():
            print(f"  ✗ 第{rd.number}轮 {rd.name} —— {f}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
