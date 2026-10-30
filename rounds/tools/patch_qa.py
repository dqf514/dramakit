"""Four measurements that were measuring the wrong thing.

1. The pitch of a voice was taken from the single best frame of the whole
   clip, so every character came out at 222 Hz and every pair of characters
   was reported as "the same voice".  The pitch of a voice is the middle of
   its frames, and two voices are the same when they are within a few
   percent of each other, not within ten hertz.

2. The check for a line that is missing from the prompt asked the timeline
   which lines fall inside a shot, which counts a line that belongs to the
   next shot.  The storyboard says which line a shot carries; that is the
   question to ask, and the line's own words have to be in the prompt.

3. The check for "the finished episode has no voice" counted loudness
   jumps in the finished mix, where the music makes the count meaningless.
   When the picture carries the voice, the question is whether the shots
   have a voice in them.

4. Two characters on the same timbre is a real fault and can be checked
   exactly, so it is checked exactly.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\qa.py")
s = p.read_text(encoding="utf-8")

# --------------------------------------------------------------------------- #
# 1. the pitch of a voice
# --------------------------------------------------------------------------- #
old = """    pitch = 0.0
    if norms:
        best = max(max(r) for r in norms)
        # the smallest lag that is nearly as good is the fundamental - taking
        # the global peak instead lands on a harmonic or on the very edge
        found = 0
        for row in norms:
            for i, v in enumerate(row):
                if v >= best * 0.85:
                    found = i
                    break
            if found:
                break
        if found:
            pitch = rate2 / (lo + found)
    return {"pitch": round(pitch, 1), "zcr": round(zcr, 1)}"""

new = """    # The pitch of a voice is the middle of its frames.  Taking the single
    # best frame of the whole clip measures one lucky moment of one line and
    # gives every character the same number.
    found_pitches: list[float] = []
    for row in norms:
        best = max(row)
        if best < 0.3:
            continue
        # the smallest lag that is nearly as good is the fundamental - taking
        # the peak instead lands on a harmonic or on the very edge
        found = 0
        for i, v in enumerate(row):
            if v >= best * 0.9:
                found = i
                break
        if found:
            found_pitches.append(rate2 / (lo + found))
    found_pitches.sort()
    pitch = found_pitches[len(found_pitches) // 2] if found_pitches else 0.0
    return {"pitch": round(pitch, 1), "zcr": round(zcr, 1)}"""
assert old in s, "音色指纹锚点没找到"
s = s.replace(old, new, 1)

# --------------------------------------------------------------------------- #
# 2. two characters, two timbres
# --------------------------------------------------------------------------- #
old = """    names = list(sigs)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = sigs[names[i]], sigs[names[j]]
            if not a["pitch"] or not b["pitch"]:
                continue
            dp = abs(a["pitch"] - b["pitch"])
            dz = abs(a["zcr"] - b["zcr"]) / max(a["zcr"], b["zcr"], 1.0)
            if dp < 10 and dz < 0.10:
                issues.append(("voice", "voices_too_similar", "-",
                               f"{names[i]} 与 {names[j]} 声音太像"
                               f"（基频 {a['pitch']:.0f}Hz vs {b['pitch']:.0f}Hz，"
                               f"过零率差 {dz*100:.0f}%），角色听感分不清"))"""

new = """    # the exact check first: two characters on one timbre and one shaping
    # sound like one person, however the numbers come out
    by_timbre: dict[tuple, list[str]] = {}
    for c in ctx.project.characters:
        if not c.voice_id:
            continue
        key = (c.voice_id, c.voice_pitch or "", c.voice_rate or "")
        by_timbre.setdefault(key, []).append(c.name)
    for (vid, pit, rate), names in by_timbre.items():
        if len(names) > 1:
            issues.append(("voice", "same_timbre", "-",
                           f"{'、'.join(names)} 用了同一个音色 {vid}"
                           f"（音高 {pit or '默认'} / 语速 {rate or '默认'}），"
                           "听感上分不出是谁"))
    names = list(sigs)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = sigs[names[i]], sigs[names[j]]
            if not a["pitch"] or not b["pitch"]:
                continue
            dp = abs(a["pitch"] - b["pitch"])
            rel = dp / max(a["pitch"], b["pitch"])
            dz = abs(a["zcr"] - b["zcr"]) / max(a["zcr"], b["zcr"], 1.0)
            # six percent of the pitch and a tenth of the brightness: below
            # that two voices are the same voice
            if rel < 0.06 and dz < 0.10:
                issues.append(("voice", "voices_too_similar", "-",
                               f"{names[i]} 与 {names[j]} 声音太像"
                               f"（基频 {a['pitch']:.0f}Hz vs {b['pitch']:.0f}Hz，"
                               f"差 {rel*100:.0f}%，过零率差 {dz*100:.0f}%），"
                               "角色听感分不清"))"""
assert old in s, "音色相似锚点没找到"
s = s.replace(old, new, 1)

# --------------------------------------------------------------------------- #
# 3. the line has to be in the prompt of the shot that carries it
# --------------------------------------------------------------------------- #
old = '''def check_prompt_has_line(ctx, ep, tl, issues):
    """A shot with a line has to ask for it in the prompt.

    Without the dialogue tag the model gets a scene description and
    narrates it - the actions come out as a voice over.
    """
    rows = []
    for ts in tl.shots:
        shot = ts.shot
        if not shot.video_prompt:
            continue
        has_line = any(t.line.kind.value == "dialogue"
                       and ts.start - 0.02 <= t.start < ts.start + ts.duration
                       for t in tl.lines)
        if not has_line:
            continue
        if "<d>" not in shot.video_prompt:
            rows.append({"shot": shot.id,
                         "same_as_picture": shot.video_prompt == (shot.prompt or "")})
    if rows:
        same = sum(1 for r in rows if r["same_as_picture"])
        issues.append(("story", "prompt_without_line", "-",
                       f"{len(rows)} 个镜头的提示词里没有台词标签"
                       f"（其中 {same} 个直接用了出图提示词），"
                       "模型会把动作当旁白念出来"))
    return {"missing": len(rows), "rows": rows[:8]}'''

new = '''def check_prompt_has_line(ctx, ep, tl, issues):
    """A shot with a line has to ask for it in the prompt.

    Without the dialogue tag the model gets a scene description and
    narrates it - the actions come out as a voice over.

    The question is asked of the shot that carries the line: the storyboard
    says which line a shot holds, and that line's own words have to be in
    the prompt, inside the tag.
    """
    rows = []
    for sc in ep.scenes:
        spoken = [l for l in sc.lines if l.kind.value != "narration"]
        for shot in sc.shots:
            if not shot.video_prompt:
                continue
            owned = [spoken[n - 1] for n in (shot.line_indices or [])
                     if 1 <= n <= len(spoken)]
            if not owned:
                continue
            missing = [l for l in owned
                       if not l.text or (l.text not in shot.video_prompt)]
            if not missing:
                continue
            tagged = "<d>" in shot.video_prompt
            rows.append({"shot": shot.id,
                         "lines": [l.text[:14] for l in missing[:3]],
                         "tagged": tagged,
                         "same_as_picture": shot.video_prompt == (shot.prompt or "")})
    if rows:
        same = sum(1 for r in rows if r["same_as_picture"])
        untagged = sum(1 for r in rows if not r["tagged"])
        issues.append(("story", "prompt_without_line", "-",
                       f"{len(rows)} 个镜头的提示词里没有它承载的台词"
                       f"（其中 {untagged} 个连台词标签都没有，"
                       f"{same} 个直接用了出图提示词），"
                       "模型会把动作当旁白念出来"))
    return {"missing": len(rows), "rows": rows[:8]}'''
assert old in s, "台词标签检查锚点没找到"
s = s.replace(old, new, 1)

# --------------------------------------------------------------------------- #
# 4. did the voice get into the picture
# --------------------------------------------------------------------------- #
old = '''    spoken = [t for t in tl.lines if t.line.kind.value == "dialogue"]
    onsets = speech_onsets(path)
    if spoken and len(onsets) < len(spoken) * 0.7:
        issues.append(("completeness", "dialogue_missing", "-",
                       f"应有 {len(spoken)} 句台词，成片里只听到 {len(onsets)} 句"))'''

new = '''    spoken = [t for t in tl.lines if t.line.kind.value == "dialogue"]
    if ctx.cfg.comfyui.native_audio:
        # The picture carries the voice, so the question is whether the shots
        # have a voice in them - the loudness jumps of the finished mix are
        # the music's, not the lines'.
        clips = [ctx.store.abs(sh.video_path) for sc in ep.scenes
                 for sh in sc.shots if sh.video_path]
        with_voice = sum(1 for c in clips if c.exists() and has_voice(c))
        if clips and with_voice < len(clips) * 0.8:
            issues.append(("completeness", "silent_clips", "-",
                           f"{len(clips) - with_voice}/{len(clips)} 个片段没有人声，"
                           "这些镜头的台词观众听不到"))
        onsets = speech_onsets(path)
    else:
        onsets = speech_onsets(path)
        if spoken and len(onsets) < len(spoken) * 0.7:
            issues.append(("completeness", "dialogue_missing", "-",
                           f"应有 {len(spoken)} 句台词，成片里只听到 {len(onsets)} 句"))'''
assert old in s, "成片人声锚点没找到"
s = s.replace(old, new, 1)

# the helper that answers "is there a voice in this file"
old = """def speech_onsets(path, min_jump=6.0, floor=-40.0):"""
new = '''def has_voice(path, floor=-45.0):
    """Does this file carry a voice, or is its audio track empty?

    The maximum level of the track answers it: a clip whose voice was never
    made sits at the noise floor.
    """
    r = ff._run([FF, "-i", str(path), "-af", "volumedetect",
                 "-f", "null", "-"], quiet=True)
    m = re.search(r"max_volume:\\s*(-?[\\d.]+) dB", r.stderr or "")
    if not m:
        return False
    try:
        return float(m.group(1)) > floor
    except ValueError:
        return False


def speech_onsets(path, min_jump=6.0, floor=-40.0):'''
assert old in s, "speech_onsets 锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("qa.py: 四处口径改好了")
