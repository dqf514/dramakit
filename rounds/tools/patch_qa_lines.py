"""The QA counts the lines the way the pipeline does.

A line is spoken unless it is narration or a caption card - that is what
`is_narration` says, and it is what the timeline, the storyboard and the
prompt generator go by.  The QA counted them its own way: it left the
caption cards in, so every index was one off, and a shot whose prompt held
exactly the right words was reported as missing one.  The monologues were
left out the other way, so a line that is spoken and has to be heard was
not counted at all.
"""
from pathlib import Path

q = Path(r"E:\\dramakit\\qa.py")
t = q.read_text(encoding="utf-8")

pairs = [
    ('    spoken = [t for t in tl.lines if t.line.kind.value == "dialogue"]\n'
     '    if not spoken:',
     '    spoken = [t for t in tl.lines if not is_narration(t.line)]\n'
     '    if not spoken:'),
    ('        spoken = [l for l in sc.lines if l.kind.value != "narration"]\n'
     '        for shot in sc.shots:',
     '        spoken = [l for l in sc.lines if not is_narration(l)]\n'
     '        for shot in sc.shots:'),
    ('        lines = [t for t in tl.lines\n'
     '                 if t.line.kind.value == "dialogue"\n'
     '                 and ts.start <= t.start < ts.start + ts.duration]',
     '        lines = [t for t in tl.lines\n'
     '                 if not is_narration(t.line)\n'
     '                 and ts.start <= t.start < ts.start + ts.duration]'),
    ('        order = [l for l in sc.lines if l.kind.value == "dialogue"]',
     '        order = [l for l in sc.lines if not is_narration(l)]'),
    ('        seq = [pos.get(id(t.line), -1) for t in tl.lines\n'
     '               if t.line.kind.value == "dialogue"]',
     '        seq = [pos.get(id(t.line), -1) for t in tl.lines\n'
     '               if not is_narration(t.line)]'),
    ('    spoken = sum(1 for sc in ep.scenes for l in sc.lines\n'
     '                 if l.audio_path and l.kind.value != "narration")',
     '    spoken = sum(1 for sc in ep.scenes for l in sc.lines\n'
     '                 if l.audio_path and not is_narration(l))'),
    ('    spoken_lines = [t for t in tl.lines\n'
     '                    if t.line.audio_path and t.line.kind.value == "dialogue"]',
     '    spoken_lines = [t for t in tl.lines\n'
     '                    if t.line.audio_path and not is_narration(t.line)]'),
]
for old, new in pairs:
    if new in t:
        print("  已经改过")
        continue
    assert old in t, f"锚点没找到:\n{old[:140]}"
    t = t.replace(old, new, 1)

q.write_text(t, encoding="utf-8")
print("qa.py: 台词的数法统一了")
