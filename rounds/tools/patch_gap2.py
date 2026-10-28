"""Wire the line gap through the config and every place the timeline is built."""
from pathlib import Path

# 1) the config
p = Path(r"E:\dramakit\dramakit\config.py")
s = p.read_text(encoding="utf-8")
old = """    film_grain: int = 4                                    # 胶片颗粒强度（去掉 AI 塑料感，0=关）"""
new = """    film_grain: int = 4                                    # 胶片颗粒强度（去掉 AI 塑料感，0=关）
    # 每句台词之间的留白（秒）。背靠背的台词听起来像在念清单，
    # 留半秒让对方接住，这是短剧的戏在的地方。
    line_gap: float = 0.35"""
assert old in s, "config 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# 2) the yaml
p = Path(r"E:\dramakit\config\default.yaml")
s = p.read_text(encoding="utf-8")
old = """  film_grain: 4                            # 胶片颗粒强度（去掉 AI 塑料感，0=关）"""
new = """  film_grain: 4                            # 胶片颗粒强度（去掉 AI 塑料感，0=关）
  line_gap: 0.35                            # 每句台词之间的留白（秒）"""
assert old in s, "yaml 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# 3) every call site
edits = [
    (Path(r"E:\dramakit\dramakit\pipeline\compose.py"),
     "    tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds)",
     "    tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                      line_gap=cc.line_gap)"),
    (Path(r"E:\dramakit\dramakit\pipeline\compose.py"),
     "         build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds).duration)",
     "         build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                      line_gap=cc.line_gap).duration)"),
    (Path(r"E:\dramakit\dramakit\pipeline\visual.py"),
     "        for ts in build_timeline(\n"
     "                ep, max_shot=ctx.cfg.comfyui.max_video_seconds).shots:",
     "        for ts in build_timeline(\n"
     "                ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                line_gap=ctx.cfg.compose.line_gap).shots:"),
    (Path(r"E:\dramakit\dramakit\pipeline\subtitle.py"),
     "        tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds)",
     "        tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                           line_gap=ctx.cfg.compose.line_gap)"),
    (Path(r"E:\dramakit\qa.py"),
     "        tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds)",
     "        tl = build_timeline(ep, max_shot=ctx.cfg.comfyui.max_video_seconds,\n"
     "                           line_gap=ctx.cfg.compose.line_gap)"),
]
for path, old, new in edits:
    s = path.read_text(encoding="utf-8")
    if old not in s:
        print(f"跳过（锚点没找到）: {path.name}: {old[:48]}")
        continue
    s = s.replace(old, new, 1)
    path.write_text(s, encoding="utf-8")
    print(f"已改: {path.name}")
