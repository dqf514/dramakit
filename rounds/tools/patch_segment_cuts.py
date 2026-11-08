"""A segment is a short sequence, not one long take.

The switch was off because a segment cut inside used to drift the face:
ten seconds with five cuts changed the face twice.  That was before the
prompt told H3 what a segment is - single time points, each shot with
its own framing, the reference pictures' jobs spelled out - and before
the cuts were proposed by the code instead of asked for in prose.

So the switch goes on, and the reason it was off is written down where
the switch is.
"""
import pathlib
import re

ROOT = pathlib.Path(r"E:\dramakit")


def patch(rel: str, old_line: str, new_line: str, note: str) -> None:
    p = ROOT / rel
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    # the comment block above the line, however many lines it is
    pat = re.compile(r"(?:#[^\n]*\n)+(?=\s*" + re.escape(old_line) + r")")
    m = pat.search(text)
    assert m, "%s 里没找到那段说明" % rel
    text = text[:m.start()] + note + text[m.end():]
    text = text.replace(old_line, new_line, 1)
    if crlf:
        text = text.replace("\n", "\r\n")
    p.write_bytes(text.encode("utf-8"))
    print("  %s 改了" % rel)


patch("config/default.yaml",
      "segment_cuts: false",
      "segment_cuts: true",
      "  # 一段是几个镜头的短序列：切点由代码给出（单点时间，At 00:0X.XXX），\n"
      "  # 每个镜头有自己的景别和角度。\n"
      "  # 以前这里是 false：那时候切点让模型自己写、提示词里又没写清一段到\n"
      "  # 底是什么，脸会在段内漂（实测十秒五刀，脸变了两次）。现在切点由代码\n"
      "  # 定、参考图的分工写明，一段两到三刀。\n")

patch("dramakit/config.py",
      "segment_cuts: bool = False",
      "segment_cuts: bool = True",
      "    # 一段是几个镜头的短序列：切点由代码给出（单点时间），每个镜头\n"
      "    # 有自己的景别和角度。以前这里是 False——那时候切点让模型自己写，\n"
      "    # 脸会在段内漂（实测十秒五刀，脸变了两次）。\n")
