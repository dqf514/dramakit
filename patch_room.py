"""Give the voice a room to be in.

The voices were recorded dry and laid straight over the picture, and a dry
voice over a room sounds like it is floating outside the frame. A little
of the room on the voice is what puts the person inside the picture.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\media\\ffmpeg.py")
s = p.read_text(encoding="utf-8")

old = """def mix_voice_bgm(voice: str | Path, bgm: Optional[str | Path], out: str | Path, *,
                  bgm_volume: float = 0.22, duck: bool = True,
                  target_lufs: Optional[float] = None) -> str:"""
new = """def mix_voice_bgm(voice: str | Path, bgm: Optional[str | Path], out: str | Path, *,
                  bgm_volume: float = 0.22, duck: bool = True,
                  target_lufs: Optional[float] = None,
                  room: float = 0.0) -> str:"""
assert old in s, "签名锚点没找到"
s = s.replace(old, new, 1)

old = """    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    has_bgm = bool(bgm and Path(bgm).exists())
    if not has_bgm:
        _run([ffmpeg_bin(), "-y", "-i", str(voice),
              "-af", "aresample=44100", "-c:a", "libmp3lame", "-q:a", "3", str(out)],
             quiet=False)
        return str(out)"""
new = """    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    has_bgm = bool(bgm and Path(bgm).exists())
    # a voice with a little room on it: two short echoes, one for the walls
    # and one for the floor, well under the direct sound
    room_af = ""
    if room and room > 0:
        wet = min(max(room, 0.0), 0.5)
        room_af = (f"aecho=0.8:0.9:38|71:0.35|0.22,"
                   f"aeval=0|0:{wet}|{wet},")
    if not has_bgm:
        _run([ffmpeg_bin(), "-y", "-i", str(voice),
              "-af", room_af + "aresample=44100",
              "-c:a", "libmp3lame", "-q:a", "3", str(out)], quiet=False)
        return str(out)"""
assert old in s, "混音锚点没找到"
s = s.replace(old, new, 1)

old = """        fc = (f"[0:a]asplit=2[v][sc];"
              f"[1:a]volume={bgm_volume}[b];"
              f"[b][sc]sidechaincompress=threshold=0.05:ratio=9:attack=15:release=280[bg];"
              f"[v][bg]amix=inputs=2:duration=first:dropout_transition=0,"
              f"aresample=44100[a]")
    else:
        fc = (f"[1:a]volume={bgm_volume}[b];"
              f"[0:a][b]amix=inputs=2:duration=first:dropout_transition=0,"
              f"aresample=44100[a]")"""
new = """        fc = (f"[0:a]{room_af}asplit=2[v][sc];"
              f"[1:a]volume={bgm_volume}[b];"
              f"[b][sc]sidechaincompress=threshold=0.05:ratio=9:attack=15:release=280[bg];"
              f"[v][bg]amix=inputs=2:duration=first:dropout_transition=0,"
              f"aresample=44100[a]")
    else:
        fc = (f"[0:a]{room_af}[v];"
              f"[1:a]volume={bgm_volume}[b];"
              f"[v][b]amix=inputs=2:duration=first:dropout_transition=0,"
              f"aresample=44100[a]")"""
assert old in s, "滤镜图锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("ffmpeg.py 已改（给声音加房间）")

# the config
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    lipsync: bool = False"""
new = """    # 台词上一点房间混响：干声铺在画面上会像飘在外面
    voice_room: float = 0.14
    lipsync: bool = False"""
assert old in s, "config 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py 已改")

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = """  lipsync: false                           # 打开后每个有台词的镜头都会过一遍 MuseTalk"""
new = """  voice_room: 0.14                         # 台词上的房间混响（0=干声）
  lipsync: false                           # 打开后每个有台词的镜头都会过一遍 MuseTalk"""
assert old in s, "yaml 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml 已改")

# the compose stage passes it
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\compose.py")
s = p.read_text(encoding="utf-8")
old = """    ff.mix_voice_bgm(voice, music or None, mix,
                     bgm_volume=1.0,
                     duck=ctx.cfg.music.duck_voice, target_lufs=target)"""
new = """    ff.mix_voice_bgm(voice, music or None, mix,
                     bgm_volume=1.0,
                     duck=ctx.cfg.music.duck_voice, target_lufs=target,
                     room=float(cc.voice_room or 0))"""
assert old in s, "compose 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("compose.py 已改")
