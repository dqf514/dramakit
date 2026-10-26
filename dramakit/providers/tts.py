"""Text-to-speech providers.

  edge      - free Microsoft Edge neural voices (async, no key). Best default.
  cosyvoice - local CosyVoice HTTP server (OpenAI-ish /tts or native endpoint)
  openai    - any OpenAI-compatible POST /v1/audio/speech
  minimax   - MiniMax T2A v2 (cloud, emotional multi-voice)
  custom    - generic: POST base_url with {text, voice} -> audio bytes

Voice resolution order:
  config.voice_map[speaker]  ->  gender fallback  ->  narrator/default voice
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

import httpx

from ..config import TTSConfig
from .base import BaseTTS

log = logging.getLogger("dramakit.tts")


def probe_duration(path: str | Path) -> float:
    """Audio duration in seconds via mutagen (falls back to 0)."""
    try:
        from mutagen import File as MFile
        f = MFile(str(path))
        if f is not None and getattr(f, "info", None) and f.info.length:
            return round(float(f.info.length), 3)
    except Exception as e:  # noqa: BLE001
        log.debug("mutagen probe failed: %s", e)
    return 0.0


# --------------------------------------------------------------------------- #
# Edge TTS (free)
# --------------------------------------------------------------------------- #
class EdgeTTS(BaseTTS):
    def __init__(self, cfg: TTSConfig):
        self.cfg = cfg

    def synthesize(self, text: str, voice: str, out_path: str, *, rate: str = "+0%",
                   volume: str = "+0%", pitch: str = "+0Hz", speed: float = 1.0,
                   emotion: str = "") -> float:
        text = (text or "").strip()
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        if not text:
            # write a tiny silent file so the timeline still advances predictably
            _write_silence(out_path, 0.3)
            return 0.3

        async def _run() -> None:
            import edge_tts
            communicate = edge_tts.Communicate(
                text, voice or self.cfg.edge_default_voice,
                rate=rate or self.cfg.rate,
                volume=volume or self.cfg.volume,
                pitch=pitch or self.cfg.pitch,
            )
            await communicate.save(out_path)

        asyncio.run(_run())
        dur = probe_duration(out_path)
        if self.cfg.silence_pad_ms > 0 and dur:
            _pad_silence(out_path, self.cfg.silence_pad_ms / 1000.0)
            dur = probe_duration(out_path) or dur
        return dur

    def list_voices(self) -> list[str]:
        async def _run():
            import edge_tts
            return [v["ShortName"] for v in await edge_tts.list_voices()
                    if v["Locale"].startswith("zh")]
        # the voice list is fetched from the network and can come back empty on a
        # transient failure; retry a couple of times before giving up
        for attempt in range(3):
            try:
                voices = asyncio.run(_run())
                if voices:
                    return voices
            except Exception:  # noqa: BLE001
                pass
            if attempt < 2:
                time.sleep(1.0 + attempt)
        return []


# --------------------------------------------------------------------------- #
# OpenAI-compatible / CosyVoice / custom HTTP
def _decode_audio(payload: str) -> bytes:
    """Decode the audio a TTS server returned.

    MiniMax hands back hex, most others base64. Hex is tried first when the
    string looks like hex and decodes cleanly.
    """
    import base64
    text = payload.strip()
    if len(text) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in text):
        try:
            return bytes.fromhex(text)
        except ValueError:
            pass
    return base64.b64decode(text)


# --------------------------------------------------------------------------- #
class HTTPTTS(BaseTTS):
    """Covers cosyvoice, openai, minimax and custom via a normalized request."""

    def __init__(self, cfg: TTSConfig, provider: str):
        self.cfg = cfg
        self.provider = provider
        self.base_url = cfg.base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            self.headers["Authorization"] = f"Bearer {cfg.api_key}"

    def _endpoint(self) -> str:
        if self.provider == "minimax":
            return f"{self.base_url}/v1/t2a_v2"
        if self.base_url.endswith("/v1") or "/v1" in self.base_url:
            return f"{self.base_url}/audio/speech"
        return f"{self.base_url}/tts"

    def _payload(self, text: str, voice: str, speed: float, emotion: str) -> dict:
        if self.provider == "minimax":
            vs = {"voice_id": voice, "speed": speed, "vol": 1.0, "pitch": 0}
            if emotion:
                # MiniMax takes the emotion as a token, not as part of the text
                vs["emotion"] = emotion
            return {
                "model": self.cfg.model or "speech-2.8-hd",
                "text": text,
                "stream": False,
                "language_boost": "Chinese",
                "voice_setting": vs,
                "audio_setting": {"sample_rate": 32000, "bitrate": 128000,
                                  "format": "mp3", "channel": 1},
            }
        if self.provider == "openai":
            return {"model": self.cfg.model or "tts-1", "input": text,
                    "voice": voice, "speed": speed, "response_format": "mp3"}
        # cosyvoice / custom (common local-server shape)
        return {"text": text, "voice": voice, "speaker": voice,
                "speed": speed, "format": "mp3", "emotion": emotion}

    def list_voices(self) -> list[str]:
        """The voice catalogue this provider can actually use."""
        if self.provider != "minimax":
            return []
        try:
            with httpx.Client(timeout=60.0, trust_env=self.cfg.use_proxy) as client:
                r = client.post(f"{self.base_url}/v1/get_voice",
                                json={"voice_type": "all"}, headers=self.headers)
            r.raise_for_status()
            data = r.json()
        except Exception as e:  # noqa: BLE001
            log.warning("minimax 音色表读取失败: %s", str(e)[:120])
            return []
        out = []
        for v in data.get("system_voice") or []:
            vid = str(v.get("voice_id") or "").strip()
            if not vid:
                continue
            if "Chinese" in vid or vid.startswith(("male-", "female-")) or \
                    vid.startswith(("presenter_", "audiobook_")):
                out.append(vid)
        return out

    def synthesize(self, text: str, voice: str, out_path: str, *, rate: str = "+0%",
                   volume: str = "+0%", pitch: str = "+0Hz", speed: float = 1.0,
                   emotion: str = "") -> float:
        text = (text or "").strip()
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        if not text:
            _write_silence(out_path, 0.3)
            return 0.3
        payload = self._payload(text, voice, speed or self.cfg.speed, emotion)
        with httpx.Client(timeout=120.0, trust_env=self.cfg.use_proxy) as client:
            r = client.post(self._endpoint(), json=payload, headers=self.headers)
        if r.status_code >= 400:
            raise RuntimeError(f"TTS HTTP {r.status_code}: {r.text[:300]}")
        ctype = r.headers.get("content-type", "")
        if "json" in ctype:
            data = r.json()
            # some servers return base64 audio inside JSON
            audio_b64 = (data.get("data", {}).get("audio")
                         if isinstance(data.get("data"), dict) else data.get("audio"))
            if audio_b64:
                Path(out_path).write_bytes(_decode_audio(audio_b64))
            elif data.get("audio_url"):
                with httpx.Client(timeout=120.0, trust_env=self.cfg.use_proxy) as c2:
                    Path(out_path).write_bytes(c2.get(data["audio_url"]).content)
            else:
                raise RuntimeError(f"Unexpected TTS JSON: {str(data)[:200]}")
        else:
            Path(out_path).write_bytes(r.content)
        dur = probe_duration(out_path)
        if self.cfg.silence_pad_ms > 0 and dur:
            _pad_silence(out_path, self.cfg.silence_pad_ms / 1000.0)
            dur = probe_duration(out_path) or dur
        return dur


def build_tts(cfg: TTSConfig) -> BaseTTS:
    if cfg.provider == "edge":
        return EdgeTTS(cfg)
    return HTTPTTS(cfg, cfg.provider)


# --------------------------------------------------------------------------- #
# voice resolution + ffmpeg silence helpers
# --------------------------------------------------------------------------- #
def resolve_voice(cfg: TTSConfig, speaker: str, gender: str = "未知",
                  is_narrator: bool = False) -> str:
    if speaker and speaker in cfg.voice_map:
        return cfg.voice_map[speaker]
    if cfg.provider == "edge":
        if is_narrator or speaker in ("旁白", "解说"):
            return cfg.edge_narrator_voice
        if gender in ("女", "female"):
            return cfg.edge_female_voice
        return cfg.edge_default_voice
    if is_narrator or speaker in ("旁白", "解说"):
        narrator = cfg.narrator_voice
        if narrator:
            return narrator
    return cfg.voice_map.get(speaker, cfg.model or "default")


def _ffmpeg() -> str:
    import shutil
    return shutil.which("ffmpeg") or "ffmpeg"


def _write_silence(out_path: str, seconds: float) -> None:
    import subprocess
    subprocess.run([
        _ffmpeg(), "-y", "-f", "lavfi", "-i",
        f"anullsrc=r=24000:cl=mono", "-t", f"{seconds:.3f}", out_path,
    ], check=False, capture_output=True)


def _pad_silence(out_path: str, seconds: float) -> None:
    """Append trailing silence to a clip (in place)."""
    import subprocess
    p = Path(out_path)
    tmp = p.with_suffix(".pad.mp3")
    r = subprocess.run([
        _ffmpeg(), "-y", "-i", str(p), "-af",
        f"apad=pad_dur={seconds:.3f}", "-c:a", "libmp3lame", str(tmp),
    ], capture_output=True)
    if r.returncode == 0 and tmp.exists():
        tmp.replace(p)
