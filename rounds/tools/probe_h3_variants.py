"""Which H3 weights does this card actually run fast?

The card was drawing 75 watts while "100% utilised" - the sign of work
that is waiting on memory rather than computing. That points at the
4-bit weights: they are stored in a packed form and have to be turned
back into ordinary numbers before a layer can use them, and if that
happens on every step rather than once at load, the card spends its
time shuffling bytes.

So the variants are compared on the same clip: same seed, same
references, same length. The number that matters is the seconds per
frame, not the total.
"""
import copy
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
sys.path.insert(0, r"E:\dramakit\rounds\tools")

from build_music_wf import build as _unused  # noqa: E402,F401  (keeps path set up)

BASE = "http://127.0.0.1:8188"
WF = Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\ab_test")
OUT.mkdir(parents=True, exist_ok=True)

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 49

VARIANTS = [
    ("nvfp4", {"unet_name": "MiniMax_H3_Ref2VA_pruned_nvfp4.safetensors"},
     {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "device": "default"}),
    ("mixed_int4_int8", {"unet_name": "MiniMax_H3_Ref2VA_pruned_mixed_int4_int8_convrot.safetensors"},
     {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "device": "default"}),
]

# The first time a weight is used the card pays for things it will not pay
# for again - the kernels are compiled, the file is read, the quantised
# weights are built. So the order of the tests is not the answer: the
# second round of each is. Two rounds, alternating, and the second round
# is what is compared.
ROUNDS = 2


def post(path, body, timeout=180):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(path, timeout=300):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


def power():
    import subprocess
    r = subprocess.run(["nvidia-smi", "--query-gpu=power.draw,memory.used",
                        "--format=csv,noheader,nounits"],
                       capture_output=True, text=True)
    return r.stdout.strip()


def run(name, unet, clip):
    g = json.loads(WF.read_text(encoding="utf-8"))
    g["127"]["inputs"].update(unet)
    g["128"]["inputs"].update(clip)
    g["119"]["inputs"]["vae_name"] = "minimax_h3_video_vae_int8_convrot.safetensors"
    g["136"]["inputs"]["length"] = FRAMES
    # one reference only: the comparison is about speed, not about who
    # the people look like
    drop_nodes = set()
    for k in list(g["136"]["inputs"]):
        if k in ("ref_images.ref_image_0", "ref_image_size"):
            continue
        if k.startswith("ref_images.") or k.startswith("ref_audios."):
            link = g["136"]["inputs"].pop(k)
            if isinstance(link, list) and link:
                drop_nodes.add(str(link[0]))
    for nid in drop_nodes:
        g.pop(nid, None)
    # this card has no SageAttention plugin: the patch node is taken out
    # and its user is pointed at what fed it, the same way the pipeline
    # does it
    sage = g.pop("151", None)
    if sage:
        src = sage["inputs"]["model"]
        for node in g.values():
            for k, v in list(node.get("inputs", {}).items()):
                if isinstance(v, list) and len(v) == 2 and str(v[0]) == "151":
                    node["inputs"][k] = list(src)
    # the first frame is the only reference: the comparison is about speed
    img = sorted((Path(r"E:\dramakit\projects\星际骷髅兵\images")).glob("shot_*.png"))[0]
    up = post("/upload/image", {}, timeout=60) if False else None
    req = urllib.request.Request(
        BASE + "/upload/image",
        data=json.dumps({"image": img.read_bytes().hex(), "overwrite": True,
                         "type": "input", "subfolder": "", "name": "ab_first.png"}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    # ComfyUI's upload takes multipart; the hex form is what its own
    # client uses, so go through the file API instead
    boundary = "----abtest"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
            f"filename=\"{img.name}\"\r\nContent-Type: image/png\r\n\r\n").encode() \
        + img.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BASE + "/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        up = json.loads(r.read())
    g["137"]["inputs"]["image"] = up["name"]

    t0 = time.time()
    try:
        pid = post("/prompt", {"prompt": g, "client_id": "abtest"})["prompt_id"]
    except urllib.error.HTTPError as e:
        return {"name": name, "error": e.read().decode("utf-8", "replace")[:300]}
    print(f"  [{name}] pid={pid[:8]} 已提交", flush=True)
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
        return {"name": name, "error": err, "seconds": round(dt, 1)}
    return {"name": name, "seconds": round(dt, 1),
            "per_frame": round(dt / FRAMES, 2), "power": power()}


results = []
for rnd in range(ROUNDS):
    for name, unet, clip in VARIANTS:
        print(f"=== 第 {rnd+1}/{ROUNDS} 轮 · {name} ===", flush=True)
        r = run(name, unet, clip)
        r["round"] = rnd + 1
        results.append(r)
        print("  ->", json.dumps(r, ensure_ascii=False), flush=True)

print()
print("=== 结果（看第 2 轮，那才是稳态）===")
for r in results:
    print("  %-18s 第%d轮  %s" % (r["name"], r.get("round", 0),
                                  json.dumps({k: v for k, v in r.items()
                                              if k not in ("name", "round")},
                                             ensure_ascii=False)))
Path(r"C:\Users\David\AppData\Local\Temp\opencode\ab_test.txt").write_text(
    json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
