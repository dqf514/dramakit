"""The music graph: one model that writes the score for a scene.

The pictures and the video are made by ComfyUI, so the music is too -
that way the pipeline has one door to the cards and one place where the
weights live.

The graph is the one ComfyUI ships for ACE-Step 1.5, flattened into the
API shape the rest of the workflows use: a text encoder that turns a
brief into a plan, a diffusion model that turns the plan into sound, and
the decoder that turns the sound back into a waveform.

Everything that changes from one track to the next - the brief, the
length, the tempo, the key - is written into the graph by the caller
before it is submitted, so the same file makes every track.
"""
import json
from pathlib import Path

# node id -> the settings that make one track
FIELDS = {
    "tags": "5",
    "lyrics": "5",
    "seed": "5",
    "bpm": "5",
    "duration": "5",
    "timesignature": "5",
    "language": "5",
    "keyscale": "5",
    "cfg_scale": "5",
    "temperature": "5",
    "top_p": "5",
    "top_k": "5",
    "min_p": "5",
    "seconds": "7",
    "steps": "8",
    "seed_ksampler": "8",
    "shift": "4",
    "filename_prefix": "10",
    "clip_name1": "1",
    "clip_name2": "1",
    "unet_name": "3",
    "vae_name": "2",
}

GRAPH = {
    "1": {"class_type": "DualCLIPLoader", "inputs": {
        "clip_name1": "qwen_0.6b_ace15.safetensors",
        "clip_name2": "qwen_1.7b_ace15.safetensors",
        "type": "ace", "device": "default"}},
    "2": {"class_type": "VAELoader", "inputs": {
        "vae_name": "ace_1.5_vae.safetensors"}},
    "3": {"class_type": "UNETLoader", "inputs": {
        "unet_name": "acestep_v1.5_turbo.safetensors", "weight_dtype": "default"}},
    "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {
        "model": ["3", 0], "shift": 3}},
    "5": {"class_type": "TextEncodeAceStepAudio1.5", "inputs": {
        "clip": ["1", 0],
        "tags": "cinematic underscore, instrumental, no vocals",
        "lyrics": "",
        "seed": 0,
        "bpm": 90,
        "duration": 60.0,
        "timesignature": "4",
        "language": "en",
        "keyscale": "C major",
        "generate_audio_codes": True,
        "cfg_scale": 2.0,
        "temperature": 0.85,
        "top_p": 0.9,
        "top_k": 0,
        "min_p": 0.0}},
    "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
    "7": {"class_type": "EmptyAceStep1.5LatentAudio", "inputs": {
        "seconds": 60.0, "batch_size": 1}},
    "8": {"class_type": "KSampler", "inputs": {
        "model": ["4", 0], "seed": 0, "steps": 8, "cfg": 1.0,
        "sampler_name": "euler", "scheduler": "simple",
        "positive": ["5", 0], "negative": ["6", 0],
        "latent_image": ["7", 0], "denoise": 1.0}},
    "9": {"class_type": "VAEDecodeAudio", "inputs": {
        "samples": ["8", 0], "vae": ["2", 0]}},
    "10": {"class_type": "SaveAudio", "inputs": {
        "audio": ["9", 0], "filename_prefix": "music/track"}},
}


def build(tags: str, *, seconds: float = 60.0, seed: int = 0,
          bpm: int = 90, key: str = "C major",
          language: str = "en", lyrics: str = "") -> dict:
    """A copy of the graph with one track's settings written in."""
    g = json.loads(json.dumps(GRAPH))
    g["5"]["inputs"]["tags"] = tags
    g["5"]["inputs"]["lyrics"] = lyrics
    g["5"]["inputs"]["seed"] = seed
    g["5"]["inputs"]["bpm"] = bpm
    g["5"]["inputs"]["duration"] = seconds
    g["5"]["inputs"]["language"] = language
    g["5"]["inputs"]["keyscale"] = key
    g["7"]["inputs"]["seconds"] = seconds
    g["8"]["inputs"]["seed"] = seed
    g["10"]["inputs"]["filename_prefix"] = "music/track"
    return g


if __name__ == "__main__":
    dest = Path(r"E:\dramakit\config\comfyui\music_acestep.json")
    dest.write_text(json.dumps(GRAPH, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print("wrote", dest)
