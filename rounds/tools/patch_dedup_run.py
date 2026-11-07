"""The old run() is still in the file, after the new one.

The merge cut the file at the wrong place and put the old stage back
after the new one, so Python used the old one and the merged stage
never ran.  One run() now - the merged one - and the dialogue check
that was in the old one rides along.
"""
import pathlib

P = pathlib.Path(r"E:\dramakit\dramakit\pipeline\script.py")
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

# ---- 1. cut the old run() and its second copy of _flatness ---------- #
marker = "def _flatness(scenes: list) -> tuple[int, int]:"
first = text.index(marker)
second = text.index(marker, first + 1)
text = text[:second].rstrip("\n") + "\n"

# ---- 2. the dialogue check rides along in the merged run ------------- #
old = """        done += 1
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 镜",
                     ep.index, ep.title, len(ep.scenes),
                     sum(len(s.shots) for s in ep.scenes))
    return {"episodes_scripted": done}"""
new = """        done += 1
        n_shots = sum(len(s.shots) for s in ep.scenes)
        ctx.log.info("script: 第%d集《%s》→ %d 场, %d 镜",
                     ep.index, ep.title, len(ep.scenes), n_shots)
        # the dialogue check: a script that is one long interrogation
        # reads like a form being filled in
        pairs, lines = _flatness(ep.scenes)
        pct = int(pairs * 100 / max(1, lines))
        if pct >= 25:
            ctx.log.warning("script: 第%d集有 %d%% 的台词是一问一答，"
                            "人物像在填表而不是在说话", ep.index, pct)
    return {"episodes_scripted": done}"""
assert old in text, "没找到新 run 的收尾"
text = text.replace(old, new, 1)

if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("旧 run 删掉了，台词检查留在新 run 里")
