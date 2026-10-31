"""The cuts the director wrote into the segment.

The storyboard writes the segment as several shots with their own times -
"shot one, zero to four seconds, the stage ...; shot two, four to seven
seconds, close on her face" - and the model was told to cut there.  It was
told, and it wrote one continuous take in almost every segment.

So the cut is put into the prompt from the director's own times: the
segment's beats, scaled to the length the segment actually ended up with,
in the form the model is told to use.
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
    # the helper
    ("""def _line_windows(shot, lines) -> list[tuple[float, float, str, str]]:""",
     '''def _internal_cuts(shot) -> list[tuple[float, float]]:
    """The shots the director wrote inside the segment, with their times.

    The action reads "shot one, zero to four seconds, ...; shot two, four
    to seven seconds, close on her face" - the segment is cut there, and
    the model has to be told so in the form it understands.
    """
    action = shot.action or ""
    cuts: list[tuple[float, float]] = []
    for m in re.finditer(r"镜头\\s*\\d+\\s*[（(]\\s*([\\d.]+)\\s*[-—~]\\s*([\\d.]+)\\s*秒",
                         action):
        cuts.append((float(m.group(1)), float(m.group(2))))
    if not cuts:
        return []
    # the action was written for the length the director first gave the
    # segment; the segment may have been scaled since
    last = cuts[-1][1]
    dur = float(shot.duration or 0.0)
    if last > 0.3 and dur > 0.3 and abs(last - dur) > 0.3:
        k = dur / last
        cuts = [(a * k, b * k) for a, b in cuts]
    return cuts


def _line_windows(shot, lines) -> list[tuple[float, float, str, str]]:'''),
    # and the cut in the prompt
    ("""            # A segment that is cut inside is a short drama; a ten second
            # take is a short drama that has forgotten to cut.  The model
            # was told to write the cuts and wrote one take in almost every
            # segment, so the cut is put in here, at the second beat, in the
            # form the model is told to use.
            if desc and "[Shot 2]" not in desc and len(windows) >= 2:
                at = windows[1][0]
                desc = desc.rstrip() + (
                    f"\\nAt {at:06.3f}, the camera cuts to [Shot 2]: a closer "
                    f"framing of the same moment, a different angle on the "
                    f"people, the action carrying on and the light unchanged.")""",
     """            # A segment that is cut inside is a short drama; a ten second
            # take is a short drama that has forgotten to cut.  The model
            # was told to write the cuts and wrote one take in almost every
            # segment, so the cut is put in here, at the times the director
            # wrote into the action, in the form the model is told to use.
            cuts = _internal_cuts(shot)
            if desc and "[Shot 2]" not in desc and len(cuts) >= 2:
                marks = []
                for i, (at, _end) in enumerate(cuts[1:], 2):
                    marks.append(
                        f"At {at:06.3f}, the camera cuts to [Shot {i}]: a "
                        f"different framing of the same moment - a different "
                        f"size of shot and a different angle on the people - "
                        f"the action carrying on and the light unchanged.")
                desc = desc.rstrip() + "\\n" + "\\n".join(marks)"""),
])
