"""Build the workflow converter from what the card itself declares.

Writing the widget field names by hand meant three loader nodes came
through with no inputs at all - a model name that never arrives, and a
render that fails on the card rather than in the log. The card publishes
every node's inputs with their types, and a widget is simply an input
whose type is not a connection: COMBO, INT, FLOAT, STRING, BOOLEAN. That
is the order the widgets are saved in, so the names can be read rather
than guessed.

Run against the remote card, since that is where the nodes live and where
their definitions are authoritative.
"""
import json
import urllib.request
from pathlib import Path

HOST = "http://192.168.31.7:8188"

# types that are a wire between nodes rather than a value to set
CONN = {"MODEL", "CLIP", "VAE", "LATENT", "IMAGE", "AUDIO", "VIDEO",
        "CONDITIONING", "SIGMAS", "NOISE", "GUIDER", "SAMPLER", "SAGEATTN",
        "COMFY_AUTOGROW_V3", "RESOLUTION_PREVIEW", "COMFYMATH_STACK"}


def widget_fields(info: dict) -> dict[str, list[str]]:
    """node type -> the widget inputs it saves, in order."""
    out: dict[str, list[str]] = {}
    for name, spec in info.items():
        if not isinstance(spec, dict):
            continue
        inp = spec.get("input") or {}
        names: list[str] = []
        for group in ("required", "optional"):
            for k, v in (inp.get(group) or {}).items():
                typ = v[0] if isinstance(v, list) and v else v
                # a connection is a wire; everything else is a widget, and
                # a widget is what widgets_values holds, in this order
                if isinstance(typ, str) and typ.upper() in CONN:
                    continue
                names.append(k)
        out[name] = names
    return out


if __name__ == "__main__":
    with urllib.request.urlopen(HOST + "/object_info", timeout=60) as r:
        info = json.loads(r.read())
    fields = widget_fields(info)
    dst = Path(r"E:\dramakit\rounds\tools\widget_fields.json")
    dst.write_text(json.dumps(fields, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(fields)} 个节点类型 -> {dst}")
    for name in ("UNETLoader", "CLIPLoader", "VAELoader", "LoraLoaderModelOnly",
                 "KSamplerSelect", "BasicScheduler", "CreateVideo",
                 "ComfyMathExpression", "PathchSageAttentionKJ",
                 "ComfySwitchNode", "MiniMaxH3ReferenceToVideo"):
        print(f"  {name:<30} {fields.get(name)}")
