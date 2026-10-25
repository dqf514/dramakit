"""Acceptance check for a finished episode: everything a viewer would notice.

Reports the delivery spec, the loudness, the picture, the subtitles and the
NLE hand-off, and pulls a few frames so the result can be eyeballed.
"""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

PROJECT = Path(r"E:\dramakit\projects\测试短剧")
SHOTS = Path(r"C:\Users\David\AppData\Local\Temp\opencode\accept")


def probe(p: Path) -> dict:
    st = ff.probe_streams(p)
    v = st.get("video") or {}
    a = st.get("audio") or {}
    dur = ff.probe_duration(p)
    return {"v": v, "a": a, "dur": dur}


def loudness(p: Path) -> dict:
    r = ff._run([ff.ffmpeg_bin(), "-i", str(p), "-af", "ebur128=peak=true",
                 "-f", "null", "-"], quiet=True)
    seg = r.stderr[r.stderr.rfind("Summary:"):]
    import re
    out = {}
    for key, pat in (("integrated_lufs", r"I:\s*(-?[\d.]+)\s*LUFS"),
                     ("lra_lu", r"LRA:\s*(-?[\d.]+)\s*LU"),
                     ("true_peak_dbfs", r"Peak:\s*(-?[\d.]+)\s*dBFS")):
        m = re.search(pat, seg)
        if m:
            out[key] = float(m.group(1))
    return out


def _rate(value) -> float:
    """'30/1' -> 30.0"""
    try:
        if isinstance(value, str) and "/" in value:
            num, _, den = value.partition("/")
            return float(num) / float(den or 1)
        return float(value)
    except Exception:  # noqa: BLE001
        return 0.0


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    ok = True
    for ep in sorted((PROJECT / "episodes").glob("ep_*.mp4")):
        print("=" * 62)
        print(ep.name)
        pr = probe(ep)
        v, a, dur = pr["v"], pr["a"], pr["dur"]
        w, h = v.get("width"), v.get("height")
        print(f"  画面  {w}x{h}  {v.get('avg_frame_rate')}  {v.get('pix_fmt')}  "
              f"{v.get('codec_name')}  {dur:.1f}s")
        print(f"  声音  {a.get('codec_name')}  {a.get('sample_rate')}Hz  "
              f"{a.get('channels')}ch  时长 {a.get('duration')}s")
        ld = loudness(ep)
        print(f"  响度  {ld.get('integrated_lufs')} LUFS  动态 {ld.get('lra_lu')} LU  "
              f"峰值 {ld.get('true_peak_dbfs')} dBFS")
        checks = [
            ("分辨率 1280x720", (w, h) == (1280, 720)),
            ("帧率 30", abs(_rate(v.get("avg_frame_rate")) - 30) < 0.5),
            ("像素格式 yuv420p", v.get("pix_fmt") == "yuv420p"),
            ("有音轨", bool(a.get("codec_name"))),
            ("音画时长差 < 0.2s",
             abs(float(a.get("duration", 0)) - dur) < 0.2),
            ("响度在 -16±2 LUFS",
             abs(ld.get("integrated_lufs", -99) - (-16)) <= 2),
            ("真峰 <= -1 dBTP", ld.get("true_peak_dbfs", 0) <= -1.0),
        ]
        for name, good in checks:
            print(f"  {'OK ' if good else 'BAD'} {name}")
            ok = ok and good

        # 字幕
        stem = ep.stem
        srt = PROJECT / "subs" / f"{stem}.srt"
        ass = PROJECT / "subs" / f"{stem}.ass"
        print(f"  {'OK ' if (srt.exists() or ass.exists()) else 'BAD'} 字幕文件 "
              f"{'srt' if srt.exists() else ('ass' if ass.exists() else '无')}")

        # FCPXML
        nle = PROJECT / "nle" / stem / f"{stem}.fcpxml"
        if nle.exists():
            root = ET.parse(nle).getroot()
            spine = len(root.findall(".//spine/asset-clip"))
            lanes = len(root.findall(".//section"))
            print(f"  OK  FCPXML 时间线  {nle.stat().st_size/1024:.0f} KB  "
                  f"片段 {spine}  音轨 {lanes}")
        else:
            print("  BAD 缺 FCPXML 时间线")
            ok = False

        # 抽帧
        for i, at in enumerate((dur * 0.15, dur * 0.5, dur * 0.85)):
            out = SHOTS / f"{stem}_{i}.jpg"
            ff.extract_frame(ep, out, at=at, width=960)
        print(f"  抽帧 {len(list(SHOTS.glob(f'{stem}_*.jpg')))} 张 -> {SHOTS}")

    print("=" * 62)
    print("总体:", "全部通过" if ok else "有未通过项")


if __name__ == "__main__":
    main()
