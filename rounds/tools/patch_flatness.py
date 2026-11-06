"""The flatness is counted, so it can be seen.

A script that is one long interrogation reads like a form being filled
in.  The number says how much of it is that: the questions that are
answered in one short line, with nothing in between - no resistance,
no interruption, no lie.
"""
import pathlib

ROOT = pathlib.Path(r"E:\dramakit")


def edit(path, old, new, what):
    p = ROOT / path
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    assert old in text, "没找到：%s（%s）" % (what, path)
    text = text.replace(old, new, 1)
    if crlf:
        text = text.replace("\n", "\r\n")
    p.write_bytes(text.encode("utf-8"))


# 1. the count
edit("dramakit/pipeline/script.py",
     """def run(ctx: Context) -> dict:""",
     '''def _flatness(scenes: list) -> tuple[int, int]:
    """How much of the dialogue is a question answered straight.

    A script that is one long interrogation reads like a form being
    filled in: the questions are answered in one short line, with
    nothing in between - no resistance, no interruption, no lie.  The
    number says how much of the script is that.
    """
    pairs = 0
    lines = 0
    for sc in scenes:
        ls = list(sc.lines)
        lines += len(ls)
        for i, ln in enumerate(ls[:-1]):
            if "？" not in ln.text and "?" not in ln.text:
                continue
            nxt = ls[i + 1]
            if "？" in nxt.text or "?" in nxt.text:
                continue
            if len(nxt.text) <= 12:
                pairs += 1
    return pairs, lines


def run(ctx: Context) -> dict:''',
     "the count")

# 2. and it is said out loud
edit("dramakit/pipeline/script.py",
     """        done += 1
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 句",
                     ep.index, ep.title, len(ep.scenes),
                     sum(len(s.lines) for s in ep.scenes))
    return {"episodes_scripted": done}""",
     """        done += 1
        pairs, lines = _flatness(ep.scenes)
        pct = int(pairs * 100 / max(1, lines))
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 句（其中 %d 处一问一答，%d%%）",
                     ep.index, ep.title, len(ep.scenes), lines, pairs, pct)
        if pct >= 25:
            ctx.log.warning("script: 第%d集有 %d%% 的台词是一问一答，"
                            "人物像在填表而不是在说话", ep.index, pct)
    return {"episodes_scripted": done}""",
     "the report")

# 3. the flag in the file
edit("config/default.yaml",
     """  opening_recap: true""",
     """  opening_recap: true
  # 初稿之后再磨一遍台词：同样的戏、同样的信息，但每一句都带态度。
  # 关掉就只写初稿（快，但容易写成一问一答）。
  polish_dialogue: true""",
     "the flag")

print("机械问答会报出来了")
