"""Transcribe a clip with a proper Chinese ASR."""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from transformers import (WhisperForConditionalGeneration, WhisperProcessor)

video = Path(sys.argv[1])
model_dir = sys.argv[2] if len(sys.argv) > 2 else r"E:\\musetalk\\models\\whisper_small"
wav = video.with_suffix(".wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn",
                "-ac", "1", "-ar", "16000", str(wav)], capture_output=True)

proc = WhisperProcessor.from_pretrained(model_dir)
model = WhisperForConditionalGeneration.from_pretrained(model_dir)
with wave.open(str(wav), "rb") as w:
    data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
arr = data.astype(np.float32) / 32768.0
feats = proc(arr, sampling_rate=16000, return_tensors="pt")
try:
    model.generation_config.language = "zh"
    model.generation_config.task = "transcribe"
    ids = model.generate(feats.input_features, max_new_tokens=120)
except Exception as e:  # noqa: BLE001
    print("generate 出错:", type(e).__name__, str(e)[:120])
    ids = model.generate(feats.input_features, max_new_tokens=120)
print("转写:", proc.batch_decode(ids, skip_special_tokens=True)[0])
print("时长:", round(len(arr) / 16000, 2), "秒")
