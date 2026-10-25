"""Stage 13 — qc: delivery quality control on the finished episode.

Composing an episode is not the same as shipping it. This stage measures the
rendered file against the delivery spec and writes a report, so a broken master
is caught by the pipeline instead of by whoever opens it first.

Measured:
  * container/stream facts  - resolution, fps, pixel format, duration, streams
  * loudness               - integrated LUFS, loudness range, true peak (EBU R128)
  * audio/video sync       - the two track lengths must agree
  * black frames           - dead frames are a rendering bug, not a mood
  * sidecars               - subtitle file present when subtitles are expected

Errors fail the episode. Warnings are recorded but do not block.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from ..media import ffmpeg as ff
from ..models import Episode, Status
from .base import Context

_I_RE = re.compile(r"I:\s*(-?[\d.]+)\s*LUFS")
_LRA_RE = re.compile(r"LRA:\s*(-?[\d.]+)\s*LU")
_PEAK_RE = re.compile(r"Peak:\s*(-?[\d.]+)\s*dBFS")
_BLACK_RE = re.compile(r"black_start:([\d.]+)\s+black_end:([\d.]+)")


def _measure_loudness(path: str | Path) -> dict:
    """Integrated loudness / LRA / true peak via EBU R128."""
    r = ff._run([ff.ffmpeg_bin(), "-i", str(path), "-af",
                 "ebur128=peak=true", "-f", "null", "-"], quiet=True)
    text = (r.stderr or "") + (r.stdout or "")
    out: dict = {}
    m = _I_RE.search(text)
    if m:
        out["integrated_lufs"] = float(m.group(1))
    m = _LRA_RE.search(text)
    if m:
        out["loudness_range_lu"] = float(m.group(1))
    m = _PEAK_RE.search(text)
    if m:
        out["true_peak_dbfs"] = float(m.group(1))
    return out


def _detect_black(path: str | Path, min_dur: float = 0.5) -> list[dict]:
    r = ff._run([ff.ffmpeg_bin(), "-i", str(path), "-vf",
                 f"blackdetect=d={min_dur}:pix_th=0.10", "-an", "-f", "null", "-"],
                quiet=True)
    text = (r.stderr or "") + (r.stdout or "")
    return [{"start": float(a), "end": float(b)}
            for a, b in _BLACK_RE.findall(text)]


def _frac(value: str) -> float:
    try:
        num, _, den = value.partition("/")
        return float(num) / float(den) if den else float(num)
    except Exception:  # noqa: BLE001
        return 0.0


def check_episode(ctx: Context, ep: Episode) -> dict:
    """Measure one finished episode. Returns the report dict."""
    cc = ctx.cfg.compose
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict = {}

    video = ctx.store.abs(ep.video_path) if ep.video_path else None
    if not video or not video.exists():
        return {"ok": False, "errors": [f"成片不存在: {ep.video_path}"],
                "warnings": [], "metrics": {}}

    streams = ff.probe_streams(video)
    vs = streams.get("video")
    aus = streams.get("audio")
    if not vs:
        errors.append("成片没有视频流")
    if not aus:
        errors.append("成片没有音频流")

    vdur = _frac(vs.get("duration", "0")) if vs else 0.0
    adur = _frac(aus.get("duration", "0")) if aus else 0.0
    total = ff.probe_duration(video) or max(vdur, adur)
    metrics["duration"] = round(total, 3)
    metrics["video_duration"] = round(vdur, 3)
    metrics["audio_duration"] = round(adur, 3)

    if vs:
        w = int(vs.get("width", 0) or 0)
        h = int(vs.get("height", 0) or 0)
        fps = _frac(vs.get("avg_frame_rate", "0")) or _frac(vs.get("r_frame_rate", "0"))
        metrics["width"], metrics["height"] = w, h
        metrics["fps"] = round(fps, 3)
        metrics["pix_fmt"] = vs.get("pix_fmt", "")
        metrics["video_codec"] = vs.get("codec_name", "")
        if (w, h) != (cc.width, cc.height):
            errors.append(f"分辨率不符: {w}x{h}（期望 {cc.width}x{cc.height}）")
        if fps and abs(fps - cc.fps) > 0.5:
            errors.append(f"帧率不符: {fps}（期望 {cc.fps}）")
        if total <= 0:
            errors.append("成片时长为 0")
    if aus:
        metrics["audio_codec"] = aus.get("codec_name", "")
        metrics["sample_rate"] = aus.get("sample_rate", "")
        metrics["channels"] = aus.get("channels", 0)

    # A/V sync: the two tracks must end together
    if vdur > 0 and adur > 0:
        drift = abs(vdur - adur)
        metrics["av_drift"] = round(drift, 3)
        if drift > 0.5:
            errors.append(f"音画不同步: 视频 {vdur:.2f}s / 音频 {adur:.2f}s（差 {drift:.2f}s）")
        elif drift > 0.15:
            warnings.append(f"音画轻微偏移 {drift:.2f}s")

    # loudness against the delivery spec
    loud = _measure_loudness(video)
    metrics.update(loud)
    target = cc.target_loudness_lufs
    if "integrated_lufs" in loud:
        dev = abs(loud["integrated_lufs"] - target)
        if dev > 3.0:
            warnings.append(f"整体响度 {loud['integrated_lufs']} LUFS 偏离目标 {target} LUFS "
                            f"（差 {dev:.1f}）")
    if "true_peak_dbfs" in loud and loud["true_peak_dbfs"] > -1.0:
        warnings.append(f"真峰 {loud['true_peak_dbfs']} dBFS 超过 -1 dBTP，可能削波")
    if "loudness_range_lu" in loud and loud["loudness_range_lu"] > 12.0:
        warnings.append(f"响度动态范围 {loud['loudness_range_lu']} LU 偏大，听感忽大忽小")

    # dead frames
    blacks = _detect_black(video)
    metrics["black_segments"] = len(blacks)
    if blacks:
        worst = max(b["end"] - b["start"] for b in blacks)
        if worst > 1.0:
            errors.append(f"检测到 {len(blacks)} 段黑帧（最长 {worst:.1f}s）")
        else:
            warnings.append(f"检测到 {len(blacks)} 段短黑帧")

    # sidecars
    if cc.burn_subtitles or cc.also_write_srt:
        srt = ctx.store.subtitle_path(ep, "srt")
        ass = ctx.store.subtitle_path(ep, "ass")
        if not srt.exists() and not ass.exists():
            warnings.append("字幕文件缺失（成片可能没有字幕）")
        else:
            metrics["subtitles"] = ("srt" if srt.exists() else "ass")

    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "metrics": metrics}


def run(ctx: Context) -> dict:
    """Run QC over every finished episode in the project."""
    total_errors = 0
    total_warnings = 0
    failed = 0
    qc_dir = ctx.store.root / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)

    for ep in ctx.target_episodes():
        if not ep.video_path:
            continue
        report = check_episode(ctx, ep)
        ep.qc_report = report
        out = qc_dir / f"ep_{ep.index:03d}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        if report["ok"]:
            ctx.mark(ep, "qc", Status.DONE)
            m = report["metrics"]
            ctx.log.info("qc: 第%d集 通过 %s | %.1fs %dx%d @%.0ffps | %.1f LUFS",
                         ep.index,
                         m.get("video_codec", "?"), m.get("duration", 0),
                         m.get("width", 0), m.get("height", 0), m.get("fps", 0),
                         m.get("integrated_lufs", 0))
        else:
            failed += 1
            ctx.mark(ep, "qc", Status.FAILED)
            ctx.log.error("qc: 第%d集 未通过（%d 项）", ep.index, len(report["errors"]))
            for e in report["errors"][:6]:
                ctx.log.error("    ✗ %s", e)
        for w in report["warnings"][:6]:
            ctx.log.warning("qc: 第%d集 ! %s", ep.index, w)
        total_errors += len(report["errors"])
        total_warnings += len(report["warnings"])

    ctx.save()
    ctx.log.info("qc: %d 集未通过 / %d 项错误 / %d 项警告",
                 failed, total_errors, total_warnings)
    return {"failed": failed, "errors": total_errors, "warnings": total_warnings}
