"""AI one-click configuration.

Goal: the user never hand-edits YAML. `dj setup` (or the web console's setup
panel) does three things:

  1. probe()      — discover what's actually reachable: ffmpeg, local LLM
                    endpoints (Ollama / LM Studio) and their model lists, the
                    remote ComfyUI (GPU, checkpoints, node types), edge voices,
                    the local music library. Pure I/O, no LLM.
  2. generate()   — hand the probe results + the user's one-line intent + the
                    selected template presets/chips to the main LLM and ask it
                    to return a complete config as JSON (only the fields it
                    wants to set; everything else keeps its default).
  3. apply()      — merge that JSON over the defaults, validate through the
                    pydantic Config model (so bad LLM output can't corrupt the
                    file), and write config/default.yaml.

If no LLM is reachable, generate() falls back to a deterministic mapping from
the chosen templates + probe, so one-click setup still produces a valid config.
"""
from __future__ import annotations

import json
import logging
import re
import socket
import time
from pathlib import Path
from typing import Optional

import httpx
import yaml

from ..config import Config
from ..media import ffmpeg as ff
from .brain import Brain
from .templates import apply_chip_ids, preset_by_id

log = logging.getLogger("dramakit.ai.autoconfig")

# candidate local LLM endpoints to probe
_LLM_ENDPOINTS = [
    ("ollama", "http://localhost:11434"),
    ("lmstudio", "http://localhost:1234"),
]


def _http_get(url: str, timeout: float = 4.0) -> Optional[dict]:
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as c:
            r = c.get(url)
            if r.status_code == 200:
                return r.json()
    except Exception:  # noqa: BLE001
        return None
    return None


def _port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _split_url(base: str) -> tuple[str, int]:
    from urllib.parse import urlparse
    u = urlparse(base if "://" in base else "http://" + base)
    return u.hostname or "127.0.0.1", (u.port or 80)


# --------------------------------------------------------------------------- #
# 1. probe
# --------------------------------------------------------------------------- #
def probe(cfg: Optional[Config] = None) -> dict:
    """Discover the reachable environment. Never raises."""
    cfg = cfg or Config()
    report: dict = {"ffmpeg": ff.check_available(), "llm_endpoints": [],
                    "comfyui": {}, "tts": {}, "music": {}}

    # --- local LLM endpoints + their models ---
    for name, base in _LLM_ENDPOINTS:
        if not _port_open(*_split_url(base)):
            continue
        models = []
        if name == "ollama":
            data = _http_get(f"{base}/api/tags")
            models = [m.get("name") for m in (data or {}).get("models", [])]
        else:  # lmstudio / openai-compat
            data = _http_get(f"{base}/v1/models")
            models = [m.get("id") for m in (data or {}).get("data", [])]
        report["llm_endpoints"].append(
            {"name": name, "base_url": base, "models": [m for m in models if m]})

    # --- configured LLM reachability ---
    brain = Brain(cfg)
    report["llm_main"] = brain.probe()["main"]

    # --- ComfyUI (may be remote) ---
    try:
        from ..providers.comfyui import ComfyUIClient
        c = ComfyUIClient(cfg.comfyui, Path("."))
        if c.ping():
            st = c.system_stats()
            sysinfo = st.get("system", {})
            devices = sysinfo.get("devices", [])
            gpus = [{"name": d.get("name"),
                     "vram_gb": round(d.get("vram_total", 0) / (1024**3), 1)}
                    for d in devices]
            t2i_rep = c.validate_workflow(cfg.comfyui.t2i_workflow, cfg.comfyui.t2i_nodes)
            i2v_rep = c.validate_workflow(cfg.comfyui.i2v_workflow, cfg.comfyui.i2v_nodes)
            flf_rep = (c.validate_workflow(cfg.comfyui.flf_workflow, cfg.comfyui.i2v_nodes)
                       if cfg.comfyui.flf_workflow else None)
            report["comfyui"] = {
                "reachable": True, "base_url": cfg.comfyui.base_url,
                "version": sysinfo.get("comfyui_version", ""),
                "gpus": gpus,
                "checkpoints": c.list_checkpoints()[:40],
                "t2i_ok": t2i_rep.get("ok", False),
                "i2v_ok": i2v_rep.get("ok", False),
                "flf_ok": (flf_rep or {}).get("ok"),
                "t2i_report": t2i_rep,
                "i2v_report": i2v_rep,
                "flf_report": flf_rep,
            }
        else:
            report["comfyui"] = {"reachable": False, "base_url": cfg.comfyui.base_url}
    except Exception as e:  # noqa: BLE001
        report["comfyui"] = {"reachable": False, "error": str(e)[:120]}

    # --- TTS ---
    try:
        from ..providers.tts import build_tts
        tts = build_tts(cfg.tts)
        voices = tts.list_voices()
        report["tts"] = {"provider": cfg.tts.provider,
                         "zh_voices": voices[:40], "voice_count": len(voices)}
    except Exception as e:  # noqa: BLE001
        report["tts"] = {"provider": cfg.tts.provider, "error": str(e)[:120]}

    # --- music library ---
    try:
        lib = Path(cfg.music.library_dir)
        files = [p.name for p in lib.rglob("*") if p.suffix.lower() in
                 (".mp3", ".wav", ".m4a", ".ogg", ".flac")] if lib.exists() else []
        report["music"] = {"provider": cfg.music.provider,
                           "library_dir": str(lib), "tracks": files[:40],
                           "track_count": len(files)}
    except Exception as e:  # noqa: BLE001
        report["music"] = {"error": str(e)[:120]}

    return report


