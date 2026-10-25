"""Shot-level colour normalisation.

AI shots are rendered independently, so each one lands on a slightly different
exposure, saturation and white balance. Cut together they read as "amateur" --
this is the single biggest tell of AI-generated footage, not the lack of a
professional NLE.

This module measures every shot with ffmpeg's `signalstats` filter and nudges
each one toward a common look (the episode median), plus optional LUT for a
shared colour grade.

    stats = grade.analyze(clip)
    target = grade.median_stats([grade.analyze(c) for c in clips])
    grade.grade_shot(clip, out, target, strength=0.8)
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from .ffmpeg import _run, ffmpeg_bin

_SIGNAL = re.compile(r"lavfi\.signalstats\.(\w+)=(-?[\d.]+)")


@dataclass
class ColorStats:
    """Averaged signal statistics of one clip."""
    luma: float = 0.0        # YAVG, 0..255
    sat: float = 0.0         # SATAVG, 0..255
    u: float = 0.0           # UAVG (blue-diff), 0..255
    v: float = 0.0           # VAVG (red-diff), 0..255
    ylow: float = 0.0
    yhigh: float = 0.0
    frames: int = 0

    @property
    def contrast(self) -> float:
        """Dynamic range proxy (YHIGH - YLOW)."""
        return max(self.yhigh - self.ylow, 1.0)

    @property
    def tint(self) -> float:
        """Positive = warm (red dominant), negative = cool (blue dominant)."""
        return self.v - self.u

    def to_dict(self) -> dict:
        return {
            "luma": round(self.luma, 2),
            "sat": round(self.sat, 2),
            "tint": round(self.tint, 2),
            "contrast": round(self.contrast, 2),
            "frames": self.frames,
        }


# --------------------------------------------------------------------------- #
# measurement
# --------------------------------------------------------------------------- #
def analyze(path: str | Path, sample_every: int = 12) -> ColorStats:
    """Measure a clip's exposure / saturation / white balance.

    Frames are sampled sparsely (every `sample_every` frames) - measuring all
    frames of a 5s clip costs real time and adds nothing.
    """
    vf = (f"select='not(mod(n\\,{max(sample_every,1)}))',"
          f"signalstats,metadata=print:file=-")
    r = _run([ffmpeg_bin(), "-i", str(path), "-vf", vf,
              "-f", "null", "-"], quiet=True)
    text = (r.stderr or "") + (r.stdout or "")
    acc: dict[str, list[float]] = {}
    for name, value in _SIGNAL.findall(text):
        acc.setdefault(name, []).append(float(value))
    if not acc:
        return ColorStats()
    n = max(len(acc.get("YAVG", [1])), 1)

    def mean(key: str, default: float = 0.0) -> float:
        vals = acc.get(key)
        return sum(vals) / len(vals) if vals else default

    return ColorStats(
        luma=mean("YAVG"),
        sat=mean("SATAVG", mean("SATAVG")),
        u=mean("UAVG"),
        v=mean("VAVG"),
        ylow=mean("YLOW"),
        yhigh=mean("YHIGH"),
        frames=n,
    )


def median_stats(items: Sequence[ColorStats]) -> ColorStats:
    """The episode's reference look: the median of every shot.

    Median (not mean) so one badly-lit shot cannot drag the whole episode.
    """
    if not items:
        return ColorStats()
    def med(getter) -> float:
        vals = [getter(i) for i in items if getter(i) or getter(i) == 0.0]
        vals = [v for v in vals if v is not None]
        return statistics.median(vals) if vals else 0.0
    return ColorStats(
        luma=med(lambda s: s.luma),
        sat=med(lambda s: s.sat),
        u=med(lambda s: s.u),
        v=med(lambda s: s.v),
        ylow=med(lambda s: s.ylow),
        yhigh=med(lambda s: s.yhigh),
        frames=sum(i.frames for i in items),
    )


# --------------------------------------------------------------------------- #
# grading
# --------------------------------------------------------------------------- #
def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def grade_filter(src: ColorStats, target: ColorStats, strength: float = 1.0,
                 lut: str | Path | None = None) -> str:
    """Build an ffmpeg filter chain that moves `src` toward `target`."""
    s = max(0.0, min(1.0, strength))
    parts: list[str] = []

    # exposure -> eq=brightness is a luma offset in code values / 255
    if target.luma > 0 and src.luma > 0:
        delta = (target.luma - src.luma) / 255.0 * s
        if abs(delta) > 0.004:
            parts.append(f"eq=brightness={_clip(delta, -0.35, 0.35):.4f}")

    # saturation -> eq=saturation is a multiplier around the luma axis
    if target.sat > 1 and src.sat > 1:
        mul = (target.sat / src.sat) ** s
        if abs(mul - 1.0) > 0.02:
            parts.append(f"eq=saturation={_clip(mul, 0.2, 3.0):.4f}")

    # contrast -> eq=contrast is a multiplier around mid grey
    if target.contrast > 1 and src.contrast > 1:
        mul = (target.contrast / src.contrast) ** s
        if abs(mul - 1.0) > 0.02:
            parts.append(f"eq=contrast={_clip(mul, 0.5, 2.0):.4f}")

    # white balance -> per-channel gain via lutrgb (U high = too blue)
    if abs(src.tint) > 3.0 and abs(target.tint) > 0.5:
        shift = (src.tint - target.tint) / 128.0 * s
        gr = 1.0 + _clip(shift, -0.12, 0.12)
        gb = 1.0
        bl = 1.0 - _clip(shift, -0.12, 0.12)
        if abs(gr - 1.0) > 0.005 or abs(bl - 1.0) > 0.005:
            parts.append(
                f"lutrgb=r='clip(val*{gr:.4f},0,255)':"
                f"g='clip(val*{gb:.4f},0,255)':"
                f"b='clip(val*{bl:.4f},0,255)'")

    if lut:
        p = str(lut).replace("\\", "/").replace(":", "\\:")
        parts.append(f"lut3d='{p}'")
    return ",".join(parts)


def grade_shot(src: str | Path, out: str | Path, target: ColorStats,
               strength: float = 1.0, lut: str | Path | None = None,
               measured: Optional[ColorStats] = None,
               crf: int = 20, preset: str = "medium",
               fps: Optional[int] = None) -> str:
    """Re-encode one clip with the correction filter applied."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    st = measured if measured is not None else analyze(src)
    vf = grade_filter(st, target, strength=strength, lut=lut)
    if not vf:
        # nothing to correct - copy so downstream code has a uniform path
        import shutil
        shutil.copy2(src, out)
        return str(out)
    cmd = [ffmpeg_bin(), "-y", "-i", str(src), "-vf", vf]
    if fps:
        cmd += ["-r", str(fps)]
    # no audio: the graded clip has to match the others bit for bit when the
    # scene is concatenated, and the mix is built from the voice and the bed
    cmd += ["-an", "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
            "-pix_fmt", "yuv420p", str(out)]
    _run(cmd, quiet=False)
    return str(out)
