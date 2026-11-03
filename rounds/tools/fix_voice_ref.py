"""The voice a character speaks with, taken from the character.

_reference_audio built the reference from the first episode's timeline and
searched it for the shot - so a shot in episode four was not found, and
every clip after the first went out with no timbre at all. It also used
the shot's own line, which meant the voice stage had to finish before any
picture could start, and a shot with nobody speaking had nothing.

Now the reference comes from the character. Each one has a sample recorded
at 定妆, and whoever speaks in this shot hands theirs over - so the voice
is theirs rather than a line's, the picture machine does not wait for the
voice machine, and the search through a timeline it does not have to do
is gone. The shot's own recording remains as the fallback, for a shot
whose speaker has no sample yet.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py")
s = p.read_text(encoding="utf-8")

if "_speakers_voice_refs" in s:
    print("visual.py: 已改，跳过")
    raise SystemExit(0)

# ------------------------------------ 1. who speaks, and their samples ----
old_fn = s[s.find("def _reference_audio("):s.find("\ndef ", s.find("def _reference_audio(") + 10)]
assert old_fn.startswith("def _reference_audio"), "找不到 _reference_audio"

new_fn = '''def _speakers_voice_refs(ctx: Context, sc, shot: Shot) -> list[str]:
    """The recorded voice of whoever speaks in this shot, up to three.

    The model takes three audio references and speaks each line in the
    timbre it is given, so the right recording is the one belonging to the
    person whose line it is - not whichever line happened to be first in
    the scene. A speaker with no sample falls through to the shot's own
    recording.
    """
    out: list[str] = []
    seen: set[str] = set()
    for idx in (shot.line_indices or []):
        if idx < 1 or idx > len(sc.lines):
            continue
        line = sc.lines[idx - 1]
        speaker = (line.speaker or "").strip()
        if not speaker or speaker in seen:
            continue
        seen.add(speaker)
        char = ctx.project.character(speaker)
        ref = getattr(char, "voice_ref", "") if char else ""
        if not ref:
            continue
        path = ctx.store.abs(ref)
        if path.exists() and path.stat().st_size > 0:
            out.append(str(path))
        if len(out) >= 3:
            break
    return out


def _reference_audio(ctx: Context, shot: Shot, sc=None, ep=None) -> str:
    """The recording of this shot's line, as the voice reference.

    H3 speaks the words itself, but it takes the timbre from this
    recording - so the character sounds the same in every shot. This is
    the fallback for a speaker without a recorded sample: the line's own
    audio, cut to where the shot sits on the timeline.
    """
    from .lipsync import _scene_wav
    # The shot is looked for in the episode it belongs to. Searching the
    # first episode's timeline meant a shot in episode four was never
    # found, and every clip after the first went out without a voice.
    eps = [ep] if ep is not None else ctx.target_episodes()
    for one in eps:
        tl = ctx.timeline(one)
        for tsc in tl.scenes:
            for ts in tsc.shots:
                if ts.shot.id != shot.id:
                    continue
                placed = []
                for t in tsc.lines:
                    if t.line.kind.value != "dialogue":
                        continue
                    if not (ts.start - 0.02 <= t.start < ts.start + ts.duration):
                        continue
                    if not t.line.audio_path:
                        continue
                    placed.append((t.start - tsc.start,
                                   ctx.store.abs(t.line.audio_path)))
                if not placed:
                    return ""
                out = ctx.store.root / "tmp" / f"refaudio_{shot.id}.wav"
                if _scene_wav(placed, ts.start - tsc.start, ts.duration, out):
                    return str(out)
    return ""


'''
s = s.replace(old_fn, new_fn, 1)

# ------------------------------------ 2. the call site prefers the cast ----
old_extra = '''    ref = _reference_audio(ctx, shot)'''
new_extra = '''    # Whoever speaks hands over their own recording; a speaker without one
    # falls back to the shot's own line, which is what this used to be.
    voices = _speakers_voice_refs(ctx, sc, shot)
    ref = voices[0] if voices else _reference_audio(ctx, shot, sc, ep)'''
assert old_extra in s, "ref 赋值锚点没找到"
s = s.replace(old_extra, new_extra, 1)

# ------------------------------------ 3. the episode must be passed in ----
old_sig = '''def _gen_video(ctx: Context, sc, shot: Shot, duration: float = 0.0) -> tuple[str, bool, str]:'''
new_sig = '''def _gen_video(ctx: Context, sc, shot: Shot, duration: float = 0.0,
               ep=None) -> tuple[str, bool, str]:'''
assert old_sig in s, "_gen_video 签名锚点没找到"
s = s.replace(old_sig, new_sig, 1)

# the phase runner discards the episode; it is needed to find the shot
old_sub = '''            futs = [ex.submit(fn, ctx, sc, shot, durations.get(shot.id, 0.0))
                    if fn is _gen_video else ex.submit(fn, ctx, sc, shot)
                    for (_ep, sc, shot) in jobs]'''
new_sub = '''            futs = [ex.submit(fn, ctx, sc, shot, durations.get(shot.id, 0.0), _ep)
                    if fn is _gen_video else ex.submit(fn, ctx, sc, shot)
                    for (_ep, sc, shot) in jobs]'''
assert old_sub in s, "submit 锚点没找到"
s = s.replace(old_sub, new_sub, 1)

# and the two direct calls at the bottom of the stage
s = s.replace('''        _sid, ok, msg = _gen_video(ctx, sc, shot, dur)''',
              '''        _sid, ok, msg = _gen_video(ctx, sc, shot, dur, _ep)''')

p.write_text(s, encoding="utf-8")
print("visual.py: 声音参考来自角色，且能在任意一集找到镜头")
