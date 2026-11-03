"""What was actually handed to the card, read back from the card.

A video of the right size proves the settings landed; it does not prove
the prompt did. A prompt that never arrives leaves the file's own words in
place, and the card renders them happily - a picture of the right
resolution, of the wrong scene, in the wrong voice.

So the submitted graph is read back from the card's own history: the
prompt text, which picture went into which slot, and which recording went
into the voice slot. Each is compared against what the test asked for.
"""
import json
import urllib.request
from pathlib import Path

HOST = "http://192.168.31.7:8188"
out = []


def get(path: str) -> dict:
    with urllib.request.urlopen(HOST + path, timeout=40) as r:
        return json.loads(r.read())


hist = get("/history?max_items=3")
out.append(f"=== 最近 {len(hist)} 条执行记录 ===")

for pid, rec in hist.items():
    # /history returns the graph two ways: a list of [id, node] pairs, or a
    # plain map. Either is read here, because the shape is not worth
    # arguing about when the answer is in the values.
    rawp = rec.get("prompt") or []
    if isinstance(rawp, dict):
        prompt = rawp
    elif isinstance(rawp, list):
        prompt = {}
        for item in rawp:
            if isinstance(item, dict):
                prompt[str(item.get("id"))] = item
            elif isinstance(item, list) and len(item) >= 2:
                prompt[str(item[0])] = item[1]
    else:
        prompt = {}
    status = rec.get("status") or {}
    out.append(f"  pid={pid}  状态={status.get('status_str')} "
               f"完成={status.get('completed')}  节点数={len(prompt)}")
    if not prompt:
        continue
    # the model node and the loaders, as submitted
    for nid, node in prompt.items():
        ct = node.get("class_type", "")
        ins = node.get("inputs", {})
        if ct == "MiniMaxH3ReferenceToVideo":
            out.append(f"    模型 #{nid}:")
            for k in ("prompt", "width", "height", "length"):
                if k in ins:
                    v = ins[k]
                    if k == "prompt":
                        v = str(v)[:400]
                    out.append(f"        {k} = {v}")
            for k in sorted(ins):
                if k.startswith("ref_"):
                    out.append(f"        {k} = {ins[k]}")
        if ct in ("LoadImage", "LoadAudio"):
            out.append(f"    {ct} #{nid}: {json.dumps(ins, ensure_ascii=False)[:120]}")
        if ct in ("PrimitiveStringMultiline", "PrimitiveFloat"):
            out.append(f"    {ct} #{nid}: {json.dumps(ins, ensure_ascii=False)[:400]}")
        if ct == "RandomNoise":
            out.append(f"    RandomNoise #{nid}: seed={ins.get('noise_seed')}")
        if ct == "CreateVideo":
            out.append(f"    CreateVideo #{nid}: fps={ins.get('fps')}")
        if ct == "ResolutionSelector":
            out.append(f"    ResolutionSelector #{nid}: "
                       f"{json.dumps(ins, ensure_ascii=False)[:100]}")
        if ct == "LoraLoaderModelOnly":
            out.append(f"    LoRA #{nid}: {ins.get('lora_name')} "
                       f"strength={ins.get('strength_model')}")
        if ct == "ComfySwitchNode":
            out.append(f"    开关 #{nid}: switch={ins.get('switch')} "
                       f"on_false={ins.get('on_false')} on_true={ins.get('on_true')}")
    out.append("")

# --- what the test asked for -------------------------------------------
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
who = next(c for c in raw["characters"] if isinstance(c, dict) and c.get("voice_ref"))
out.append("=== 测试要求的输入 ===")
out.append(f"  角色 {who.get('name')!r}")
out.append(f"  配音 {who.get('voice_ref')}")
out.append(f"  参考图 {[Path(p).name for p in who.get('ref_images', [])][:4]}")
out.append(f"  提示词含 <d> 台词标签")
out.append(f"  要求 1344x768 @24fps, 22 帧")

# --- the rendered frames, to see whose face it is -----------------------
vid = proj / "_render_test" / "probe.mp4"
if vid.exists():
    out.append("")
    out.append(f"=== 输出 {vid.name} {vid.stat().st_size/1024:.0f} KB ===")
    try:
        import subprocess
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,nb_frames,duration,codec_name",
             "-of", "json", str(vid)], capture_output=True, text=True, timeout=60)
        out.append("  " + (r.stdout or "").replace("\n", " "))
        # extract a frame so the face can be looked at
        frame = proj / "_render_test" / "frame.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(vid),
             "-vf", "select=eq(n\\,10)", "-vframes", "1", str(frame)],
            capture_output=True, timeout=60)
        if frame.exists():
            out.append(f"  抽帧 -> {frame} ({frame.stat().st_size/1024:.0f} KB)")
    except Exception as e:  # noqa: BLE001
        out.append(f"  ffprobe/ffmpeg: {e}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\history.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
