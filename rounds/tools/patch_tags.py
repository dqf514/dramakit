"""The tags have to be the shot's own words.

The model that writes the description puts the words of the shot in the
dialogue tags - most of the time.  Two things go wrong now and then: it
drops a line, and it puts a line that belongs to the next shot in the
tag (and once it wrote a caption card, "episode two, the rain", as if it
were something to say out loud).

So the tags are checked against the lines the shot carries: the ones that
do not belong are taken out, the ones that are missing are written in
with the moment they belong to.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")

old = """        # A line that is not in the prompt is a line nobody says.  The model
        # that writes the description drops one now and then, so the ones it
        # left out are written back in with the moment they belong to.
        if desc and ctx.cfg.comfyui.native_audio and lines:
            windows = _line_windows(shot, lines)
            add = []
            for (start, end, spk, txt) in windows:
                if _said(desc, txt):
                    continue
                add.append(f"From {start:.1f} to {end:.1f} seconds, {spk} opens "
                           f"their mouth and speaks, the lips moving with every "
                           f"syllable: <d>[zh-CN]{txt}</d>")
            if add:
                desc = desc.rstrip() + "\\n" + "\\n".join(add)"""

new = """        # The tags have to be the shot's own words.  The model that writes
        # the description drops a line now and then, and it puts the words
        # of the next shot in the tag - and once it wrote a caption card as
        # if it were something to say out loud.  The ones that do not belong
        # are taken out; the ones that are missing are written back in with
        # the moment they belong to.
        if desc and ctx.cfg.comfyui.native_audio and lines:
            allowed = {txt.strip() for _spk, txt, _d in lines if txt and txt.strip()}

            def _keep(m):
                return m.group(0) if m.group(1).strip() in allowed else ""

            desc = re.sub(r"<d>\\[zh-CN\\](.*?)</d>", _keep, desc)
            windows = _line_windows(shot, lines)
            add = []
            for (start, end, spk, txt) in windows:
                if _said(desc, txt):
                    continue
                add.append(f"From {start:.1f} to {end:.1f} seconds, {spk} opens "
                           f"their mouth and speaks, the lips moving with every "
                           f"syllable: <d>[zh-CN]{txt}</d>")
            if add:
                desc = desc.rstrip() + "\\n" + "\\n".join(add)"""

assert old in s, "提示词台词修复锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py: 不属于这一镜的台词标签会被拿掉")

# and the QA counts the lines the way the pipeline does
q = Path(r"E:\\dramakit\\qa.py")
t = q.read_text(encoding="utf-8")
old2 = """    spoken = [t for t in tl.lines if t.line.kind.value == "dialogue"]
    if ctx.cfg.comfyui.native_audio:"""
new2 = """    spoken = [t for t in tl.lines if not is_narration(t.line)]
    if ctx.cfg.comfyui.native_audio:"""
if old2 in t:
    t = t.replace(old2, new2, 1)
    q.write_text(t, encoding="utf-8")
    print("qa.py: 台词数法改过来了")
else:
    print("qa.py: 那处已经改过了")
