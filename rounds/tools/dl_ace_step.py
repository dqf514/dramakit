"""Fetch the music model, in the background, without disturbing the cards.

The download is the slow part and it uses no GPU at all, so it can run
while the video machine is busy. Three files: the model that makes the
music, the text encoder that reads the brief, and the thing that turns
the result back into sound.

The split version is used rather than the all-in-one checkpoint because
the split one loads through the ordinary loaders, so the same graph
builder that makes the pictures makes the music.
"""
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://hf-mirror.com/Comfy-Org/ACE-Step-1.5/resolve/main/"
ROOT = Path(r"E:\ComfyUI\models")

FILES = [
    ("split_files/diffusion_models/acestep_v1.5_turbo.safetensors",
     ROOT / "diffusion_models" / "acestep_v1.5_turbo.safetensors"),
    ("split_files/text_encoders/qwen_1.7b_ace15.safetensors",
     ROOT / "text_encoders" / "qwen_1.7b_ace15.safetensors"),
    ("split_files/vae/ace_1.5_vae.safetensors",
     ROOT / "vae" / "ace_1.5_vae.safetensors"),
]

LOG = Path(r"C:\Users\David\AppData\Local\Temp\opencode\ace_step_dl.txt")


def note(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


for rel, dest in FILES:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100 * 1024 * 1024:
        note("已有 %s（%.2f GB），跳过" % (dest.name, dest.stat().st_size / 2**30))
        continue
    url = BASE + rel
    tmp = dest.with_suffix(dest.suffix + ".part")
    note("开始 %s" % dest.name)
    t0 = time.time()
    got = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "python-requests/2.31"})
        with urllib.request.urlopen(req, timeout=120) as r:
            total = int(r.headers.get("Content-Length") or 0)
            with tmp.open("wb") as f:
                while True:
                    chunk = r.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    if total and got % (200 * 1024 * 1024) < len(chunk):
                        note("  %s %.1f/%.1f GB" % (dest.name, got / 2**30, total / 2**30))
        tmp.replace(dest)
        note("完成 %s（%.2f GB，%.0f 秒）" % (dest.name, dest.stat().st_size / 2**30, time.time() - t0))
    except Exception as e:  # noqa: BLE001
        note("失败 %s: %s %s" % (dest.name, type(e).__name__, str(e)[:150]))
        sys.exit(1)

note("全部完成")
