"""One timeline for everybody.

Every stage has to agree on where a line falls inside a shot: the prompt
that asks H3 for the performance, the picture that is cut together, the
subtitle that is written and the music that is laid under it. When two of
them built the timeline differently - one with the breath between the
lines and one without - the prompt asked H3 for one line while the mix
played another, and the lips belonged to the wrong person.
"""
from pathlib import Path

# 1) the helper on Context
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\base.py")
s = p.read_text(encoding="utf-8")
old = """    def stage_done(self, ep: Episode, stage: str) -> bool:"""
new = '''    def timeline(self, ep: Episode) -> Timeline:
        """The one timeline every stage works from.

        The prompt that asks for the performance, the picture that is cut
        together, the subtitles and the music all have to agree on where a
        line falls inside a shot - otherwise the lips belong to the wrong
        person.
        """
        return build_timeline(ep,
                              max_shot=self.cfg.comfyui.max_video_seconds,
                              line_gap=self.cfg.compose.line_gap)

    def stage_done(self, ep: Episode, stage: str) -> bool:'''
assert old in s, "Context 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# 2) every call site
edits = [
    (Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py"),
     "    tl = build_timeline(ep)",
     "    tl = ctx.timeline(ep)"),
    (Path(r"E:\\dramakit\\dramakit\\pipeline\\compose.py"),
     "    tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                      line_gap=cc.line_gap)",
     "    tl = ctx.timeline(ep)"),
    (Path(r"E:\\dramakit\\dramakit\\pipeline\\compose.py"),
     "         build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                      line_gap=cc.line_gap).duration)",
     "         ctx.timeline(ep).duration)"),
    (Path(r"E:\\dramakit\\dramakit\\pipeline\\subtitle.py"),
     "        tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                           line_gap=ctx.cfg.compose.line_gap)",
     "        tl = ctx.timeline(ep)"),
    (Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py"),
     "        for ts in build_timeline(\n"
     "                ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                line_gap=ctx.cfg.compose.line_gap).shots:",
     "        for ts in ctx.timeline(ep).shots:"),
    (Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py"),
     "        for ts in build_timeline(\n"
     "                ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                line_gap=ctx.cfg.compose.line_gap).shots:",
     "        for ts in ctx.timeline(ep).shots:"),
    (Path(r"E:\\dramakit\\dramakit\\review.py"),
     "    tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                        line_gap=ctx.cfg.compose.line_gap)",
     "    tl = ctx.timeline(ep)"),
    (Path(r"E:\\dramakit\\dramakit\\drift.py"),
     "    tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                        line_gap=ctx.cfg.compose.line_gap)",
     "    tl = ctx.timeline(ep)"),
]
for path, old, new in edits:
    s = path.read_text(encoding="utf-8")
    if old not in s:
        print(f"跳过（锚点没找到）: {path.name}: {old.strip()[:50]}")
        continue
    s = s.replace(old, new)
    path.write_text(s, encoding="utf-8")
    print(f"已改: {path.name}")

# 3) the qa script
p = Path(r"E:\\dramakit\\qa.py")
s = p.read_text(encoding="utf-8")
old = """        tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,
                           line_gap=ctx.cfg.compose.line_gap)"""
if old in s:
    s = s.replace(old, "        tl = ctx.timeline(ep)")
    p.write_text(s, encoding="utf-8")
    print("已改: qa.py")
else:
    print("跳过 qa.py（锚点没找到）")

print("完成")
