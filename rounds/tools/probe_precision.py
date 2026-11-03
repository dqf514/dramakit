"""The same clip, made two ways, on the same card.

There is one systematic difference between the two cards: the weights.
The remote runs eight-bit, the local card runs four-bit. Everything else
- the workflow, the steps, the adapter, the prompts, the reference
pictures - is the same, so the weights are the only thing that could
make one card's clips worse than the other's.

So the same clip is made both ways here, with the references the
pipeline actually uses, and the frames are put side by side. The time
is measured too: eight-bit on a card with sixteen gigabytes does not
fit, so the question is not only whether it looks better but what it
costs.
"""
import copy
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

BASE = "http://127.0.0.1:8188"
WF = Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
PROJ = Path(r"E:\dramakit\projects\星际骷髅兵")
OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\quality")
OUT.mkdir(parents=True, exist_ok=True)
FRAMES = 49

CASES = [
    ("4bit", {"unet_name": "MiniMax_H3_Ref2VA_pruned_nvfp4.safetensors"},
     {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "device": "default"}),
    ("8bit", {"unet_name": "MiniMax_H3_Ref2VA_pruned_int8_convrot.safetensors"},
     {"clip_name": "qwen3vl_32b_minimax_h3_int8_convrot.safetensors", "device": "default"}),
]


def post(path, body, timeout=300):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(path, timeout=300):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


def upload(path: Path) -> str:
    boundary = "----dq"
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".mp3": "audio/mpeg",
            ".wav": "audio/wav"}[path.suffix.lower()]
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
            f"filename=\"{path.name}\"\r\nContent-Type: {mime}\r\n\r\n").encode() \
        + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BASE + "/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["name"]


def graph_for(unet, clip, frame: Path):
    g = json.loads(WF.read_text(encoding="utf-8"))
    g["127"]["inputs"].update(unet)
    g["128"]["inputs"].update(clip)
    g["119"]["inputs"]["vae_name"] = "minimax_h3_video_vae_int8_convrot.safetensors"
    g["136"]["inputs"]["length"] = FRAMES
    # this card has no SageAttention: take the patch out and wire past it
    sage = g.pop("151", None)
    if sage:
        src = sage["inputs"]["model"]
        for node in g.values():
            for k, v in list(node.get("inputs", {}).items()):
                if isinstance(v, list) and len(v) == 2 and str(v[0]) == "151":
                    node["inputs"][k] = list(src)
    # the references the pipeline uses: the frame, the character's sheet,
    # the room, and the voice
    four = sorted((PROJ / "characters").rglob("four.png"))[0]
    room = sorted((PROJ / "locations").rglob("ref.png"))
    voice = sorted((PROJ / "characters").rglob("voice.mp3"))[0]
    g["137"]["inputs"]["image"] = upload(frame)
    g["162"]["inputs"]["image"] = upload(four)
    g["161"]["inputs"]["audio"] = upload(voice)
    # the workflow has room for nine pictures and one recording; only the
    # ones that are filled stay, and the rest go with them
    keep_images = {"137", "162"}
    if room:
        g["163"]["inputs"]["image"] = upload(room[0])
        keep_images.add("163")
    drop = set()
    for k, v in list(g["136"]["inputs"].items()):
        if not k.startswith("ref_images.ref_image_"):
            continue
        if str(v[0]) in keep_images:
            continue
        g["136"]["inputs"].pop(k)
        drop.add(str(v[0]))
    for nid in drop:
        g.pop(nid, None)
    return g


def first_prompt():
    raw = json.loads((PROJ / "project.json").read_text(encoding="utf-8"))
    for ep in raw.get("episodes") or []:
        for sc in ep.get("scenes") or []:
            for sh in sc.get("shots") or []:
                if sh.get("video_prompt"):
                    return sh["video_prompt"]
    return ""