# --------------------------------------------------------------------------- #
# 2. generate
# --------------------------------------------------------------------------- #
_SETUP_SYS = """你是短剧自动化工厂的配置引擎。根据【环境探测结果】和【用户意图】，
产出一份完整的运行配置。只输出 JSON，不要解释。只写你想要设置的字段，其余用默认值。
可用的顶层字段与含义：
{
  "llm": {"base_url","model","api_key","temperature","use_proxy"},
  "ai": {"light_base_url","light_model","language","auto_tag"},
  "tts": {"provider","edge_default_voice","edge_narrator_voice","edge_female_voice","rate","base_url","model"},
  "comfyui": {"enabled","base_url","checkpoint","width","height","steps","cfg","sampler","scheduler","frames","fps","mode","auth"},
  "music": {"provider","bgm_volume","duck_voice","base_url","model"},
  "segment": {"strategy","episode_duration","min_episode_duration","max_episode_duration"},
  "storyboard": {"shots_per_scene"},
  "compose": {"width","height","fps","transition","motion_effect","burn_subtitles"},
  "art_direction": {"genre","style","era","color_palette","aspect_ratio"},
  "pipeline": {"stages_enabled"}
}
硬性规则：
1) llm.model / comfyui.checkpoint 必须从探测到的真实列表里选，选不到的就用探测里第一个可用项；若某能力探测不可达，就把它设成不依赖它的方案（如 comfyui 不可达则 enabled=false，music 无乐库则 provider=none）。
2) 竖屏短剧默认 compose.width=1080,height=1920；若用户要横屏则改。
3) 优先本地/免费方案，除非用户明确要云端。
4) 若探测到本地有 >=2 个模型，用较大的做 llm.model，较小的做 ai.light_model（打标签用）。
5) 数值字段必须是数字，布尔必须是 true/false。"""


def generate(cfg: Config, intent: str, *, genre_preset: str = "",
             chips: Optional[list[str]] = None, extra: str = "",
             probe_report: Optional[dict] = None) -> dict:
    """Return a config-overrides dict (JSON) for the given intent + templates."""
    report = probe_report if probe_report is not None else probe(cfg)
    preset = preset_by_id(genre_preset) if genre_preset else None
    chip_over = apply_chip_ids(chips or [])

    constraints = {
        "intent": intent or "",
        "extra_requirements": extra or "",
        "genre_preset": preset or {},
        "chip_overrides": chip_over,
    }
    brain = Brain(cfg)
    user = ("【环境探测结果】\n" + json.dumps(report, ensure_ascii=False)[:6000] +
            "\n\n【用户约束】\n" + json.dumps(constraints, ensure_ascii=False))
    out = brain.json(_SETUP_SYS, user, role="config", temperature=0.2, max_tokens=2000)
    if isinstance(out, dict) and out:
        return out
    # deterministic fallback (no LLM): map templates + probe straight to config
    return _fallback_config(cfg, report, preset, chip_over, intent)


