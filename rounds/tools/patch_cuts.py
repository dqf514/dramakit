"""A segment has to be cut inside.

A ten second take is a short drama that has forgotten to cut: the
reference films cut twenty to forty times a minute, and the eye reads a
long uncut take as dead.  The model was told to write the cuts, and wrote
one continuous take in thirty-two segments out of thirty-three.

So the description is asked for it more firmly, and the code checks: a
segment that has a second beat gets a cut marker at that beat, in the
form the model is told to use.
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


# --------------------------------------------------------------------------- #
# 1. the prompt asks for it more firmly
# --------------------------------------------------------------------------- #
patch("dramakit/prompts/templates.py", [
    ("""要求：
- integrated_multimodal_description 以 [Shot 1] 开头，描述这一镜的完整画面与运动
- 本镜台词用 <d>[zh-CN]...</d> 包住，保留原样台词""",
     """要求：
- integrated_multimodal_description 以 [Shot 1] 开头，描述这一镜的完整画面与运动
- **这一段要切成 2~4 个镜头，不要写成一镜到底**（除非这一段本来就只有一个动作）：
  [Shot 1] … At 00:0X.XXX, the camera cuts to … [Shot 2] … At 00:0Y.XXX, the camera
  cuts to … [Shot 3] …
  每个新镜头都要**换景别换机位**（近景↔特写↔过肩↔中景），
  切点是硬切（cut），不是叠化；时间和下面的时间轴对齐
- 本镜台词用 <d>[zh-CN]...</d> 包住，保留原样台词"""),
])

# --------------------------------------------------------------------------- #
# 2. and the code makes sure the cut is there
# --------------------------------------------------------------------------- #
patch("dramakit/pipeline/promptgen.py", [
    ("""            if add:
                desc = desc.rstrip() + "\\n" + "\\n".join(add)
        if desc:""",
     """            if add:
                desc = desc.rstrip() + "\\n" + "\\n".join(add)
            # A segment that is cut inside is a short drama; a ten second
            # take is a short drama that has forgotten to cut.  The model
            # was told to write the cuts and wrote one take in almost every
            # segment, so the cut is put in here, at the second beat, in the
            # form the model is told to use.
            if desc and "[Shot 2]" not in desc and len(windows) >= 2:
                at = windows[1][0]
                desc = desc.rstrip() + (
                    f"\\nAt {at:06.3f}, the camera cuts to [Shot 2]: a closer "
                    f"framing of the same moment, a different angle on the "
                    f"people, the action carrying on and the light unchanged.")
        if desc:"""),
])
