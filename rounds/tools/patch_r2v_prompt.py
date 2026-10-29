"""The full-reference prompt, and the voice that goes with it.

The reference-to-video model writes its prompt in six sections: what the
references are, what the video is, how the references are kept, the shots
themselves, the room sound and the score. The model we already have for
the picture writes the shots; this wraps them in the rest.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")

# 1) the skeleton
old = """def _assemble_h3_prompt(desc: str, soundscape: str, music: str) -> str:"""
new = '''R2V_HEADER = ("subject_definitions:\\n"
              "<Subject 1> is the person in <Picture 1>, with the face, hair, "
              "clothes and the surroundings exactly as shown there.\\n"
              "<Audio 1> is the voice-timbre reference for <Subject 1> (S1), "
              "containing a spoken Mandarin vocal layer.\\n\\n"
              "summary:\\n"
              "[reference generation + audio reference] The target video is a "
              "single shot in the style and place of <Picture 1>, in which "
              "<Subject 1> speaks, using the voice timbre referenced from "
              "<Audio 1>.\\n\\n"
              "retention_analysis:\\n"
              "<Subject 1> (appears in [Shot 1]): fully_preserved - the face, "
              "hair, clothes, the room and the light of <Picture 1> are kept.\\n"
              "<Picture 1> ([Shot 1] composition): fully_preserved - the "
              "framing and the blocking of <Picture 1> are kept.\\n"
              "<Audio 1>: reference - the vocal timbre of <Audio 1> guides how "
              "<Subject 1> speaks, without copying the original signal.\\n\\n"
              "detailed_description:\\n")


def _assemble_r2v_prompt(desc: str, soundscape: str, music: str) -> str:
    """The full-reference format, for the model that speaks."""
    return "\\n".join([
        R2V_HEADER,
        desc.strip(),
        "",
        f"overall_soundscape: {soundscape or 'N/A'}",
        "",
        f"non_diegetic_music: {music or 'N/A'}",
    ])


def _assemble_h3_prompt(desc: str, soundscape: str, music: str) -> str:'''
assert old in s, "骨架锚点没找到"
s = s.replace(old, new, 1)

# 2) the generator: the reference workflow writes the full-reference format
old = """        shot.video_prompt = (_assemble_h3_prompt(desc, soundscape or "N/A", music or "N/A")
                             if desc else _fallback_h3_prompt(ctx, shot, sc, lines))"""
new = """        if desc:
            if ctx.cfg.comfyui.native_audio:
                shot.video_prompt = _assemble_r2v_prompt(
                    desc, soundscape or "N/A", music or "N/A")
            else:
                shot.video_prompt = _assemble_h3_prompt(
                    desc, soundscape or "N/A", music or "N/A")
        else:
            shot.video_prompt = _fallback_h3_prompt(ctx, shot, sc, lines)"""
assert old in s, "生成锚点没找到"
s = s.replace(old, new, 1)

# 3) the note: with the native path the model has to say the line itself
old = """        spk_note = _speaker_note(shot, lines)
        if ctx.cfg.compose.h3_audio == "bed":"""
new = """        spk_note = _speaker_note(shot, lines)
        if ctx.cfg.comfyui.native_audio:
            # the model says the line itself: the words go in the prompt and
            # the voice comes from the reference recording
            dlg_text, _ids = _numbered_dialogue(lines)
            note = ("本镜的台词**由 H3 自己在这一镜里说出来**：台词原样用 "
                    "<d>[zh-CN]...</d> 包住，放在描述里角色说话的那一句后面。"
                    "声音参考 <Audio 1>：角色的音色、用词习惯和情绪照着它，"
                    "但不要把录音里的原话重复进 <d>。"
                    "说话的人要开口，嘴型跟声音对上；其他人闭嘴只听。"
                    "overall_soundscape 写环境声和动作声，不要写人声。")
        elif ctx.cfg.compose.h3_audio == "bed":"""
assert old in s, "note 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py 已改（R2V 提示词）")