def _fallback_config(cfg: Config, report: dict, preset: Optional[dict],
                     chip_over: dict, intent: str) -> dict:
    """Build a sane config without an LLM, from templates + what's reachable."""
    out: dict = {"art_direction": {}, "compose": {}, "segment": {}}
    # LLM: pick first reachable local endpoint
    eps = report.get("llm_endpoints") or []
    if eps:
        ep = eps[0]
        out["llm"] = {"base_url": (ep["base_url"] + "/v1") if ep["name"] == "lmstudio"
                      else ep["base_url"] + "/v1", "use_proxy": False}
        models = ep.get("models") or []
        if models:
            out["llm"]["model"] = models[0]
            if len(models) > 1:
                out["ai"] = {"light_base_url": out["llm"]["base_url"],
                             "light_model": models[-1], "language": "zh"}
    # ComfyUI: only enable if reachable
    comfy = report.get("comfyui", {})
    out["comfyui"] = {"enabled": bool(comfy.get("reachable"))}
    if comfy.get("checkpoints"):
        out["comfyui"]["checkpoint"] = comfy["checkpoints"][0]
    # Music: library only if tracks exist
    music = report.get("music", {})
    out["music"] = {"provider": "library" if music.get("track_count") else "none"}
    # art direction / pacing from preset + chips
    if preset:
        out["art_direction"] = dict(preset.get("art", {}))
        out["segment"]["episode_duration"] = preset.get("episode_duration", 90)
    for dotted, val in chip_over.items():
        _set_dotted(out, dotted, val)
    out.setdefault("compose", {}).update({"width": 1080, "height": 1920})
    return out


# top-level Config sections the fallback may write; semantic hints like
# "pacing"/"audience" are for the LLM only and are skipped here.
_CONFIG_SECTIONS = {"llm", "ai", "web", "tts", "comfyui", "music", "segment",
                    "storyboard", "compose", "pipeline", "art_direction"}


def _set_dotted(d: dict, dotted: str, value) -> None:
    """Write value into nested dict by 'a.b' path. 'art.*' -> 'art_direction.*'.

    Only recognized config sections are written; bare semantic-hint keys
    (pacing/audience/...) are ignored so the fallback never emits stray fields.
    """
    if dotted.startswith("art."):
        dotted = "art_direction." + dotted[len("art."):]
    parts = dotted.split(".")
    if parts[0] not in _CONFIG_SECTIONS:
        return
    cur = d
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


# --------------------------------------------------------------------------- #
# 3. apply
# --------------------------------------------------------------------------- #
def apply_overrides(base: Config, overrides: dict) -> Config:
    """Deep-merge an overrides dict over `base`, re-validating through pydantic.

    Only recognized top-level Config sections are merged; stray keys (template
    hints like `pacing`, or anything the LLM hallucinated) are dropped. Wrong-
    typed values fall back to the default rather than raising, so bad output can
    never corrupt the config file. `art_direction` is not a Config section (it
    lives on each project), so it is stashed on the returned cfg for `dj new`.
    """
    data = json.loads(base.model_dump_json())
    overrides = dict(overrides or {})
    art = overrides.pop("art_direction", None)
    known = {k for k in overrides if k in data}
    _deep_merge(data, {k: overrides[k] for k in known})
    cfg = Config.model_validate(_drop_nulls(data))
    if art:
        # remember intended art direction so `dj new` can seed the project
        cfg.pipeline.__dict__["_art_defaults"] = art  # noqa: SLF001
    return cfg


def _deep_merge(dst: dict, src: dict) -> None:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v


def _drop_nulls(obj):
    if isinstance(obj, dict):
        return {k: _drop_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_drop_nulls(v) for v in obj]
    return obj


def setup(cfg: Config, intent: str, *, genre_preset: str = "",
          chips: Optional[list[str]] = None, extra: str = "",
          out_path: str | Path = "config/default.yaml",
          probe_report: Optional[dict] = None) -> dict:
    """Full one-click flow: probe -> generate -> apply -> write YAML.

    Returns {"config": <merged dict>, "probe": <report>, "written": <path>,
             "art_defaults": <dict>, "used_llm": bool}.
    """
    report = probe_report if probe_report is not None else probe(cfg)
    overrides = generate(cfg, intent, genre_preset=genre_preset, chips=chips,
                         extra=extra, probe_report=report)
    used_llm = bool(Brain(cfg).probe()["main"]["ok"])
    art = overrides.get("art_direction") if isinstance(overrides, dict) else None
    merged = apply_overrides(cfg, dict(overrides))
    out_path = Path(out_path)
    # dump_yaml rewrites the whole file and cannot preserve comments, so keep a
    # .bak of the current (hand-commented) config before overwriting it.
    if out_path.exists():
        try:
            out_path.with_suffix(out_path.suffix + ".bak").write_bytes(out_path.read_bytes())
        except OSError:
            pass
    merged.dump_yaml(out_path)
    return {
        "config": json.loads(merged.model_dump_json()),
        "probe": report, "written": str(out_path),
        "art_defaults": art or {}, "used_llm": used_llm,
        "overrides": overrides,
    }


