"""Put several pictures side by side."""
from pathlib import Path
from typing import Sequence

from . import ffmpeg as _ff


def character_sheet(face: str | Path, bodies: Sequence[str | Path],
                     out: str | Path, *, width: int = 1536, height: int = 576,
                     gap: int = 6, face_share: float = 0.4,
                     background: str = "0xe9e9e9") -> str:
    """One picture of a character: the face big on the left, the views right.

    H3 has a handful of reference slots, so the views of a character have
    to share one picture - and the face gets the biggest part of it, since
    the face is what has to stay the same from one shot to the next.
    """
    out = Path(out)
    face_p = Path(face)
    body_ps = [Path(p) for p in bodies if Path(p).exists()]
    if not face_p.exists() and not body_ps:
        raise RuntimeError("character_sheet: 没有图片")
    if not face_p.exists():
        face_p = body_ps.pop(0)
    elif not body_ps:
        body_ps = []

    fw = int(width * face_share)
    bw = max(16, (width - fw - gap * (len(body_ps) + 1)) // max(1, len(body_ps)))
    panels: list[tuple[Path, int, bool]] = [(face_p, fw, False)]
    # the face in the full-body front panel is small and soft; the model can
    # copy it into the video.  The big face is the only face the sheet is
    # allowed to have, so the front panel is cut below the head.
    for p in body_ps:
        headless = face_p is not None and "front" in p.name.lower()
        panels.append((p, bw, headless))

    args = ["ffmpeg", "-v", "error", "-y"]
    for p, _w, _h in panels:
        args += ["-i", str(p)]
    # every panel is cropped to its own width, so the face is not letterboxed
    # and a full body is not squeezed
    chain = []
    for i, (p, w, headless) in enumerate(panels):
        if headless:
            chain.append(
                f"[{i}:v]scale={w}:{height}:force_original_aspect_ratio=increase,"
                f"crop={w}:{int(height * 0.78)}:0:{int(height * 0.22)},"
                f"pad={w}:{height}:0:{int(height * 0.22)}:"
                f"{background}[c{i}]")
        else:
            chain.append(f"[{i}:v]scale={w}:{height}:force_original_aspect_ratio=increase,"
                         f"crop={w}:{height}[c{i}]")
    stack = "".join(f"[c{i}]" for i in range(len(panels)))
    fc = ";".join(chain) + ";" + stack + \
        f"hstack=inputs={len(panels)}[sheet]"
    args += ["-filter_complex", fc, "-map", "[sheet]", "-frames:v", "1",
             "-q:v", "3", str(out)]
    _ff._run(args, quiet=False)
    return str(out)


def contact_sheet(images: Sequence[str | Path], out: str | Path, *,
                  width: int = 1536, gap: int = 8,
                  background: str = "0x101014") -> str:
    """One picture with the given pictures next to each other.

    The character sheets are three views of the same person; the model has
    to see all three at once to keep the person the same in every shot.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    paths = [Path(p) for p in images if Path(p).exists()]
    if not paths:
        raise RuntimeError("contact_sheet: 没有图片")
    if len(paths) == 1:
        _ff._run(["ffmpeg", "-v", "error", "-y", "-i", str(paths[0]),
                  "-vf", f"scale={width}:-1", str(out)], quiet=False)
        return str(out)

    # every panel the same height, then side by side
    h = 0
    for p in paths:
        w0, h0 = _ff.image_size(p)
        h = max(h, h0)
    h = max(h, 1)
    args = ["ffmpeg", "-v", "error", "-y"]
    for p in paths:
        args += ["-i", str(p)]
    parts = []
    for i in range(len(paths)):
        parts.append(f"[{i}:v]scale=-1:{h},pad=iw+{gap}:{h}:{gap}:0:"
                     f"{background}[v{i}]")
    chain = ";".join(parts)
    stack_in = "".join(f"[v{i}]" for i in range(len(paths)))
    fc = (f"{chain};{stack_in}hstack=inputs={len(paths)}[sheet];"
          f"[sheet]scale={width}:-1[out]")
    args += ["-filter_complex", fc, "-map", "[out]", "-frames:v", "1",
             "-q:v", "3", str(out)]
    _ff._run(args, quiet=False)
    return str(out)
