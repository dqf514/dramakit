"""Does H3 speak intelligibly - and which weight file ruins it?

The mouth moves but the audio comes out as noise. That is either the
quantization of the transformer (nvfp4 vs w6a8) or the way the prompt is
written (I2VA vs R2V format). This runs the same line through the
combinations.

    python rounds/tools/exp_speech.py 轮次09_09
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

line = None
for sc in ep.scenes:
    for l in sc.lines:
        if l.kind.value == "dialogue" and l.audio_path:
            line = l
            break
    if line:
        break
audio = ctx.store.abs(line.audio_path)
sheet = Path(r"E:\\dramakit\\projects") / name / "characters" / line.speaker / "front.png"
if not sheet.exists():
    sheet = sorted((Path(r"E:\\dramakit\\projects") / name / "characters")
                   .glob("*/front.png"))[0]
print(f"台词 {line.speaker}: 「{line.text}」")

I2VA = ("For the target video, at 0.00 seconds into the target video, "
        "<Picture 1> (from [Shot 1]) is fully referenced.\n\n"
        "integrated_multimodal_description: [Shot 1] A steady medium "
        "close-up of the person in <Picture 1>. They look slightly off "
        "camera, take a breath and begin to speak, the lips moving clearly "
        "and in time with the voice. The room behind stays still, the light "
        "unchanged. (S1) says, <d>[zh-CN]{line.text}</d>\n\n"
        "overall_soundscape: The room tone of the place in <Picture 1> "
        "continues throughout, with the small sounds of the room.\n\n"
        "non_diegetic_music: N/A")


def run(tag: str, workflow: str, unet: str, prompt: str, with_audio: bool):
    import json
    wf = json.load(open(Path(r"E:\\dramakit") / workflow, encoding="utf-8"))
    for nid, node in wf.items():
        if isinstance(node, dict) and node.get("class_type") == "UNETLoader":
            node["inputs"]["unet_name"] = unet
    tmp_wf = Path(r"E:\\dramakit\\config\\comfyui") / f"_tmp_{tag}.json"
    json.dump(wf, open(tmp_wf, "w", encoding="utf-8"), ensure_ascii=False)
    cfg2 = ctx.cfg.comfyui.model_copy(deep=True)
    cfg2.i2v_workflow = f"config/comfyui/{tmp_wf.name}"
    vis.cfg = cfg2
    extra = {}
    if with_audio:
        extra = {"graph_overrides": {"900": {"audio": Path(audio).name,
                                            "upload": "audio"}}}
    out = out_dir / f"{tag}.mp4"
    print(f"--- {tag}: {unet}")
    try:
        vis.generate_video(prompt, "", image_path=str(sheet), frames=56,
                           fps=24, seed=20260201, out_path=str(out),
                           extra=extra)
    except Exception as e:  # noqa: BLE001
        print("   失败:", type(e).__name__, str(e)[:200])
        return
    r = subprocess.run(["E:\\ComfyUI\\venv\\Scripts\\python.exe",
                        r"E:\\dramakit\\rounds\\tools\\transcribe.py", str(out)],
                       capture_output=True, text=True, errors="replace")
    said = ""
    for l in r.stdout.splitlines():
        if l.startswith("转写:"):
            said = l.split(":", 1)[1].strip()
    print(f"   H3 说: 「{said}」  我们要: 「{line.text}」")
    r2 = subprocess.run(["E:\\ComfyUI\\venv\\Scripts\\python.exe",
                         r"E:\\dramakit\\rounds\\tools\\audio_energy.py", str(out)],
                        capture_output=True, text=True, errors="replace")
    rms = [l.strip() for l in r2.stdout.splitlines() if "rms=" in l]
    print("   能量:", " ".join(x.split("rms=")[1].split()[0] for x in rms[:12]))


run("e_fl2va_w6a8", "config/comfyui/i2v_minimax_h3.json",
    "minimax_h3_fl2va_pruned_w6a8.safetensors", I2VA, False)
run("f_fl2va_nvfp4", "config/comfyui/i2v_minimax_h3.json",
    "MiniMax_H3_FL2VA_pruned_nvfp4.safetensors", I2VA, False)
print("DONE")
