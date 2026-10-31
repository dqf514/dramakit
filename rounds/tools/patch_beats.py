"""The segment has to be written as the several shots it is.

The model makes one continuous take: the prompt said where to cut and the
clip did not cut.  What it needs is not a marker but the shots themselves -
the storyboard wrote them down ("shot two, four and a half to six point
two seconds, close up: the bouquet hits Lu Chen's cheek, the petals
burst, he turns his head"), and the description has to be those shots, one
after another, with the cut between them.

So the shots the director wrote are handed to the model as the shots to
write, and the template asks for them by name.
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
    # the beats, with what happens in each
    ("""def _internal_cuts(shot) -> list[tuple[float, float]]:""",
     '''def _segment_beats(shot) -> list[tuple[float, float, str]]:
    """The shots inside the segment, with their times and what happens.

    The storyboard writes them down - "shot one, zero to four and a half
    seconds, medium, fixed, slightly low: ...; shot two, four and a half
    to six point two seconds, close up: ..." - and the model has to write
    them as the shots they are, with the cut between them.
    """
    action = shot.action or ""
    marks = list(re.finditer(
        r"镜头\\s*(\\d+)\\s*[（(]?\\s*([\\d.]+)\\s*[-—~]\\s*([\\d.]+)\\s*秒([^：:]*)[:：]", action))
    if not marks:
        return []
    out: list[tuple[float, float, str]] = []
    for i, m in enumerate(marks):
        body = action[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(action)]
        out.append((float(m.group(2)), float(m.group(3)),
                    (m.group(1) + "，" + m.group(4) + "：" + body).strip("；; ")))
    last = out[-1][1]
    dur = float(shot.duration or 0.0)
    if last > 0.3 and dur > 0.3 and abs(last - dur) > 0.3:
        k = dur / last
        out = [(a * k, b * k, t) for a, b, t in out]
    return out


def _internal_cuts(shot) -> list[tuple[float, float]]:'''),
    # and the template gets them
    ("""            references=_reference_jobs(shot),
            timeline=_shot_timeline(shot, lines),
            constraints=H3_CONSTRAINTS)""",
     """            references=_reference_jobs(shot),
            timeline=_shot_timeline(shot, lines),
            segment_shots=_segment_shots_text(shot),
            constraints=H3_CONSTRAINTS)"""),
    # the text
    ("""def _shot_timeline(shot, lines) -> str:""",
     '''def _segment_shots_text(shot) -> str:
    """The shots inside the segment, as the model is to write them."""
    beats = _segment_beats(shot)
    if len(beats) < 2:
        return ""
    out = []
    for i, (at, end, what) in enumerate(beats, 1):
        out.append(f"[Shot {i}] {at:.1f}-{end:.1f}秒：{what}")
    return "\\n".join(out)


def _shot_timeline(shot, lines) -> str:'''),
])

patch("dramakit/prompts/templates.py", [
    ("""**时间轴（必须与 {{duration}} 秒一致）**：
{{timeline}}""",
     """**时间轴（必须与 {{duration}} 秒一致）**：
{{timeline}}
{% if segment_shots %}
**这一段是几个镜头，逐个写出来**（下面的切点是定好的，不要改时间）：
{{segment_shots}}
integrated_multimodal_description 就要写成 [Shot 1] … [Shot 2] … [Shot 3] … 的样子，
每个镜头写自己的景别、机位和内容，镜头之间用
`At 00:0X.XXX, the camera cuts to [Shot N]` 开头（硬切，不是叠化）。
**这一段不能写成一镜到底**
{% endif %}"""),
    ("""- **这一段要切成 2~4 个镜头，不要写成一镜到底**（除非这一段本来就只有一个动作）：
  [Shot 1] … At 00:0X.XXX, the camera cuts to … [Shot 2] … At 00:0Y.XXX, the camera
  cuts to … [Shot 3] …
  每个新镜头都要**换景别换机位**（近景↔特写↔过肩↔中景），
  切点是硬切（cut），不是叠化；时间和下面的时间轴对齐""",
     """- **这一段要写成几个镜头，不要写成一镜到底**（除非下面没有给镜头）：
  [Shot 1] … At 00:0X.XXX, the camera cuts to … [Shot 2] … At 00:0Y.XXX, the camera
  cuts to … [Shot 3] …
  每个新镜头都要**换景别换机位**（近景↔特写↔过肩↔中景），
  切点是硬切（cut），不是叠化；时间和上面给的切点对齐"""),
])
