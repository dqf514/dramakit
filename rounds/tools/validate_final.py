"""Re-check after the fixes, against the card the workflow runs on.

The notes are gone, the voice slot points at a node that exists, the
tail-frame slot is unwired, and the switch now decides whether the LoRA is
used. What is left is to confirm the card accepts the graph and that the
pipeline's writes land where the graph can take them.

As before, the save node is removed so the check costs no GPU: a clean
graph reports no outputs, a broken one reports the fault.
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

HOST = "http://192.168.31.7:8188"
out = []


def post(graph: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        HOST + "/prompt",
        data=json.dumps({"prompt": graph, "client_id": "dramakit-validate"}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace")[:700]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:700]
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


from dramakit.config import Config                     # noqa: E402
from dramakit.providers.comfyui import ComfyUIClient    # noqa: E402

cfg = Config.load(Config.discover())
cfg.comfyui.base_url = HOST
c = ComfyUIClient(cfg.comfyui, root=Path(r"E:\dramakit"))

rep = c.validate_workflow(cfg.comfyui.i2v_workflow, cfg.comfyui.i2v_nodes, "i2v")
out.append(f"=== {cfg.comfyui.i2v_workflow} 对 {HOST} ===")
out.append(f"  节点数 {rep.get('nodes')}  kind={rep.get('kind')}  ok={rep['ok']}")
for p in rep.get("problems") or []:
    out.append("  [问题] " + p)
for w in rep.get("warnings") or []:
    out.append("  [提醒] " + w)
if not (rep.get("problems") or []):
    out.append("  **无问题**")
out.append("")

graph = c._load_workflow(cfg.comfyui.i2v_workflow, "i2v")
no_out = {k: v for k, v in graph.items()
          if v.get("class_type") not in ("SaveVideo", "SaveImage", "VHS_VideoCombine")}
st, body = post(no_out)
out.append(f"=== 去掉 SaveVideo 后提交（{len(no_out)} 节点）===")
out.append(f"  HTTP {st}")
out.append("  " + body.replace("\n", " ")[:600])
if "prompt_no_outputs" in body:
    out.append("  => **通过**：全部节点类型/输入/文件校验合格")
else:
    out.append("  => **失败**")
out.append("")

# what the pipeline writes, and whether the field is there
out.append("=== 管线写入是否落在正确字段 ===")
nm = cfg.comfyui.i2v_nodes
checks = [("positive", "prompt", "提示词"), ("frames", "length", "帧数"),
          ("width", "width", "宽"), ("height", "height", "高"),
          ("seed", "noise_seed", "种子"), ("fps", "fps", "帧率"),
          ("image", "image", "首帧")]
for sem, field, label in checks:
    nid = str(nm.get(sem) or "")
    node = graph.get(nid)
    if not node:
        out.append(f"  {label:4} {sem:8} -> #{nid}  **节点不存在**")
        continue
    has = field in (node.get("inputs") or {})
    out.append(f"  {label:4} {sem:8} -> #{nid} {node.get('class_type'):<28} "
               f"字段 {field}: {'✓' if has else '**缺**'}")
out.append("")
out.append("=== 参考音频节点 ===")
out.append(f"  ref_audio_node = {cfg.comfyui.ref_audio_node!r}  "
           f"图里存在: {cfg.comfyui.ref_audio_node in graph}")
out.append(f"  该节点类型: {graph.get(cfg.comfyui.ref_audio_node, {}).get('class_type')}")
out.append(f"  last_image = {nm.get('last_image')!r}  "
           f"(空=不接尾帧)")
out.append(f"  native_audio = {cfg.comfyui.native_audio}  "
           f"video_references = {cfg.comfyui.video_references}")
out.append("")
out.append("=== 视频分辨率/帧数 ===")
out.append(f"  video_width x video_height = {cfg.comfyui.video_width} x {cfg.comfyui.video_height}")
out.append(f"  frames = {cfg.comfyui.frames}  fps = {cfg.comfyui.fps}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\final_check.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
