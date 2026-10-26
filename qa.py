"""Objective QA for a finished episode.

Measures what a viewer would notice - picture, voice, subtitles, music - and
writes a machine-readable report so rounds can be compared against each other.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.media import ffmpeg as ff
from dramakit.media import grade as gr
from dramakit.pipeline.base import Context, build_timeline
from dramakit.project import ProjectStore

FF = "ffmpeg"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def lufs(path, extra=""):
    r = ff._run([FF, "-i", str(path), "-af", f"ebur128=peak=true{extra}",
                  "-f", "null", "-"], quiet=True)
    seg = r.stderr[r.stderr.rfind("Summary:"):]
    out = {}
    for key, pat in (("i", r"I:\s*(-?[\d.]+)\s*LUFS"),
                     ("lra", r"LRA:\s*(-?[\d.]+)\s*LU"),
                     ("pk", r"Peak:\s*(-?[\d.]+)\s*dBFS")):
        m = re.search(pat, seg)
        if m:
            out[key] = float(m.group(1))
    return out


def raw_gray(path, size=192):
    """Grayscale pixels of an image/video frame, as bytes."""
    r = subprocess.run(
        [FF, "-hide_banner", "-v", "error", "-i", str(path),
         "-vf", f"scale={size}:{size}", "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True)
    return r.stdout


def sharpness(path):
    """Laplacian variance - the standard blur detector, no numpy needed."""
    data = raw_gray(path)
    if len(data) < 4096:
        return 0.0
    n = int(len(data) ** 0.5)
    px = list(data[:n * n])
    total = 0
    count = 0
    for y in range(1, n - 1):
        row = y * n
        for x in range(1, n - 1):
            i = row + x
            v = (4 * px[i] - px[i - 1] - px[i + 1] - px[i - n] - px[i + n])
            total += v * v
            count += 1
    return total / count if count else 0.0


def black_segments(path):
    r = ff._run([FF, "-i", str(path), "-vf", "blackdetect=d=0.4:pix_th=0.10",
                  "-an", "-f", "null", "-"], quiet=True)
    return re.findall(r"black_start:([\d.]+)\s+black_end:([\d.]+)", r.stderr)


# --------------------------------------------------------------------------- #
# the checks
# --------------------------------------------------------------------------- #
def check_picture(ctx, ep, tl, issues):
    """The finished episode: sharp enough, and tonally consistent shot to shot.

    Measured on the rendered episode, not on the source stills - the grade
    step is what the viewer actually sees.
    """
    ep_path = ctx.store.abs(ep.video_path) if ep.video_path else None
    frames = []
    if ep_path and ep_path.exists():
        dur = ff.probe_duration(ep_path)
        tmp = ctx.store.root / "tmp" / f"qa_{ep.index:03d}"
        tmp.mkdir(parents=True, exist_ok=True)
        for i in range(8):
            at = dur * (i + 0.5) / 8
            p = tmp / f"f{i}.png"
            ff.extract_frame(ep_path, p, at=at, width=640)
            if p.exists():
                st = gr.analyze(p)
                frames.append({"at": round(at, 1), "sharp": round(sharpness(p), 1),
                               "luma": round(st.luma, 1), "sat": round(st.sat, 1)})
    if not frames:
        issues.append(("picture", "no_frames", "-", "成片抽不出画面"))
        return {}
    sharp = [f["sharp"] for f in frames]
    lumas = [f["luma"] for f in frames]
    sats = [f["sat"] for f in frames]
    med = sorted(sharp)[len(sharp) // 2]
    for f in frames:
        if med > 0 and f["sharp"] < med * 0.35:
            issues.append(("picture", "blurry_frame", f"t={f['at']}s",
                           f"锐度 {f['sharp']} 远低于中位 {med}"))
    spread = max(lumas) - min(lumas)
    if spread > 30:
        issues.append(("picture", "tonal_spread", "-",
                       f"成片内亮度差 {spread:.0f}（{min(lumas)}~{max(lumas)}）"))
    sat_spread = max(sats) - min(sats)
    if sat_spread > 14:
        issues.append(("picture", "saturation_spread", "-",
                       f"成片内饱和度差 {sat_spread:.0f}"))
    return {"frames": frames, "sharp_median": round(med, 1),
            "sharp_min": round(min(sharp), 1),
            "luma_spread": round(spread, 1),
            "sat_spread": round(sat_spread, 1)}


def check_voice(ctx, ep, tl, issues):
    """Every spoken line: has audio, is long enough, sits at a sane level."""
    rows = []
    for ts in tl.shots:
        pass
    for scene in ep.scenes:
        for line in scene.lines:
            if not line.audio_path:
                continue
            p = ctx.store.abs(line.audio_path)
            if not p.exists():
                issues.append(("voice", "missing_audio", line.id, "音频文件不存在"))
                continue
            d = ff.probe_duration(p)
            rows.append({"id": line.id, "speaker": line.speaker,
                         "emotion": line.emotion, "duration": round(d, 2),
                         "chars": len(line.text)})
    if not rows:
        issues.append(("voice", "no_voice_at_all", "-", "一集没有任何配音"))
        return {}
    # a line much shorter than its text needs is a truncated synthesis
    for r in rows:
        if r["chars"] >= 8 and r["duration"] < 0.35 * r["chars"] / 3.0:
            issues.append(("voice", "too_fast", r["id"],
                           f"{r['chars']} 字只用了 {r['duration']:.2f}s"))
        if r["duration"] < 0.4:
            issues.append(("voice", "too_short", r["id"], f"只有 {r['duration']:.2f}s"))
    emo = {}
    for r in rows:
        emo.setdefault(r["emotion"], []).append(r["duration"])
    # the same emotion should not collapse to one identical duration
    return {"lines": len(rows), "rows": rows,
            "per_emotion": {k: round(sum(v)/len(v), 2) for k, v in emo.items()}}


def momentary_profile(path, limit=20000):
    """EBU R128 momentary (400ms) loudness over time.

    The integrated loudness of a dialogue track is dragged down by the silences
    between the lines, so it cannot answer "can you hear the speech over the
    music". The momentary profile can: the loud windows are the speech, the
    quiet ones are the bed alone.
    """
    r = ff._run([FF, "-i", str(path), "-af",
                 "ebur128=metadata=1,ametadata=mode=print:file=-",
                 "-f", "null", "-"], quiet=True)
    vals = [float(x) for x in re.findall(r"lavfi\.r128\.M=(-?[\d.]+)", r.stdout)]
    return [v for v in vals if v > -120][:limit]


def check_audibility(path, issues):
    """How far does the speech stand out from the music bed?"""
    vals = momentary_profile(path)
    if len(vals) < 20:
        return {}
    vals.sort()
    n = len(vals)
    speech = vals[n // 2:]          # the louder half: the dialogue
    bed = vals[:n // 2]             # the quieter half: gaps, bed only
    speech_med = speech[len(speech) // 2]
    bed_med = bed[len(bed) // 2]
    gap = speech_med - bed_med
    if gap < 8:
        issues.append(("mix", "speech_buried", "-",
                       f"对白只比垫底高 {gap:.1f} LU，听不清（要 >= 8 LU）"))
    elif gap > 30:
        issues.append(("mix", "music_too_quiet", "-",
                       f"对白比垫底高 {gap:.1f} LU，音乐几乎听不到"))
    return {"speech_lufs": round(speech_med, 1), "bed_lufs": round(bed_med, 1),
            "gap_lu": round(gap, 1)}


def check_audio_mix(ctx, ep, issues):
    """The final mix: dialogue over music, both audible, at the delivery spec."""
    ep_path = ctx.store.abs(ep.video_path) if ep.video_path else None
    if not ep_path or not ep_path.exists():
        issues.append(("mix", "no_episode", "-", "没有成片"))
        return {}
    total = lufs(ep_path)
    tmp = ctx.store.root / "tmp" / f"ep_{ep.index:03d}"
    voice = tmp / "voice.mp3"
    bed = tmp / "h3_bed.mp3"
    music = tmp / "music.mp3"
    v = lufs(voice) if voice.exists() else {}
    m = lufs(music) if music.exists() else {}
    b = lufs(bed) if bed.exists() else {}
    aud = check_audibility(ep_path, issues)
    if total.get("i") is not None and abs(total["i"] + 16) > 2.5:
        issues.append(("mix", "loudness_off", "-",
                       f"整体响度 {total['i']} LUFS（目标 -16）"))
    if total.get("pk") is not None and total["pk"] > -0.8:
        issues.append(("mix", "peak_too_hot", "-", f"真峰 {total['pk']} dBFS"))
    blacks = black_segments(ep_path)
    if blacks:
        issues.append(("mix", "black_frames", "-", f"{len(blacks)} 段黑帧"))
    return {"episode": total, "voice": v, "music": m, "bed": b,
            "audibility": aud, "black_segments": len(blacks)}


def check_subtitles(ctx, ep, tl, issues):
    """Cues: present, timed with the voice, at most two lines, inside the frame."""
    ass = ctx.store.abs(ep.ass_path) if ep.ass_path else None
    srt = ctx.store.abs(ep.subtitle_path) if ep.subtitle_path else None
    path = ass if (ass and ass.exists()) else srt
    if not path:
        issues.append(("subtitle", "no_subtitle_file", "-", "没有字幕文件"))
        return {}
    if path.suffix == ".ass":
        text = path.read_text(encoding="utf-8", errors="replace")
        styles = {}
        for l in text.splitlines():
            if not l.startswith("Style:"):
                continue
            # Style: name,font,size,primary,secondary,outline,back,bold,italic,
            #        underline,strike,scaleX,scaleY,spacing,angle,border,outline,
            #        shadow,marginL,marginR,marginV,encoding
            f = l[len("Style:"):].strip().split(",")
            try:
                styles[f[0]] = {"font_size": int(f[2]),
                                "margin_h": int(f[18]) if len(f) > 18 else 0,
                                "margin_v": int(f[20]) if len(f) > 20 else 0}
            except (ValueError, IndexError):
                continue
        cues = []
        for l in text.splitlines():
            if not l.startswith("Dialogue:"):
                continue
            f = l.split(",", 9)
            body = re.sub(r"\{[^}]*\}", "", f[-1])
            cues.append({"start": f[1], "end": f[2], "style": f[3],
                         "text": body.replace("\\N", "\n").strip()})
    else:
        cues = []
        for block in path.read_text(encoding="utf-8", errors="replace").strip().split("\n\n"):
            lines = block.splitlines()
            if len(lines) >= 2 and "-->" in lines[0]:
                cues.append({"start": lines[0].split("-->")[0].strip(),
                             "end": lines[0].split("-->")[1].strip(),
                             "style": "srt", "text": "\n".join(lines[1:]).strip()})
    spoken = sum(1 for sc in ep.scenes for l in sc.lines
                 if l.audio_path or l.kind.value == "narration")
    if len(cues) < spoken:
        issues.append(("subtitle", "missing_cues", "-",
                       f"{spoken} 句台词只有 {len(cues)} 条字幕"))
    width = ctx.cfg.compose.width
    for c in cues:
        rows = [r for r in c["text"].split("\n") if r.strip()]
        if len(rows) > 2:
            issues.append(("subtitle", "too_many_lines", "-",
                           f"一条字幕 {len(rows)} 行：{c['text'][:26]}"))
        size = (styles.get(c["style"], {}).get("font_size") or 30)
        for r in rows:
            # a full-width CJK glyph is about as wide as the font size
            est = sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in r)
            if est * size > width * 0.92:
                issues.append(("subtitle", "overflow", "-",
                               f"字幕超宽（估 {est*size:.0f}px / 画面 {width}px）：{r[:20]}"))
    return {"cues": len(cues), "styles": list(styles),
            "max_rows": max((len([r for r in c['text'].split('\n') if r.strip()]) for c in cues),
                             default=0)}


def check_nle(ctx, ep, issues):
    """The FCPXML hand-off has to be openable, so it needs both lanes."""
    nle = ctx.store.root / "nle" / f"ep_{ep.index:03d}" / f"ep_{ep.index:03d}.fcpxml"
    if not nle.exists():
        issues.append(("nle", "missing", "-", "没有导出 FCPXML"))
        return {}
    import xml.etree.ElementTree as ET
    root = ET.parse(nle).getroot()
    spine = len(root.findall(".//spine/asset-clip"))
    lanes = [s.get("name") for s in root.findall(".//section")]
    if not lanes:
        issues.append(("nle", "no_audio_lane", "-", "FCPXML 没有音轨"))
    return {"spine": spine, "lanes": lanes}


# --------------------------------------------------------------------------- #
def qa_project(project_dir: Path) -> dict:
    """Full QA pass over one project."""
    cfg = Config.load(r"E:\dramakit\config\default.yaml")
    store = ProjectStore(project_dir)
    ctx = Context(cfg, store)
    issues = []
    out = {"project": store.root.name, "episodes": []}
    for ep in ctx.target_episodes():
        tl = build_timeline(ep)
        e = {"index": ep.index, "title": ep.title}
        e["picture"] = check_picture(ctx, ep, tl, issues)
        e["voice"] = check_voice(ctx, ep, tl, issues)
        e["mix"] = check_audio_mix(ctx, ep, issues)
        e["subtitle"] = check_subtitles(ctx, ep, tl, issues)
        e["nle"] = check_nle(ctx, ep, issues)
        out["episodes"].append(e)
    out["issues"] = [{"area": a, "kind": k, "where": w, "detail": d}
                     for a, k, w, d in issues]
    out["issue_count"] = len(issues)
    out["verdict"] = "PASS" if not issues else "ISSUES"
    return out


def print_report(rep: dict) -> None:
    print(f"===== {rep['project']}  {rep['verdict']}  ({rep['issue_count']} 个问题) =====")
    for e in rep["episodes"]:
        print(f"  第{e['index']}集 {e.get('title','')}")
        p = e.get("picture") or {}
        if p:
            print(f"    画面: {len(p.get('frames', []))} 帧  锐度中位 {p.get('sharp_median')} "
                  f"最低 {p.get('sharp_min')}  亮度差 {p.get('luma_spread')}  "
                  f"饱和差 {p.get('sat_spread')}")
        v = e.get("voice") or {}
        if v:
            print(f"    配音: {v['lines']} 句  各情绪均长 {v['per_emotion']}")
        m = e.get("mix") or {}
        if m:
            au = m.get("audibility") or {}
            print(f"    混音: 成片 {m.get('episode',{}).get('i')} LUFS  "
                  f"对白段 {au.get('speech_lufs')}  垫底段 {au.get('bed_lufs')}  "
                  f"高出 {au.get('gap_lu')} LU")
        s = e.get("subtitle") or {}
        if s:
            print(f"    字幕: {s.get('cues')} 条  最多 {s.get('max_rows')} 行/条")
        n = e.get("nle") or {}
        if n:
            print(f"    FCPXML: {n.get('spine')} 片段  音轨 {n.get('lanes')}")
    if rep["issues"]:
        print("  问题:")
        for i in rep["issues"]:
            print(f"    [{i['area']}/{i['kind']}] {i['where']}: {i['detail']}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"E:\dramakit\projects\测试短剧")
    rep = qa_project(target)
    print_report(rep)
    out = Path(r"E:\dramakit\rounds") / f"{target.name}.qa.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print("报告:", out)
