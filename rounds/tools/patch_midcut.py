"""A segment the director left with one shot still gets a cut.

The director's own rule is two to four shots inside a segment.  When the
storyboard wrote one, the segment would run ten seconds without a cut -
which is a short drama that has forgotten to cut.  So the segment is cut
in the middle, on the same action, with a different framing.
"""
from pathlib import Path

ROOT = Path(r"E:\\dramakit")


def patch(path: str, pairs: list[tuple[str, str]]) -> None:
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s and old not in s:
            print(f"  {path}: 已经打过补丁了")
            continue
        assert old in s, f"{path}: 锚点没找到\n{old[:200]}"
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"  {path}: 改好了")


patch("dramakit/pipeline/promptgen.py", [
    # the cut markers, in one place
    ("""def _internal_cuts(shot) -> list[tuple[float, float]]:""",
     '''def _cut_marks(shot) -> list[str]:
    """The cut markers the segment is to have.

    From the shots the director wrote inside it; and when the director
    left the segment with one shot, the segment is cut in the middle, on
    the same action, with a different framing - ten seconds without a cut
    is a short drama that has forgotten to cut.
    """
    beats = _segment_beats(shot)
    dur = float(shot.duration or 0.0)
    if len(beats) >= 2:
        return [f"At {at:06.3f}, the camera cuts to [Shot {i}]: a different "
                f"framing of the same moment - a different size of shot and a "
                f"different angle on the people - the action carrying on and "
                f"the light unchanged."
                for i, (at, _end, _what) in enumerate(beats[1:], 2)]
    if len(beats) == 1 and dur > 6.5:
        at = dur * 0.55
        return [f"At {at:06.3f}, the camera cuts to [Shot 2]: a closer framing "
                f"of the same moment, a different angle on the people, the "
                f"action carrying on and the light unchanged."]
    return []


def _internal_cuts(shot) -> list[tuple[float, float]]:'''),
    # and the prompt uses them
    ("""            cuts = _internal_cuts(shot)
            if desc and "[Shot 2]" not in desc and len(cuts) >= 2:
                marks = []
                for i, (at, _end) in enumerate(cuts[1:], 2):
                    marks.append(
                        f"At {at:06.3f}, the camera cuts to [Shot {i}]: a "
                        f"different framing of the same moment - a different "
                        f"size of shot and a different angle on the people - "
                        f"the action carrying on and the light unchanged.")
                desc = desc.rstrip() + "\\n" + "\\n".join(marks)""",
     """            marks = _cut_marks(shot)
            if desc and "[Shot 2]" not in desc and marks:
                desc = desc.rstrip() + "\\n" + "\\n".join(marks)"""),
])
