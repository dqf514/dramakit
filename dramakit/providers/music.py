"""Background-music providers.

  library  - pick a track from a local folder by mood tag, loop/trim/fade with ffmpeg
  musicgen - generate with Meta MusicGen (local HTTP server or transformers)
  suno     - generate via a Suno-compatible API
  none     - no BGM

Mood tags come from scene.bgm_mood / scene.mood (e.g. 紧张, 悲伤, 欢快, 恢弘).
"""
from __future__ import annotations

import logging
import random
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import httpx

from ..config import MusicConfig
from .base import BaseMusic

log = logging.getLogger("dramakit.music")

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}

# Chinese mood tag -> English MusicGen prompt
MOOD_PROMPT = {
    "紧张": "tense cinematic suspense strings, fast pulse, thriller",
    "悬疑": "mysterious dark ambient, sparse piano, investigation thriller",
    "悲伤": "sad emotional piano and strings, slow, melancholic",
    "欢快": "upbeat cheerful pop, light percussion, happy",
    "温馨": "warm gentle acoustic, soft piano, heartwarming",
    "恢弘": "epic orchestral, powerful brass and choir, heroic trailer",
    "激昂": "energetic epic rock orchestra, driving drums, uplifting",
    "恐怖": "horror drone, dissonant strings, eerie atmosphere",
    "浪漫": "romantic soft piano and violin, tender love theme",
    "愤怒": "aggressive percussion, dark intense orchestral, anger",
    "平静": "calm minimal ambient, soft pads, neutral",
    "搞笑": "playful comedic pizzicato, quirky light music",
    "中性": "neutral cinematic underscore, subtle ambient",
}


def _ffmpeg() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def _normalize_mood(mood: str) -> str:
    mood = (mood or "").strip()
    if mood in MOOD_PROMPT:
        return mood
    for k in MOOD_PROMPT:
        if k in mood or mood in k:
            return k
    return "中性"


# --------------------------------------------------------------------------- #
class MusicLibrary(BaseMusic):
    """Pick from a local folder. Matching priority:
       1) config.mood_map[mood] explicit filenames
       2) files whose name contains the mood tag or an english keyword
       3) any file (random)
    """

    def __init__(self, cfg: MusicConfig, root: Optional[Path] = None):
        self.cfg = cfg
        self.root = Path(root) if root else Path(".")
        self.lib_dir = (self.root / cfg.library_dir) if not Path(cfg.library_dir).is_absolute() \
            else Path(cfg.library_dir)

    def _all_tracks(self) -> list[Path]:
        if not self.lib_dir.exists():
            return []
        return [p for p in self.lib_dir.rglob("*") if p.suffix.lower() in AUDIO_EXT]

    def _pick(self, mood: str) -> Optional[Path]:
        tracks = self._all_tracks()
        if not tracks:
            return None
        m = _normalize_mood(mood)
        # explicit map
        mapped = self.cfg.mood_map.get(m) or self.cfg.mood_map.get(mood) or []
        for name in mapped:
            cand = self.lib_dir / name
            if cand.exists():
                return cand
        # filename keyword match (chinese tag or english prompt words)
        kw = [m] + MOOD_PROMPT.get(m, "").split()[:3]
        hits = [p for p in tracks
                if any(k.lower() in p.stem.lower() for k in kw if k)]
        if hits:
            return random.choice(hits)
        return random.choice(tracks)

    def get_track(self, mood: str, duration: float, out_path: str) -> Optional[str]:
        src = self._pick(mood)
        if not src:
            log.warning("音乐库为空（%s），跳过 BGM。放入音频文件或在 config 配置 mood_map。",
                        self.lib_dir)
            return None
        return _fit_audio(src, out_path, duration, self.cfg)


# --------------------------------------------------------------------------- #
class MusicGenHTTP(BaseMusic):
    """Talks to a MusicGen HTTP server: POST /generate {prompt, duration}."""

    def __init__(self, cfg: MusicConfig):
        self.cfg = cfg
        self.base = cfg.base_url.rstrip("/")

    def get_track(self, mood: str, duration: float, out_path: str) -> Optional[str]:
        prompt = MOOD_PROMPT.get(_normalize_mood(mood), MOOD_PROMPT["中性"])
        dur = min(max(duration, 5.0), self.cfg.duration or duration)
        with httpx.Client(timeout=600, trust_env=self.cfg.use_proxy) as c:
            r = c.post(f"{self.base}/generate",
                       json={"prompt": prompt, "duration": dur, "model": self.cfg.model})
        if r.status_code >= 400:
            log.error("MusicGen HTTP %s: %s", r.status_code, r.text[:200])
            return None
        ctype = r.headers.get("content-type", "")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        if "json" in ctype:
            data = r.json()
            url = data.get("audio_url") or data.get("url")
            if url:
                with httpx.Client(timeout=300, trust_env=self.cfg.use_proxy) as c2:
                    Path(out_path).write_bytes(c2.get(url).content)
            else:
                return None
        else:
            Path(out_path).write_bytes(r.content)
        return _fit_audio(Path(out_path), out_path, duration, self.cfg)


