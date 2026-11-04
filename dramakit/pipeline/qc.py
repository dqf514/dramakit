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
from ..models import Episode, Status, is_narration
from .base import Context

_I_RE = re.compile(r"I:\s*(-?[\d.]+)\s*LUFS")
_LRA_RE = re.compile(r"LRA:\s*(-?[\d.]+)\s*LU")
_PEAK_RE = re.compile(r"Peak:\s*(-?[\d.]+)\s*dBFS")
_BLACK_RE = re.compile(r"black_start:([\d.]+)\s+black_end:([\d.]+)")


def _measure_loudness(path: str | Path) -> dict:
    """Integrated loudness / LRA / true peak via EBU R128.

    ebur128 prints a running value on every frame; only the block after
    "Summary:" holds the final measurement.
    """
    r = ff._run([ff.ffmpeg_bin(), "-i", str(path), "-af",
                 "ebur128=peak=true", "-f", "null", "-"], quiet=True)
    text = (r.stderr or "") + (r.stdout or "")
    idx = text.rfind("Summary:")
    if idx >= 0:
        text = text[idx:]
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


def _camera_on(shot, ep) -> str:
    """Who the camera is on in this shot.

    The shot's own text is not enough: the model writes a subject in its
    own words ("合同与父亲医药费缴费单"), and two of those are not two
    shots of the same face.  The face is the person whose lines the shot
    carries, or whoever is left in the frame.
    """
    from .storyboard import camera_on
    for sc in ep.scenes:
        if shot in sc.shots:
            spoken = [l for l in sc.lines if not is_narration(l)]
            return camera_on(shot, spoken)
    return shot.characters[0] if shot.characters else ""


def _coverage_metrics(ep: Episode) -> tuple[dict, list[str]]:
    """How varied the coverage of an episode is.

    The failure this catches is the one that looks fine on paper: every
    line of dialogue gets its own close-up of the person saying it, and
    the whole episode is one camera on one tripod.  The numbers are cheap
    to take and they say what a viewer would say - that it never cuts.
    """
    shots = [sh for sc in ep.scenes for sh in sc.shots]
    if not shots:
        return {}, []
    out: dict = {"shots": len(shots)}
    talking = [sh for sh in shots if sh.line_indices]
    out["talking_shots"] = len(talking)
    # a face square to the lens, saying the line: an interview, not a scene
    head_on = [sh for sh in talking if sh.angle == "正面"]
    out["head_on_shots"] = len(head_on)
    if talking:
        out["head_on_share"] = round(len(head_on) / len(talking), 3)
    # how many different pictures there are
    frames = {(sh.shot_type.value, sh.angle, _camera_on(sh, ep)) for sh in shots}
    out["distinct_frames"] = len(frames)
    out["distinct_share"] = round(len(frames) / len(shots), 3)
    # the longest run of the same face in a row
    run = best = 1
    for a, b in zip(shots, shots[1:]):
        run = run + 1 if _camera_on(a, ep) and _camera_on(a, ep) == _camera_on(b, ep) else 1
        best = max(best, run)
    out["longest_same_subject_run"] = best
    # the shots that carry no line: reactions, inserts, the establishing
    # shot - the ones that make a scene a scene
    out["silent_shots"] = len(shots) - len(talking)
    out["over_shoulder_shots"] = sum(1 for sh in shots
                                      if sh.shot_type.value == "过肩")
    out["insert_shots"] = sum(1 for sh in shots
                              if sh.shot_type.value in ("空镜", "特写"))
    warnings: list[str] = []
    if talking and len(head_on) / len(talking) > 0.3:
        warnings.append(f"正对镜头的台词镜头 {len(head_on)}/{len(talking)}"
                        f"（{len(head_on) / len(talking) * 100:.0f}%）："
                        "整场像访谈，不像戏")
    if out["distinct_share"] < 0.6:
        warnings.append(f"镜头重复率高：{len(shots)} 镜只有 {len(frames)} 种"
                        f"景别/角度/主体组合")
    if best >= 3:
        warnings.append(f"连续 {best} 镜拍同一个人，缺正反打与反应镜头")
    if talking and out["silent_shots"] == 0:
        warnings.append("没有一镜不带台词：整集只有说话的脸，没有画面")
    return out, warnings


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
    if "loudness_range_lu" in loud and loud["loudness_range_lu"] > 16.0:
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

    # how the scene was covered
    coverage, cover_warnings = _coverage_metrics(ep)
    metrics["coverage"] = coverage
    warnings.extend(cover_warnings)

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
        # compose already recorded the mix measurements (music stem, bed
        # segments) - keep them alongside the delivery checks
        previous = ep.qc_report or {}
        ep.qc_report = {**{k: v for k, v in previous.items() if k == "mix"},
                        **report}
        out = qc_dir / f"ep_{ep.index:03d}.json"
        out.write_text(json.dumps(ep.qc_report, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        mix = (ep.qc_report.get("mix") or {})
        if mix.get("music_lufs") is None:
            ctx.log.warning("qc: 第%d集 没有音乐轨", ep.index)
        elif mix.get("music_lufs", -99) < -60:
            ctx.log.error("qc: 第%d集 音乐轨静音（%.1f LUFS）",
                          ep.index, mix["music_lufs"])
            ep.qc_report["ok"] = False
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
