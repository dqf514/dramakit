"""A voice for each character, made once, used for every clip.

The video model speaks the words itself and takes the timbre from a
recording, so a character sounds the same in every shot only if the same
recording is handed over every time. That recording was the shot's own
line - which meant the voice stage had to finish before any video could
start, and a shot with no dialogue had no voice at all.

So the sample is made where the rest of the character is made. The stage
that draws the face also records the voice, once, with the voice already
assigned to that character; every clip they speak in afterwards refers to
it. Two things follow: the timbre stops depending on which line happened
to be spoken first, and the picture machine no longer waits for the
voice machine - the two can run together.

A short neutral sentence, the same for everyone, so two voices are
comparable rather than two different scripts being mistaken for two
different people.
"""
from pathlib import Path

# the same sentence for every character: what is being compared is the
# voice, so the words have to be the same or the difference is the script
VOICE_SAMPLE = ("这是角色的声音样本。用你平时说话的语气，"
                "自然地把这句话读出来，语速适中，情绪平稳。")

# --------------------------------------------------- 1. the field --------
m = Path(r"E:\\dramakit\\dramakit\\models.py")
t = m.read_text(encoding="utf-8")
if "voice_ref:" not in t:
    old = '    voice_rate: str = ""'
    new = '''    voice_rate: str = ""
    # A recording of this character's voice, made once at定妆 and used as
    # the audio reference for every clip they speak in - so the timbre is
    # theirs rather than whatever the model invents per shot.
    voice_ref: str = ""'''
    assert old in t, "voice_rate 字段锚点没找到"
    t = t.replace(old, new, 1)
    m.write_text(t, encoding="utf-8")
    print("models.py: Character.voice_ref 字段")

# ------------------------------------------------ 2. the path helper -----
pr = Path(r"E:\\dramakit\\dramakit\\project.py")
u = pr.read_text(encoding="utf-8")
if "character_voice_path" not in u:
    anchor = "    def character_dir(self, name: str"
    i = u.find(anchor)
    assert i > 0, "character_dir 锚点没找到"
    add = '''    def character_voice_path(self, name: str, ext: str = "mp3") -> Path:
        """Where a character's voice sample lives, beside their pictures.

        The sample is made with the rest of the character, so it sits with
        the rest of the character - and, like the pictures, it is per
        season, because a look that changed may have a voice that did not.
        """
        return self.character_dir(name) / f"voice.{ext}"

'''
    # insert before character_dir, keeping its decorator/docstring intact
    j = u.rfind("\n", 0, i)
    u = u[:j + 1] + add + u[j + 1:]
    pr.write_text(u, encoding="utf-8")
    print("project.py: character_voice_path")

# --------------------------------- 3. generate them at 定妆 time ---------
c = Path(r"E:\\dramakit\\dramakit\\pipeline\\character.py")
v = c.read_text(encoding="utf-8")
if "generate_voice_refs" not in v:
    anchor = "def generate_refs(ctx: Context, c: Character"
    i = v.find(anchor)
    assert i > 0, "generate_refs 锚点没找到"
    fn = '''def generate_voice_refs(ctx: Context, chars: list[Character]) -> int:
    """Record one sample of each character's voice, once.

    The video model speaks the words and takes the timbre from a recording,
    so a character is only consistent across clips if the same recording is
    handed over every time. Made here, with the rest of the character, so
    the picture machine never has to wait for the voice machine to start.

    Never raises: a voice that cannot be recorded is a voice without a
    sample, and the shot falls back to its own line rather than failing
    the stage.
    """
    tts = ctx.providers.tts
    if tts is None:
        ctx.log.info("character: 没有 TTS，跳过声音样本")
        return 0
    made = 0
    for c in chars:
        if not c.voice_id:
            continue
        out = ctx.store.character_voice_path(c.name)
        if c.voice_ref and ctx.store.abs(c.voice_ref).exists():
            continue
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            tts.synthesize(VOICE_SAMPLE, c.voice_id, str(out))
            if out.exists() and out.stat().st_size > 0:
                c.voice_ref = ctx.store.rel(out)
                made += 1
                ctx.log.info("character: %s 声音样本已生成", c.name)
            else:
                ctx.log.warning("character: %s 声音样本是空的", c.name)
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("character: %s 声音样本失败: %s", c.name, str(e)[:120])
    return made


'''
    v = v[:i] + fn + v[i:]
    c.write_text(v, encoding="utf-8")
    print("character.py: generate_voice_refs")

# and call it from run(), right after the voices are cast
v = c.read_text(encoding="utf-8")
old_run = '''    casted = cast_voices(ctx, chars)'''
new_run = '''    casted = cast_voices(ctx, chars)
    # a sample of each voice, so the picture machine can start without
    # waiting for the voice machine to finish its lines
    voice_refs = generate_voice_refs(ctx, chars)'''
if old_run in v and "voice_refs = generate_voice_refs" not in v:
    v = v.replace(old_run, new_run, 1)
    # and include it in what the stage reports
    v = v.replace(
        '''    ctx.log.info("character: 第%d季 %d 个角色，锚点补齐 %d，选角 %d，参考图 %d，场景参考图 %d",
                 ctx.season_index, len(chars), anchors, casted, refs, loc_refs)''',
        '''    ctx.log.info("character: 第%d季 %d 个角色，锚点补齐 %d，选角 %d，参考图 %d，"
                 "场景参考图 %d，声音样本 %d",
                 ctx.season_index, len(chars), anchors, casted, refs, loc_refs,
                 voice_refs)''', 1)
    c.write_text(v, encoding="utf-8")
    print("character.py: run() 里调用并汇报")
else:
    print("character.py: run() 调用锚点没找到（跳过）")
