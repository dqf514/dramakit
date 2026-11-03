"""One real render, to prove the settings reach the card.

Everything up to here was checked by reading: the node ids, the field
names, the card's own validation. None of that shows whether the prompt
actually arrives at the model, whether the size the config asks for is the
size the sampler takes, or whether a character's recording reaches the
voice input - each of those fails silently, leaving the placeholder in
place and rendering whatever the file already held.

So: one shot, with the inputs the pipeline would send - a first frame, the
character's face and turnaround, the line the character was recorded
saying - at the shortest length the model accepts, so it costs minutes
rather than a full episode.

The result is checked rather than eyeballed: the container's real
resolution, its duration, and whether it carries a sound track at all.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.providers.comfyui import build_visual  # noqa: E402

out = []
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))

# the character: face and turnaround, as the reference is meant to be built
chars = raw.get("characters") or []
who = next((c for c in chars if isinstance(c, dict) and c.get("voice_ref")), chars[0])
name = who.get("name")
refs = [proj / p for p in (who.get("ref_images") or [])]
refs = [p for p in refs if p.exists()]
voice = proj / who["voice_ref"] if who.get("voice_ref") else None
voice = voice if voice and voice.exists() else None

# the first frame: a shot that already has one
frames_imgs = sorted((proj / "images").glob("*.png"))
first = frames_imgs[0] if frames_imgs else None

out.append(f"角色: {name}")
out.append(f"  参考图 {len(refs)} 张: {[p.name for p in refs]}")
out.append(f"  配音: {voice.relative_to(proj) if voice else '无'} "
           f"({voice.stat().st_size/1024:.0f} KB)" if voice else "  配音: 无")
out.append(f"  首帧: {first.relative_to(proj) if first else '无'}")

# a line in the shape the pipeline writes: English scene, Chinese dialogue
PROMPT = (
    "A moonlit stone courtyard in an ancient fantasy city, cold blue light "
    "on wet flagstones, lanterns swaying. <d>[zh-CN]师父说过，剑要快，心要更静。</d> "
    "The young disciple lowers the blade and looks up, breath visible in "
    "the cold air, camera slowly pushing in on the face."
)

cfg = Config.load(Config.discover())
# The workflow is for the 3090, and the card's own node set is what decides
# whether a graph is accepted - the local machine does not have the
# attention patch the file uses. So the client is pointed at the card the
# workflow was built for, which is where the pipeline's node pool routes it.
cfg.comfyui.base_url = "http://192.168.31.7:8188"
vis = build_visual(cfg.comfyui, root=Path(r"E:\dramakit"))
if vis is None:
    out.append("!! build_visual 返回 None（comfyui.enabled=false）")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\render_test.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

out.append(f"  客户端 base = {vis.base}")
out.append(f"  workflow = {cfg.comfyui.i2v_workflow}")
out.append(f"  ref_audio_node = {cfg.comfyui.ref_audio_node}")

# the shortest length the model takes: 17k+5 -> 22
FRAMES = 22
dest = proj / "_render_test" / "probe.mp4"
dest.parent.mkdir(parents=True, exist_ok=True)

extra = {"ref_pictures": [str(p) for p in refs[:3]]}
if voice:
    extra["ref_audio_path"] = str(voice)
    extra["ref_audio_node"] = cfg.comfyui.ref_audio_node

out.append("")
out.append(f"=== 开始渲染（{FRAMES} 帧 @24fps，1344x768）===")
t0 = time.time()
try:
    path = vis.generate_video(
        prompt=PROMPT, negative="",
        image_path=str(first) if first else "",
        frames=FRAMES, fps=24, seed=12345,
        out_path=str(dest), extra=extra)
    dt = time.time() - t0
    out.append(f"  完成 {dt:.1f}s -> {path}")
except Exception as e:  # noqa: BLE001
    dt = time.time() - t0
    out.append(f"  **失败** {dt:.1f}s: {type(e).__name__}: {e}")
    path = ""

Path(r"C:\Users\David\AppData\Local\Temp\opencode\render_test.txt").write_text(
    "\n".join(out), encoding="utf-8")

# --- what the file really is -------------------------------------------
if path and Path(path).exists():
    probe = []
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,r_frame_rate,duration,channels",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60)
        info = json.loads(r.stdout or "{}")
        for s in info.get("streams", []):
            probe.append("  " + json.dumps(s, ensure_ascii=False))
    except FileNotFoundError:
        probe.append("  ffprobe 不可用，用文件大小判断")
    except Exception as e:  # noqa: BLE001
        probe.append(f"  ffprobe 失败: {e}")
    probe.append(f"  文件大小 {Path(path).stat().st_size/1024:.0f} KB")

    with open(r"C:\Users\David\AppData\Local\Temp\opencode\render_test.txt",
              "a", encoding="utf-8") as f:
        f.write("\n\n=== 输出文件实况 ===\n" + "\n".join(probe))

print("wrote")
