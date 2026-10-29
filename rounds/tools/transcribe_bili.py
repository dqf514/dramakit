"""Transcribe the tutorial so the techniques can be read."""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

video = Path(sys.argv[1])
out_txt = video.with_suffix(".txt")
model_dir = sys.argv[2] if len(sys.argv) > 2 else r"E:\\musetalk\\models\\whisper_small"
wav = video.with_suffix(".wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn",
                "-ac", "1", "-ar", "16000", "-af", "highpass=f=100",
                str(wav)], capture_output=True)

from transformers import WhisperForConditionalGeneration, WhisperProcessor
proc = WhisperProcessor.from_pretrained(model_dir)
model = WhisperForConditionalGeneration.from_pretrained(model_dir)

with wave.open(str(wav), "rb") as w:
    raw = w.readframes(w.getnframes())
arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

chunks = []
step = 20 * 16000
for i in range(0, len(arr), step):
    seg = arr[i:i + step]
    if len(seg) < 16000:
        break
    feats = proc(seg, sampling_rate=16000, return_tensors="pt")
    ids = model.generate(feats.input_features, max_new_tokens=180)
    txt = proc.batch_decode(ids, skip_special_tokens=True)[0].strip()
    if txt:
        chunks.append(f"[{i//16000:5d}s] {txt}")
    print(f"  {i//16000:5d}s {txt[:60]}")

out_txt.write_text("\n".join(chunks), encoding="utf-8")
print("写到", out_txt)
