"""Can H3 speak the line? A small matrix of variations.

    python rounds/tools/exp_matrix.py 轮次09_09
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
print(f"台词 {line.speaker}: 「{line.text}」  参考图 {sheet.name}")

DESC = ("[Shot 1] A steady medium close-up of <Subject 1>, exactly as framed "
        "in <Picture 1>. The person looks slightly off camera, takes a breath "
        "and begins to speak, the lips moving clearly and in time with the "
        "voice. The room behind stays still, the light unchanged.")


def prompt(with_audio: bool) -> str:
    subs = ["<Subject 1> is the person in <Picture 1>, with the face, hair, "
            "clothes and the surroundings exactly as shown there."]
    if with_audio:
        subs.append("<Audio 1> is the voice-timbre reference for <Subject 1> "
                     "(S1), containing a spoken Mandarin vocal layer.")
    s = "subject_definitions:\n" + "\n".join(subs) + "\n\n"
    s += ("summary:\n[reference generation"
          + (" + audio reference" if with_audio else "")
          + "] The target video is a single shot in the style and place of "
            "<Picture 1>, in which <Subject 1> speaks one line.\n\n")
    s += ("retention_analysis:\n"
          "<Subject 1> (appears in [Shot 1]): fully_preserved - the face, "
          "hair, clothes, the room and the light of <Picture 1> are kept.\n"
          "<Picture 1> ([Shot 1] composition): fully_preserved - the framing "
          "and the blocking of <Picture 1> are kept.\n")
    if with_audio:
        s += ("<Audio 1>: reference - the vocal timbre of <Audio 1> guides "
              "how <Subject 1> speaks, without copying the original signal.\n")
    s += "\ndetailed_description:\n" + DESC + "\n"
    if with_audio:
        s += (f"<Subject 1> (S1) speaks, using the clear Mandarin voice "
              f"timbre referenced from <Audio 1>, saying "
              f"<d>[zh-CN]{line.text}</d>\n")
    else:
        s += (f"<Subject 1> (S1) says, <d>[zh-CN]{line.text}</d>\n")
    s += ("\noverall_soundscape:\nThe room tone of the place in <Picture 1> "
          "continues throughout, with the small sounds of the room.\n\n"
          "non_diegetic_music:\nN/A")
    return s


def run(tag: str, with_audio: bool, turbo: bool):
    cfg2 = ctx.cfg.comfyui.model_copy(deep=True)
    cfg2.i2v_workflow = "config/comfyui/i2v_minimax_h3_ref2v_audio.json"
    vis.cfg = cfg2
    extra = {}
    if with_audio:
        extra["graph_overrides"] = {"900": {"audio": Path(audio).name,
                                            "upload": "audio"}}
    if not turbo:
        # the lightning LoRA off and a real step count: the docs say the
        # references hold better with 20-25 steps
        ov = extra.setdefault("graph_overrides", {})
        ov["121"] = {"strength_model": 0.0}
        ov["9"] = {"steps": 20}
    out = out_dir / f"{tag}.mp4"
    print(f"--- {tag}: 参考音频={with_audio} turbo={turbo}")
    try:
        vis.generate_video(prompt(with_audio), "",
                           image_path=str(sheet), frames=56, fps=24,
                           seed=20260201, out_path=str(out), extra=extra)
    except Exception as e:  # noqa: BLE001
        print("   失败:", type(e).__name__, str(e)[:160])
        return
    wav = out.with_suffix(".wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vn",
                    "-ac", "1", "-ar", "16000", str(wav)], capture_output=True)
    r = subprocess.run(["E:\\ComfyUI\\venv\\Scripts\\python.exe",
                        r"E:\\dramakit\\rounds\\tools\\transcribe.py", str(out)],
                       capture_output=True, text=True, errors="replace")
    said = ""
    for line_out in r.stdout.splitlines():
        if line_out.startswith("转写:"):
            said = line_out.split(":", 1)[1].strip()
    print(f"   -> {out.name}  H3 说: 「{said}」")
    print(f"   我们要: 「{line.text}」")


run("a_audio_turbo", True, True)
run("b_audio_full", True, False)
run("c_plain_turbo", False, True)
run("d_plain_full", False, False)
print("DONE", out_dir)
