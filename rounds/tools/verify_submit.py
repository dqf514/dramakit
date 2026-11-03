"""Read back what the card was actually given, for the render that just ran.

The card's history keeps the graph it executed, and the graph is the only
record of what arrived: which words went to the prompt, which file went to
which picture slot, which recording went to the voice slot. A render of the
right resolution proves the size landed; it says nothing about any of the
rest, and each of those fails by leaving the file's own value in place.

So the newest records are scanned for the one this workflow produced - it
is the only graph with this many nodes and these loaders - and its
prompt, slots and settings are printed against what the test asked for.
"""
import json
import urllib.request
from pathlib import Path

HOST = "http://192.168.31.7:8188"
out = []


def get(path: str) -> dict:
    with urllib.request.urlopen(HOST + path, timeout=40) as r:
        return json.loads(r.read())


hist = get("/history?max_items=12")
out.append(f"=== 扫描 {len(hist)} 条历史 ===")

want_nodes = json.loads(
    Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json").read_text(encoding="utf-8"))

found = None
for pid, rec in hist.items():
    p = rec.get("prompt")
    # [number, prompt_id, graph, extra, outputs]
    graph = p[2] if isinstance(p, list) and len(p) > 2 and isinstance(p[2], dict) else (
        p if isinstance(p, dict) else {})
    n = len(graph)
    is_new = "136" in graph and graph.get("136", {}).get("class_type") == (
        "MiniMaxH3ReferenceToVideo")
    outs = rec.get("outputs") or {}
    files = [i.get("filename") for v in outs.values()
             if isinstance(v, dict) for i in v.get("images", [])]
    ok = (rec.get("status") or {}).get("status_str") == "success"
    out.append(f"  pid={pid[:8]} 节点={n:>3} 新工作流={is_new} "
               f"成功={ok} 输出={files}")
    # The run to read is the one that produced a file from this workflow
    # and succeeded. Earlier records are from before the fixes: same file,
    # fewer nodes, and the card's own placeholder still in the slots.
    if is_new and ok and files and (found is None or n > len(found[1])):
        found = (pid, graph, rec)

if not found:
    out.append("")
    out.append("没找到新工作流的记录")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\verify.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

pid, graph, rec = found
out.append("")
out.append(f"=== 这次渲染 pid={pid} ===")

# --- the prompt, as submitted ------------------------------------------
m = graph.get("136") or {}
ins = m.get("inputs") or {}
prompt_link = ins.get("prompt")
prompt_text = None
if isinstance(prompt_link, list):
    src = graph.get(str(prompt_link[0])) or {}
    prompt_text = (src.get("inputs") or {}).get("value")
elif isinstance(prompt_link, str):
    prompt_text = prompt_link
out.append("提示词（模型节点 #136 的 prompt 来源）:")
out.append(f"  来源: {prompt_link}")
out.append(f"  文本: {prompt_text}")
if prompt_text:
    out.append(f"  含 <d> 台词标签: {'<d>' in prompt_text}")
    out.append(f"  长度: {len(prompt_text)} 字")

# --- the picture slots --------------------------------------------------
out.append("")
out.append("参考图槽（谁喂给谁）:")
for key in sorted(ins):
    if not key.startswith("ref_images"):
        continue
    link = ins[key]
    nid = str(link[0]) if isinstance(link, list) else "?"
    node = graph.get(nid) or {}
    fname = (node.get("inputs") or {}).get("image")
    out.append(f"  {key} -> #{nid} {node.get('class_type')}  image={fname!r}")

# --- the voice slot -----------------------------------------------------
out.append("")
out.append("音频槽:")
for key in sorted(ins):
    if not key.startswith("ref_audios"):
        continue
    link = ins[key]
    nid = str(link[0]) if isinstance(link, list) else "?"
    node = graph.get(nid) or {}
    fname = (node.get("inputs") or {}).get("audio")
    out.append(f"  {key} -> #{nid} {node.get('class_type')}  audio={fname!r}")
if "ref_audios.ref_audio_0" not in ins:
    out.append("  **没有音频槽** —— 配音没进去")

# --- the settings -------------------------------------------------------
out.append("")
out.append("设置:")
for key, label in (("width", "宽"), ("height", "高"), ("length", "帧数")):
    v = ins.get(key)
    if isinstance(v, list):
        src = graph.get(str(v[0])) or {}
        v = f"来自 #{v[0]} {src.get('class_type')} = {(src.get('inputs') or {})}"
    out.append(f"  {label} ({key}) = {v}")
noise = graph.get("129") or {}
out.append(f"  种子 noise_seed = {(noise.get('inputs') or {}).get('noise_seed')}")
vid = graph.get("130") or {}
out.append(f"  fps = {(vid.get('inputs') or {}).get('fps')}")
res = graph.get("115") or {}
out.append(f"  分辨率选择器 = {(res.get('inputs') or {})}")
sw = graph.get("146") or {}
out.append(f"  LoRA 开关 #146 = {(sw.get('inputs') or {}).get('value')}")
lora = graph.get("145") or {}
out.append(f"  LoRA = {(lora.get('inputs') or {}).get('lora_name')}")
att = graph.get("151") or {}
out.append(f"  SageAttention #151 model 来源 = {(att.get('inputs') or {}).get('model')}")

# --- the output ---------------------------------------------------------
out.append("")
out.append("输出文件:")
for nid, v in (rec.get("outputs") or {}).items():
    if isinstance(v, dict):
        for i in v.get("images", []):
            out.append(f"  #{nid} {i.get('filename')} ({i.get('subfolder')})")

# --- and what was asked for --------------------------------------------
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
who = next(c for c in raw["characters"] if isinstance(c, dict) and c.get("voice_ref"))
out.append("")
out.append("=== 测试要求 ===")
out.append(f"  角色 {who.get('name')!r} 的配音: {who.get('voice_ref')}")
out.append(f"  角色参考图: {[Path(p).name for p in who.get('ref_images', [])]}")
out.append(f"  分辨率 1344x768  帧率 24  帧数 22")
out.append(f"  提示词含中文 <d> 台词")

# --- a frame to look at -------------------------------------------------
vid = proj / "_render_test" / "probe.mp4"
frame = proj / "_render_test" / "frame.jpg"
out.append("")
out.append(f"=== 抽帧 {frame.name if frame.exists() else '未生成'} ===")
if frame.exists():
    out.append(f"  {frame} ({frame.stat().st_size/1024:.0f} KB)")
if vid.exists():
    out.append(f"  视频 {vid} ({vid.stat().st_size/1024:.0f} KB)")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\verify.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
