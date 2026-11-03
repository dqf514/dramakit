"""Check the whole workflow without spending a minute of GPU.

Submitting a valid graph starts a render, and a render is the one test that
cannot be run twice for free. But ComfyUI validates before it queues, and
its last check is whether the graph produces anything at all: strip the
save node and a clean graph reports "no outputs" while a broken one reports
the actual fault - a missing node type, an input that is not there, a file
the card cannot see. That is the whole validation, for free.

So the test is the shipped workflow with its save node removed. "No
outputs" means every other node passed.
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

HOST = "http://192.168.31.7:8188"
WF = Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
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


def check(label: str, graph: dict) -> str:
    st, body = post(graph)
    out.append(f"--- {label} ---")
    out.append(f"  HTTP {st}")
    out.append("  " + body.replace("\n", " ")[:600])
    verdict = ""
    if "prompt_no_outputs" in body:
        verdict = "通过（除输出节点外全部校验合格）"
    elif "missing_node_type" in body:
        verdict = "失败：节点类型不存在"
    else:
        verdict = "见上"
    out.append(f"  => {verdict}")
    out.append("")
    return verdict


full = json.loads(WF.read_text(encoding="utf-8"))

# --- the workflow as shipped, minus whatever produces output -----------
no_out = {k: v for k, v in full.items()
          if v.get("class_type") not in ("SaveVideo", "SaveImage", "VHS_VideoCombine")}
before = len(full)
st, body = post(no_out)
out.append(f"=== 原样工作流（去掉输出节点 {before}->{len(no_out)}）===")
out.append(f"  HTTP {st}")
out.append("  " + body.replace("\n", " ")[:700])
if "prompt_no_outputs" in body:
    out.append("  => **通过**：除输出节点外，全部节点类型/输入/文件校验合格")
else:
    out.append("  => **失败**：见上方错误")
out.append("")

# --- now fix by fix, so each change can be blamed or cleared -----------
def without(*nids: str) -> dict:
    g = {k: v for k, v in no_out.items() if k not in set(nids)}
    # and any link that pointed at a removed node
    for n in g.values():
        for k, v in list((n.get("inputs") or {}).items()):
            if isinstance(v, list) and str(v[0]) in set(nids):
                n["inputs"].pop(k)
    return g


out.append("=== 逐项验证 ===")
check("删掉 3 个 MarkdownNote (116,117,140)", without("116", "117", "140"))

g = without("116", "117", "140", "165")
check("再删掉 LoadImage->ref_video_0 (165)", g)

# --- reference slots the pipeline never fills --------------------------
# the pipeline writes audio into the node named by ref_audio_node; with the
# default 900 that node does not exist, and a node with no class_type is
# refused. This is what the shipped graph does with its audio slots.
g2 = without("116", "117", "140", "165")
check("音频槽留空（LoadAudio 无 audio 字段）", g2)

# what the pipeline will actually do: point ref_audio_node at node 162
g3 = without("116", "117", "140", "165")
model = next(k for k, n in g3.items()
             if n.get("class_type") == "MiniMaxH3ReferenceToVideo")
ins = g3[model]["inputs"]
# keep only the slot the pipeline fills
keep = {k: v for k, v in ins.items() if not k.startswith("ref_audios.")}
keep["ref_audios.ref_audio_0"] = ["162", 0]
g3[model]["inputs"] = keep
check("只留 ref_audio_0 -> #162", g3)

# --- pictures: what if fewer than three arrive ------------------------
g4 = without("116", "117", "140", "165")
m4 = next(k for k, n in g4.items()
          if n.get("class_type") == "MiniMaxH3ReferenceToVideo")
imgs = dict(g4[m4]["inputs"].get("ref_images") or {})
imgs.pop("ref_images.ref_image_2", None)
g4[m4]["inputs"]["ref_images"] = imgs
g4.pop("161", None)
check("只用 2 张参考图（删 ref_image_2 / 161）", g4)

Path(r"C:\Users\David\AppData\Local\Temp\opencode\wfcheck.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