class MusicGenLocal(BaseMusic):
    """Local transformers MusicGen (needs torch; generates on GPU/CPU)."""

    def __init__(self, cfg: MusicConfig):
        self.cfg = cfg
        self._pipe = None

    def _load(self):
        if self._pipe is None:
            from transformers import AutoProcessor, MusicgenForConditionalGeneration
            import torch
            model = MusicgenForConditionalGeneration.from_pretrained(self.cfg.model)
            proc = AutoProcessor.from_pretrained(self.cfg.model)
            dev = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(dev)
            self._pipe = (model, proc, dev, torch)
        return self._pipe

    def get_track(self, mood: str, duration: float, out_path: str) -> Optional[str]:
        try:
            model, proc, dev, torch = self._load()
        except Exception as e:  # noqa: BLE001
            log.error("MusicGen 本地加载失败（需 pip install dramakit[musicgen]）：%s", e)
            return None
        prompt = MOOD_PROMPT.get(_normalize_mood(mood), MOOD_PROMPT["中性"])
        dur = min(max(duration, 5.0), 30.0)
        inputs = proc(text=[prompt], padding=True, return_tensors="pt").to(dev)
        audio = model.generate(**inputs, do_sample=True,
                               max_new_tokens=int(dur * 50))
        import soundfile as sf
        data = audio[0, 0].cpu().numpy()
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        wav = str(Path(out_path).with_suffix(".wav"))
        sf.write(wav, data, model.config.audio_encoder.sampling_rate)
        return _fit_audio(Path(wav), out_path, duration, self.cfg)


# --------------------------------------------------------------------------- #
class SunoAPI(BaseMusic):
    """Suno-compatible generate endpoint (many proxy servers share this shape)."""

    def __init__(self, cfg: MusicConfig):
        self.cfg = cfg
        self.base = cfg.base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            self.headers["Authorization"] = f"Bearer {cfg.api_key}"

    def get_track(self, mood: str, duration: float, out_path: str) -> Optional[str]:
        style = MOOD_PROMPT.get(_normalize_mood(mood), MOOD_PROMPT["中性"])
        with httpx.Client(timeout=600, trust_env=self.cfg.use_proxy) as c:
            r = c.post(f"{self.base}/api/generate",
                       headers=self.headers,
                       json={"prompt": style, "make_instrumental": True, "wait_audio": True})
        if r.status_code >= 400:
            log.error("Suno HTTP %s: %s", r.status_code, r.text[:200])
            return None
        data = r.json()
        clips = data if isinstance(data, list) else data.get("clips", [])
        if not clips or not clips[0].get("audio_url"):
            return None
        with httpx.Client(timeout=300, trust_env=self.cfg.use_proxy) as c:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_bytes(c.get(clips[0]["audio_url"]).content)
        return _fit_audio(Path(out_path), out_path, duration, self.cfg)


class NoMusic(BaseMusic):
    def get_track(self, mood: str, duration: float, out_path: str) -> Optional[str]:
        return None


# --------------------------------------------------------------------------- #
def _fit_audio(src: Path, out_path: str, duration: float, cfg: MusicConfig) -> str:
    """Loop-or-trim `src` to exactly `duration` seconds with fade in/out."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    duration = max(duration, 1.0)
    fi, fo = cfg.fade_in, min(cfg.fade_out, duration / 2)
    af = []
    if cfg.loop_to_fit:
        af.append(f"aloop=loop=-1:size=2e9")
    af.append(f"atrim=0:{duration:.3f}")
    af.append(f"afade=t=in:st=0:d={fi:.2f}")
    af.append(f"afade=t=out:st={max(duration - fo, 0):.2f}:d={fo:.2f}")
    cmd = [_ffmpeg(), "-y", "-stream_loop", "-1", "-i", str(src),
           "-af", ",".join(af), "-t", f"{duration:.3f}",
           "-c:a", "libmp3lame", "-q:a", "4", out_path]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        # fallback: simple copy-trim
        subprocess.run([_ffmpeg(), "-y", "-i", str(src), "-t", f"{duration:.3f}",
                        out_path], capture_output=True)
    return out_path


def build_music(cfg: MusicConfig, root: Optional[Path] = None) -> BaseMusic:
    if cfg.provider == "library":
        return MusicLibrary(cfg, root)
    if cfg.provider == "musicgen":
        # if base_url set -> HTTP server, else local transformers
        if cfg.base_url and "localhost:8001" not in cfg.base_url:
            return MusicGenHTTP(cfg)
        if cfg.base_url:
            return MusicGenHTTP(cfg)
        return MusicGenLocal(cfg)
    if cfg.provider == "suno":
        return SunoAPI(cfg)
    return NoMusic()