# --------------------------------------------------------------------------- #
# 4. LLM 连接测试（设置页用）
# --------------------------------------------------------------------------- #
def _norm_base(base_url: str) -> str:
    """Normalise an OpenAI-compatible base url to end with /v1 (no trailing /)."""
    b = (base_url or "").strip().rstrip("/")
    if not b:
        return ""
    if not b.startswith("http"):
        b = "http://" + b
    if "/v1" not in b:
        b += "/v1"
    return b


def list_models(base_url: str, api_key: str = "", use_proxy: bool = False,
                timeout: float = 6.0) -> list[str]:
    """GET /v1/models and return model ids. Never raises (empty on failure)."""
    b = _norm_base(base_url)
    if not b:
        return []
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        with httpx.Client(timeout=timeout, trust_env=use_proxy) as c:
            r = c.get(f"{b}/models", headers=headers)
            if r.status_code != 200:
                return []
            data = r.json()
    except Exception:  # noqa: BLE001
        return []
    ids = []
    for m in (data.get("data") or []):
        mid = m.get("id") if isinstance(m, dict) else None
        if mid:
            ids.append(str(mid))
    return ids


def test_llm_endpoint(base_url: str, api_key: str = "", model: str = "",
                      use_proxy: bool = False, timeout: float = 8.0) -> dict:
    """Validate an OpenAI-compatible endpoint: list models + a tiny completion.

    Returns {ok, reachable, models, model_ok, latency_ms, message, error}.
    `ok` is True only when a real chat completion succeeded. Never raises.
    """
    out = {"ok": False, "reachable": False, "models": [], "model_ok": False,
           "latency_ms": None, "message": "", "error": ""}
    b = _norm_base(base_url)
    if not b:
        out["error"] = "base_url 为空"
        return out
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    models = list_models(b, api_key, use_proxy, timeout=min(timeout, 6.0))
    out["models"] = models[:60]
    test_model = (model or "").strip() or (models[0] if models else "")
    if not test_model:
        out["error"] = "连不上或没有模型：确认地址/端口，本地服务是否已启动"
        return out

    payload = {"model": test_model,
               "messages": [{"role": "user", "content": "ping"}],
               "max_tokens": 5, "temperature": 0, "stream": False}
    t0 = time.time()
    try:
        with httpx.Client(timeout=timeout, trust_env=use_proxy) as c:
            r = c.post(f"{b}/chat/completions", json=payload, headers=headers)
        dt = int((time.time() - t0) * 1000)
        out["latency_ms"] = dt
        out["reachable"] = True
        if r.status_code == 200:
            out["ok"] = True
            out["model_ok"] = True
            out["message"] = f"连接成功，模型 {test_model} 可用（{dt}ms）"
        elif r.status_code in (401, 403):
            out["error"] = f"鉴权失败(HTTP {r.status_code})：API Key 不对或无权限"
        elif r.status_code == 404:
            out["error"] = f"模型不存在(HTTP 404)：{test_model}"
        else:
            out["error"] = f"HTTP {r.status_code}: {r.text[:160]}"
    except httpx.TimeoutException:
        out["error"] = f"超时（>{timeout:.0f}s）：地址不通或模型加载慢"
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)[:200]
    return out


