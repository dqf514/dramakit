"""Ask the card what its nodes actually take.

The widget field names were being guessed, and a wrong guess does not fail
loudly - it leaves the input at its default, so a prompt never arrives or
a resolution never changes, and the render happens anyway. ComfyUI publishes
the input spec for every node it has; this reads it for the ones the new
workflow uses, so the mapping is written from the node's own definition
rather than from a guess.
"""
import json
import urllib.request
from pathlib import Path

HOSTS = {
    "3090": "http://192.168.31.7:8188",
    "5080": "http://127.0.0.1:8188",
}
WANT = ["MiniMaxH3ReferenceToVideo", "PrimitiveStringMultiline",
        "PrimitiveFloat", "PrimitiveInt", "PrimitiveBoolean",
        "ResolutionSelector", "LoadImage", "LoadAudio", "RandomNoise",
        "CreateVideo", "UNETLoader", "CLIPLoader", "LoraLoaderModelOnly",
        "PathchSageAttentionKJ", "ComfyMathExpression"]

out = []
for label, host in HOSTS.items():
    out.append(f"=== {label}  {host} ===")
    try:
        with urllib.request.urlopen(host + "/object_info", timeout=25) as r:
            info = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        out.append(f"  读不到: {type(e).__name__}: {str(e)[:120]}")
        out.append("")
        continue
    out.append(f"  节点总数 {len(info)}")
    for name in WANT:
        spec = info.get(name)
        if not spec:
            out.append(f"    {name}: 这台机器上没有")
            continue
        ins = (spec.get("input") or {}).get("required", {})
        opt = (spec.get("input") or {}).get("optional", {})
        out.append(f"    {name}:")
        for k, v in list(ins.items())[:9]:
            kind = v[0] if isinstance(v, list) and v else v
            out.append(f"        必填 {k}: {kind}")
        for k, v in list(opt.items())[:7]:
            kind = v[0] if isinstance(v, list) and v else v
            out.append(f"        可选 {k}: {kind}")
    out.append("")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\objinfo.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