def run(label, unet, clip, prompt, frame: Path):
    g = graph_for(unet, clip, frame)
    g["138"]["inputs"]["text"] = prompt
    outdir = Path(r"E:\ComfyUI\output\video")
    before = {p.name for p in outdir.glob("*.mp4")} if outdir.exists() else set()
    t0 = time.time()
    try:
        pid = post("/prompt", {"prompt": g, "client_id": "dq"})["prompt_id"]
    except urllib.error.HTTPError as e:
        return {"label": label, "error": e.read().decode("utf-8", "replace")[:400]}
    print(f"  [{label}] pid={pid[:8]} 提交了", flush=True)
    rec = None
    while time.time() - t0 < 3600:
        time.sleep(6)
        rec = (json.loads(get("/history/" + pid)) or {}).get(pid)
        if rec and (rec.get("status") or {}).get("status_str") in ("success", "error"):
            break
    dt = time.time() - t0
    st = (rec or {}).get("status") or {}
    if st.get("status_str") != "success":
        err = ""
        for m in (st.get("messages") or []):
            if isinstance(m, list) and m[0] == "execution_error":
                e = m[1] if isinstance(m[1], dict) else {}
                err = str(e.get("exception_message"))[:200]
        return {"label": label, "error": err, "seconds": round(dt, 1)}
    name = None
    for out in (rec.get("outputs") or {}).values():
        for key in ("gifs", "videos", "video", "images"):
            for a in (out.get(key) or []):
                if isinstance(a, dict) and a.get("filename"):
                    name = a["filename"]
                    sub = a.get("subfolder") or ""
    if not name:
        return {"label": label, "error": "没有输出", "seconds": round(dt, 1)}
    # the card writes the file into its output folder; take the one that
    # is new, not the newest one that happens to be there
    new = [p for p in (outdir.glob("*.mp4") if outdir.exists() else [])
           if p.name not in before]
    if not new:
        return {"label": label, "error": "输出文件没出现", "seconds": round(dt, 1)}
    src = max(new, key=lambda p: p.stat().st_mtime)
    dest = OUT / (label.split(" ")[0] + ".mp4")
    dest.write_bytes(src.read_bytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(dest),
                    "-vf", "select='eq(n\\,30)',scale=800:-1",
                    "-frames:v", "1", str(OUT / (label.split(" ")[0] + ".jpg"))],
                   capture_output=True, timeout=180)
    return {"label": label, "seconds": round(dt, 1),
            "per_frame": round(dt / FRAMES, 2), "file": str(dest)}


def pick_shot():
    """A shot with people in it, and its own picture and its own prompt.

    The two cases have to be the same shot - the same frame, the same
    words - or the comparison is between two different scenes.
    """
    raw = json.loads((PROJ / "project.json").read_text(encoding="utf-8"))
    for ep in raw.get("episodes") or []:
        for sc in ep.get("scenes") or []:
            for sh in sc.get("shots") or []:
                people = [c for c in (sh.get("characters") or [])]
                img = PROJ / (sh.get("image_path") or "")
                if not people or not sh.get("video_prompt") or not img.exists():
                    continue
                return img, sh["video_prompt"], sh.get("id")
    return None, None, None


def main():
    frame, prompt, sid = pick_shot()
    if frame is None:
        print("  找不到合适的镜头")
        return
    print("  镜头:", sid, " 图:", frame.name, " 提示词长度:", len(prompt))
    results = []
    for label, unet, clip in CASES:
        print(f"=== {label} ===", flush=True)
        r = run(label, unet, clip, prompt, frame)
        results.append(r)
        print("  ->", json.dumps(r, ensure_ascii=False), flush=True)
    # side by side
    jpgs = [OUT / (c[0].split(" ")[0] + ".jpg") for c in CASES]
    jpgs = [j for j in jpgs if j.exists()]
    if len(jpgs) == 2:
        out = OUT / "4bit_vs_8bit.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(jpgs[0]),
                        "-i", str(jpgs[1]), "-filter_complex", "hstack=inputs=2",
                        str(out)], capture_output=True, timeout=180)
        print("  并排:", out, out.exists())
    print(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
