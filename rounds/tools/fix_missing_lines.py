"""Write the lines the model left out back into the prompts.

The same rule the prompt generator now follows, applied to the prompts
that are already written: every line the shot carries has to be in the
prompt, inside the dialogue tag.  The shots that were missing a line are
listed - they have to be drawn again, or the words are never said.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.promptgen import _line_windows, _said
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "短剧_重生恶毒继母"
eps = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [1]

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
store = ProjectStore(Path(r"E:\\dramakit\\projects") / name)
ctx = Context(cfg, store)

fixed = []
for ep in ctx.project.episodes:
    if ep.index not in eps:
        continue
    tl = ctx.timeline(ep)
    for tsc in tl.scenes:
        for ts in tsc.shots:
            shot = ts.shot
            vp = shot.video_prompt or ""
            if not vp:
                continue
            lines = []
            for t in tsc.lines:
                if t.line.kind.value != "dialogue":
                    continue
                if not (ts.start - 0.02 <= t.start < ts.start + ts.duration):
                    continue
                dur = max(0.1, t.end - t.start)
                lines.append((t.line.speaker, t.line.text, dur))
            if not lines:
                continue
            # the description is the part between the header and the soundscape
            head, sep, tail = vp.partition("detailed_description:")
            body, sep2, rest = tail.partition("overall_soundscape:")
            if not sep or not sep2:
                continue
            add = []
            for (start, end, spk, txt) in _line_windows(shot, lines):
                if _said(body, txt):
                    continue
                add.append(f"From {start:.1f} to {end:.1f} seconds, {spk} opens "
                           f"their mouth and speaks, the lips moving with every "
                           f"syllable: <d>[zh-CN]{txt}</d>")
            if add:
                shot.video_prompt = head + sep + body.rstrip() + "\n" + "\n".join(add) + \
                    "\n\n" + sep2 + rest
                fixed.append(shot.id)
ctx.save()
print(f"{name}: 补回台词的片段 {len(fixed)} 个")
for sid in fixed:
    print("  " + sid)
print("\n这些片段要重画：")
for sid in fixed:
    print(f'  .\\venv\\Scripts\\dj.exe run ... ; 或用 rounds\\tools\\regen_list.py {sid}')