# --------------------------------------------------------------------------- #
# 5. 定点写回 YAML（保留注释）——设置页保存用
# --------------------------------------------------------------------------- #
def _is_num(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _fmt_scalar(v) -> str:
    """Render a Python scalar as a YAML value, quoting only when necessary."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return '""'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    s = str(v)
    if s == "":
        return '""'
    quote = (s[0] in "!&*?|>%@`'\"#[],{}"
             or s.strip() != s or s.startswith("- ")
             or ": " in s or "#" in s
             or s.lower() in {"true", "false", "null", "yes", "no", "on", "off", "~"}
             or _is_num(s))
    if quote:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _trailing_comment(rest: str) -> str:
    """From the text after `key:`, return its trailing `# comment` (single
    leading space) so edits preserve the file's inline documentation."""
    m = re.search(r"\s#", rest)
    if m:
        return " " + rest[m.start():].lstrip()
    stripped = rest.lstrip()
    return " " + stripped if stripped.startswith("#") else ""


def _yaml_set_scalar(text: str, section: str, key: str, value) -> str:
    """Set `key: value` under a top-level `section:` in YAML text, in place,
    preserving indentation and the trailing comment. Inserts after the section
    header if the key is absent. Only touches the first (top-level) match."""
    lines = text.split("\n")
    sec_re = re.compile(rf"^{re.escape(section)}\s*:(\s#.*)?$")
    top_re = re.compile(r"^[A-Za-z_][\w\-]*\s*:")
    start = next((i for i, ln in enumerate(lines) if sec_re.match(ln)), None)
    if start is None:
        return text
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if top_re.match(lines[j]):
            end = j
            break
    key_re = re.compile(rf"^(\s+){re.escape(key)}\s*:(.*)$")
    for j in range(start + 1, end):
        m = key_re.match(lines[j])
        if m:
            indent, rest = m.group(1), m.group(2)
            lines[j] = f"{indent}{key}: {_fmt_scalar(value)}{_trailing_comment(rest)}"
            return "\n".join(lines)
    lines.insert(start + 1, f"  {key}: {_fmt_scalar(value)}")
    return "\n".join(lines)


def _yaml_set_block(text: str, section: str, value) -> str:
    """Replace a whole top-level section (for nested/list data like
    models.entries) with a YAML dump. The section header line and every other
    section are preserved verbatim, including their comments."""
    dumped = yaml.safe_dump({section: value}, allow_unicode=True,
                            sort_keys=False).rstrip("\n").split("\n")
    lines = text.split("\n")
    sec_re = re.compile(rf"^{re.escape(section)}\s*:(\s#.*)?$")
    top_re = re.compile(r"^[A-Za-z_][\w\-]*\s*:")
    start = next((i for i, ln in enumerate(lines) if sec_re.match(ln)), None)

    if start is None:
        # place the new block right after llm: (readability), else at the end
        anchor = next((i for i, ln in enumerate(lines)
                       if re.match(r"^llm\s*:", ln)), None)
        if anchor is None:
            if lines and lines[-1] != "":
                lines.append("")
            lines += dumped
            return "\n".join(lines)
        end = len(lines)
        for j in range(anchor + 1, len(lines)):
            if top_re.match(lines[j]):
                end = j
                break
        # keep a following section's banner comments attached to that section:
        # insert before the banner (and the blank line above it).
        at = end
        while at > anchor + 1 and lines[at - 1].startswith("#"):
            at -= 1
        if at > anchor + 1 and lines[at - 1].strip() == "":
            at -= 1
        block = [""] + dumped
        if at < len(lines) and lines[at].strip() != "":
            block.append("")
        lines[at:at] = block
        return "\n".join(lines)

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if top_re.match(lines[j]):
            end = j
            break
    # keep the next section's banner comments (and the blank lines around
    # them); only the managed section body is replaced.
    stop = end
    while stop > start + 1 and lines[stop - 1].strip() == "":
        stop -= 1
    while stop > start + 1 and lines[stop - 1].startswith("#"):
        stop -= 1
    if stop > start + 1 and lines[stop - 1].strip() == "":
        stop -= 1
    replacement = [lines[start]] + dumped[1:]
    if stop < len(lines) and lines[stop].strip() != "":
        replacement.append("")
    lines[start:stop] = replacement
    return "\n".join(lines)


def save_settings(cfg_path: str | Path, updates: dict, blocks: dict | None = None) -> dict:
    """Surgically write {section: {key: value}} scalars and/or whole-section
    `blocks` (nested data such as models.entries) into the YAML config,
    preserving comments and every other key. Validates by reloading and
    restores the backup if the result won't parse. Returns the reloaded config.
    """
    path = Path(cfg_path)
    updates = {s: dict(f) for s, f in (updates or {}).items() if f}
    blocks = {s: v for s, v in (blocks or {}).items() if v is not None}
    if not updates and not blocks:
        return json.loads(Config.load(path).model_dump_json())

    if path.exists() and path.read_text(encoding="utf-8").strip():
        backup = text = path.read_text(encoding="utf-8")
        for section, fields in updates.items():
            for key, val in fields.items():
                text = _yaml_set_scalar(text, section, key, val)
        for section, value in blocks.items():
            text = _yaml_set_block(text, section, value)
        path.write_text(text, encoding="utf-8")
        try:
            cfg = Config.load(path)
        except Exception:
            path.write_text(backup, encoding="utf-8")
            raise
        return json.loads(cfg.model_dump_json())

    data = dict(updates)
    data.update(blocks)
    cfg = apply_overrides(Config.load(path), data)
    cfg.dump_yaml(path)
    return json.loads(cfg.model_dump_json())
