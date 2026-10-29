"""What did H3 actually say? Transcribe the generated clip."""
import sys
import wave
from pathlib import Path

import numpy as np

video = Path(sys.argv[1])
wav = video.with_suffix(".wav")
import subprocess
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn",
                "-ac", "1", "-ar", "16000", str(wav)], capture_output=True)

from transformers import (WhisperForConditionalGeneration, WhisperProcessor)

mdir = r"E:\\musetalk\\models\\whisper"
proc = WhisperProcessor.from_pretrained(mdir)
model = WhisperForConditionalGeneration.from_pretrained(mdir)
with wave.open(str(wav), "rb") as w:
    data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
arr = data.astype(np.float32) / 32768.0
feats = proc(arr, sampling_rate=16000, return_tensors="pt")
try:
    ids = model.generate(feats.input_features, language="zh", task="transcribe")
except ValueError:
    # the tiny checkpoint has no language tokens: decode without forcing one
    ids = model.generate(feats.input_features)
print("转写:", proc.batch_decode(ids, skip_special_tokens=True)[0])
print("时长:", round(len(arr) / 16000, 2), "秒")
