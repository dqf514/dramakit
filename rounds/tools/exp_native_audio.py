"""The experiment: let H3 say the line itself.

Picture, mouth and voice in one pass: the picture is the reference picture,
our recorded line is the voice-timbre reference, and H3 speaks the words
with that voice while it moves the lips. Then a speech recognition pass
checks whether the words actually came out.

    python rounds/tools/exp_native_audio.py 轮次09_09
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore

name = sys.argv[1] if len(sys.argv) > 1 else "轮次09_09"
out_dir = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\nat")
out_dir.mkdir(parents=True, exist_ok=True)

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
ctx = Context(cfg, ProjectStore(Path(r"E:\\dramakit\\projects") / name))
ep = ctx.target_episodes()[0]
vis = ctx.providers.visual

# a line with its recording
line = None
for sc in ep.scenes:
    for l in sc.lines:
        if l.kind.value == "dialogue" and l.audio_path:
            line = l
            break
    if line:
        break
if not line:
    raise SystemExit("项目里没有带录音的台词")
audio = ctx.store.abs(line.audio_path)
print(f"台词 {line.speaker}: 「{line.text}」 录音 {audio}")

# a picture of that character: the character sheet, or the last still
name_c = line.speaker
sheet = Path(r"E:\\dramakit\\projects") / name / "characters" / name_c / "front.png"
if not sheet.exists():
    cands = sorted((Path(r"E:\\dramakit\\projects") / name / "characters")
                   .glob("*/front.png"))
    sheet = cands[0] if cands else None
print("参考图:", sheet)

if not sheet or not sheet.exists():
    raise SystemExit("找不到参考图")
pic = sheet

PROMPT = f"""subject_definitions:
<Subject 1> is the person in <Picture 1>, with the face, hair, clothes and the surroundings exactly as shown there.
<Audio 1> is the voice-timbre reference for <Subject 1> (S1), containing a spoken Mandarin vocal layer.

summary:
[reference generation + audio reference] The target video is a single shot in the style and place of <Picture 1>, in which <Subject 1> speaks one line, using the voice timbre referenced from <Audio 1>.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - the face, hair, clothes, the room and the light of <Picture 1> are kept.
<Picture 1> ([Shot 1] composition): fully_preserved - the framing and the blocking of <Picture 1> are kept.
<Audio 1>: reference - the vocal timbre of <Audio 1> guides how <Subject 1> speaks, without copying the original signal.

detailed_description:
[Shot 1] A steady medium close-up of <Subject 1>, exactly as framed in <Picture 1>. The person looks slightly off camera, takes a breath and begins to speak, the lips moving clearly and in time with the voice. The room behind stays still, the light unchanged.
<Subject 1> (S1) speaks, using the clear Mandarin voice timbre referenced from <Audio 1>, saying <d>[zh-CN]{line.text}</d>

overall_soundscape:
The room tone of the place in <Picture 1> continues throughout, with the small sounds of the room.

non_diegetic_music:
N/A"""

cfg2 = ctx.cfg.comfyui.model_copy(deep=True)
cfg2.i2v_workflow = "config/comfyui/i2v_minimax_h3_ref2v_audio.json"
vis.cfg = cfg2

extra = {"graph_overrides": {"900": {"audio": Path(audio).name, "upload": "audio"}}}
frames = 56
out = out_dir / f"native_{name_c}.mp4"
print(f"提交 ref2va（{frames} 帧）...")
vis.generate_video(PROMPT, "", image_path=str(pic), frames=frames, fps=24,
                   seed=20260201, out_path=str(out), extra=extra)
print("  ->", out, out.stat().st_size, "字节")

wav = out.with_suffix(".wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vn",
                "-ac", "1", "-ar", "16000", str(wav)], capture_output=True)
print("转写中 ...")
try:
    import numpy as np
    import torch
    import wave
    from transformers import (WhisperForConditionalGeneration,
                              WhisperProcessor)
    mdir = r"E:\\musetalk\\models\\whisper"
    proc = WhisperProcessor.from_pretrained(mdir)
    model = WhisperForConditionalGeneration.from_pretrained(mdir)
    with wave.open(str(wav), "rb") as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    arr = data.astype(np.float32) / 32768.0
    feats = proc(arr, sampling_rate=16000, return_tensors="pt")
    ids = model.generate(feats.input_features, language="zh", task="transcribe")
    said = proc.batch_decode(ids, skip_special_tokens=True)[0]
    print(f"  H3 说的: 「{said}」")
    print(f"  我们要的: 「{line.text}」")
except Exception as e:  # noqa: BLE001
    print("  转写失败:", type(e).__name__, str(e)[:300])
print("DONE", out_dir)
