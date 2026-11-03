"""Does the card reject a prompt that names a node type it does not have?

The workflow carries three note nodes that the 3090 does not define, and a
prompt that fails validation never reaches the queue - the whole render is
refused, not just the note. The check is a two-node graph with one unknown
type: if it is refused, the notes have to come out; if it is accepted, the
notes can stay and the real cause of a failure lies elsewhere.

The graph is refused or accepted before anything is sampled, so this costs
no GPU time either way.
"""
import json
import time
import urllib.request

HOST = "http://192.168.31.7:8188"
out = []


def post(payload: dict, timeout: float = 30) -> tuple[int, str]:
    req = urllib.request.Request(
        HOST + "/prompt",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")[:600]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:600]
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def probe(label: str, graph: dict) -> None:
    st, body = post({"prompt": graph, "client_id": "dramakit-validate"})
    out.append(f"--- {label} ---")
    out.append(f"  HTTP {st}")
    out.append("  " + body.replace("\n", " ")[:500])
    out.append("")


# 1. a note node the card does not define, feeding nothing
probe("未知类型 MarkdownNote（孤立）", {
    "1": {"class_type": "MarkdownNote", "inputs": {"value": "hello"}},
    "2": {"class_type": "Note", "inputs": {"value": "known note type"}},
})

# 2. a real node with an extra input the node does not declare
probe("真实节点 + 多余字段 text", {
    "1": {"class_type": "PrimitiveFloat", "inputs": {"value": 5.0, "text": "junk"}},
    "2": {"class_type": "Note", "inputs": {"value": "x"}},
})

# 3. an image loader pointed at a video slot (type mismatch)
probe("LoadImage -> ref_videos 槽", {
    "1": {"class_type": "LoadImage", "inputs": {"image": "does_not_exist.png"}},
    "2": {"class_type": "MiniMaxH3ReferenceToVideo",
          "inputs": {"prompt": "x", "width": 64, "height": 64, "length": 5,
                     "clip": ["3", 0], "ref_videos.ref_video_0": ["1", 0]}},
    "3": {"class_type": "CLIPLoader",
          "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_int8_convrot.safetensors",
                     "type": "minimax"}},
})

# 4. a node id with no class_type at all (what ref_audio_node=900 would make)
probe("无 class_type 的节点", {
    "900": {"inputs": {"audio": "x.wav"}},
})

# 5. what a missing file in LoadImage looks like
probe("LoadImage 指向不存在的文件", {
    "1": {"class_type": "LoadImage", "inputs": {"image": "nope_missing.png"}},
})

Path = __import__("pathlib").Path
Path(r"C:\Users\David\AppData\Local\Temp\opencode\reject.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
