"""Can the local card do the video work?

The remote workers are down, and the run needs video. This asks the
local card the only question that matters: does it render a clip, and
how long does it take?

The answer decides the plan, so it is measured rather than guessed:
a short clip first (to find out whether the weights even load), then
the numbers are read off the card's own history.

The weights are the Blackwell-native ones the card can actually hold -
the 4-bit text encoder is too big for 16 GB next to the model, so it
is put on the CPU, which costs time once per clip and nothing per frame.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import ComfyUIConfig          # noqa: E402
from dramakit.providers.comfyui import ComfyUIClient  # noqa: E402

REPO = Path(r"E:\dramakit")
proj = REPO / "projects" / "星际骷髅兵"
out = []

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 25
DEVICE = sys.argv[2] if len(sys.argv) > 2 else "cpu"

cfg = ComfyUIConfig(
    enabled=True,
    base_url="http://127.0.0.1:8188",
    i2v_workflow="config/comfyui/i2v_shortdrama.json",
    video_width=1344,
    video_height=768,
    fps=24,
    frames=FRAMES,
    timeout=3600,
    request_timeout=120,
    poll_interval=2.0,
    use_websocket=True,
    graph_overrides={
        "127": {"unet_name": "MiniMax_H3_Ref2VA_pruned_nvfp4.safetensors"},
        "128": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
                "device": DEVICE},
        "119": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"},
    },
)

client = ComfyUIClient(cfg, REPO)

# the pieces a real shot uses: the frame, the character's sheet, the room
img = sorted((proj / "images").glob("shot_*.png"))
img = img[0] if img else None
four = sorted((proj / "characters").rglob("four.png"))
four = four[0] if four else None
voice = sorted((proj / "characters").rglob("voice.mp3"))
voice = voice[0] if voice else None

out.append(f"=== 素材 ===")
out.append(f"  首帧: {img}")
out.append(f"  四视图: {four}")
out.append(f"  配音: {voice}")

raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
prompt = ""
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            if sh.get("video_prompt"):
                prompt = sh["video_prompt"]
                break
        if prompt:
            break
    if prompt:
        break
out.append(f"  提示词: {prompt[:140]}")

extra = {}
if four:
    extra["ref_pictures"] = [str(four)]
if voice:
    extra["ref_audio_path"] = str(voice)
    extra["ref_audio_node"] = "161"

dest = Path(r"C:\Users\David\AppData\Local\Temp\opencode\local_h3_test.mp4")
t0 = time.time()
try:
    client.generate_video(
        prompt=prompt, negative="",
        image_path=str(img) if img else "",
        frames=FRAMES, fps=24, seed=12345,
        out_path=str(dest), extra=extra)
    dt = time.time() - t0
    out.append("")
    out.append(f"=== 成功：{dt:.0f} 秒 = {dt/60:.1f} 分 ===")
    out.append(f"  {dt/FRAMES:.2f} 秒/帧")
    if dest.exists():
        out.append(f"  产物 {dest.stat().st_size/1024:.0f} KB")
except Exception as e:  # noqa: BLE001
    out.append("")
    out.append(f"=== 失败：{type(e).__name__}: {str(e)[:600]} ===")
    out.append(f"  用时 {time.time()-t0:.0f} 秒")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\local_h3.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("\n".join(out))
