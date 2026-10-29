"""The native audio path needs two small adjustments.

- The clip must not carry music: the score comes from its own music-only
  clip, and two beds would fight.
- The lip-sync step must be skipped: H3's mouth already moves with the
  voice it generated itself. Running MuseTalk over it would redraw the
  mouth to the recording, and the lips would then be out of step with the
  voice that is actually in the episode.
"""
from pathlib import Path

# 1) the prompt: no music in the clip
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")
old = """            if ctx.cfg.comfyui.native_audio:
                shot.video_prompt = _assemble_r2v_prompt(
                    desc, soundscape or "N/A", music or "N/A")"""
new = """            if ctx.cfg.comfyui.native_audio:
                # the score has its own music-only clip; the shot clip
                # carries the voice and the room
                shot.video_prompt = _assemble_r2v_prompt(
                    desc, soundscape or "N/A", "N/A")"""
assert old in s, "R2V 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py 已改（片段里不出配乐）")

# 2) the lip-sync step: not needed when the model speaks itself
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\lipsync.py")
s = p.read_text(encoding="utf-8")
old = """    cfg = ctx.cfg.compose
    if not cfg.lipsync:
        return {"skipped": True}"""
new = """    cfg = ctx.cfg.compose
    if not cfg.lipsync:
        return {"skipped": True}
    if ctx.cfg.comfyui.native_audio:
        # the mouth already moves with the voice the model generated; a
        # second pass would put the lips out of step with the sound
        ctx.log.info("lipsync: 跳过（画面里的人声是 H3 自己说的，嘴本来就对上了）")
        return {"skipped": True}"""
assert old in s, "lipsync 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("lipsync.py 已改（原生音频路径跳过）")
