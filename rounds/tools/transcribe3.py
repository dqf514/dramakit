"""Transcribe the voice band only - the room is loud enough to hide it."""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

video = Path(sys.argv[1])
model_dir = sys.argv[2] if len(sys.argv) > 2 else r"E:\\musetalk\\models\\whisper_small"
wav = video.with_suffix(".wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn",
                "-ac", "1", "-ar", "16000", str(wav)], capture_output=True)

from transformers import WhisperForConditionalGeneration, WhisperProcessor
proc = WhisperProcessor.from_pretrained(model_dir)
model = WhisperForConditionalGeneration.from_pretrained(model_dir)

with wave.open(str(wav), "rb") as w:
    raw = w.readframes(w.getnframes())
arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

variants = {
    "原样": arr,
    "人声频段": None,   # filled below
}
# the voice band, and a compressor to lift it over the room
clean = Path(r"C:\\Users\\David\\AppData\\Local\\Temp\\opencode\\voiceband.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav),
                "-af", "highpass=f=180,lowpass=f=3800,"
                       "acompressor=threshold=-28dB:ratio=6:attack=5:release=120,"
                       "dynaudnorm=f=200:g=5",
                "-ac", "1", "-ar", "16000", str(clean)], capture_output=True)
with wave.open(str(clean), "rb") as w:
    variants["人声频段"] = np.frombuffer(w.readframes(w.getnframes()),
                                        dtype=np.int16).astype(np.float32) / 32768.0

for tag, a in variants.items():
    if a is None or len(a) == 0:
        continue
    feats = proc(a, sampling_rate=16000, return_tensors="pt")
    ids = model.generate(feats.input_features, max_new_tokens=120)
    print(f"{tag}: {proc.batch_decode(ids, skip_special_tokens=True)[0]}")
