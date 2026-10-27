"""Two small things the finished episode showed.

The scene fades at a transition were counted as two cuts, which made the
rhythm look faster than it is and produced a sixteenth second "shot". And
the AIGC label is only asked for in the opening, so it does not have to
sit on every frame.
"""
from pathlib import Path

# 1) the rhythm analysis: cuts that sit on top of each other are one cut
p = Path(r"E:\dramakit\dramakit\ref_rhythm.py")
s = p.read_text(encoding="utf-8")
old = """    dur = _duration(path)
    cuts = sorted(set(round(t, 2) for t in _cuts(path)))"""
new = """    dur = _duration(path)
    raw = sorted(set(round(t, 2) for t in _cuts(path)))
    # a transition fades to black and back, which the detector sees as two
    # cuts; they are one cut
    cuts: list[float] = []
    for t in raw:
        if cuts and t - cuts[-1] < 0.5:
            continue
        cuts.append(t)"""
assert old in s, "切点锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# 2) the AIGC label: always, or only in the opening
p = Path(r"E:\dramakit\dramakit\media\ffmpeg.py")
s = p.read_text(encoding="utf-8")
old = """    if watermark:
        text = watermark.replace("\\\\", "\\\\\\\\").replace(":", "\\\\:").replace("'", "")
        font = _cjk_font()
        vf.append(
            f"drawtext=fontfile='{font}':text='{text}':fontcolor=white@0.6:"
            f"fontsize={watermark_size}"
            f":x=24:y=20:box=1:boxcolor=black@0.35:boxborderw={max(8, int(height*0.03))}")"""
new = """    if watermark:
        text = watermark.replace("\\\\", "\\\\\\\\").replace(":", "\\\\:").replace("'", "")
        font = _cjk_font()
        label = (f"drawtext=fontfile='{font}':text='{text}':fontcolor=white@0.6:"
                 f"fontsize={watermark_size}"
                 f":x=24:y=20:box=1:boxcolor=black@0.35:boxborderw={max(8, int(height*0.03))}")
        if watermark_seconds and watermark_seconds > 0:
            # the platform asks for the label in the opening, not on every frame
            label += f":enable='between(t,0,{watermark_seconds:.1f})'"
        vf.append(label)"""
assert old in s, "水印锚点没找到"
s = s.replace(old, new, 1)
old = """        watermark: str = "", watermark_size: int = 18,
        grain: int = 0) -> str:"""
new = """        watermark: str = "", watermark_size: int = 18,
        watermark_seconds: float = 0.0, grain: int = 0) -> str:"""
assert old in s, "mux 签名锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# 3) the compose passes it
p = Path(r"E:\dramakit\dramakit\pipeline\compose.py")
s = p.read_text(encoding="utf-8")
old = """           watermark=mark, watermark_size=max(14, cc.height // 30),
           grain=int(cc.film_grain or 0))"""
new = """           watermark=mark, watermark_size=max(14, cc.height // 30),
           watermark_seconds=float(cc.ai_declaration_seconds or 0),
           grain=int(cc.film_grain or 0))"""
assert old in s, "compose 水印锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# 4) the config
p = Path(r"E:\dramakit\dramakit\config.py")
s = p.read_text(encoding="utf-8")
old = """    ai_declaration: str = "本片画面与声音由AI生成\""""
new = """    ai_declaration: str = "本片画面与声音由AI生成"
    ai_declaration_seconds: float = 3.0                        # 声明只放在片头几秒"""
assert old in s, "config 水印锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

p = Path(r"E:\dramakit\config\default.yaml")
s = p.read_text(encoding="utf-8")
old = """  ai_declaration: "本片画面与声音由AI生成\""""
new = """  ai_declaration: "本片画面与声音由AI生成"
  ai_declaration_seconds: 3                    # 声明只放在片头 3 秒（平台要求）"""
assert old in s, "yaml 水印锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

print("节奏分析与水印已改")
