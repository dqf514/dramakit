"""Which shape the reference slots take, in the file that works and the
file that does not.

The code fills the picture slots by reading a nested dict, and the job was
refused because the slot stayed empty. The workflow the pipeline has been
using stores those slots one way, and the export stores them another: a
link can be written as a nested map or as a flat key with dots in it, and
only one of those is what the filling code reads.

So both files are read here, side by side, at the model node - which
decides whether the fix belongs in the new file or in the code that reads
it.
"""
import json
from pathlib import Path

out = []
old = Path(r"E:\dramakit\config\comfyui\i2v_minimax_h3_ref2v_audio.json")
new = Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")


def show(label: str, path: Path) -> None:
    out.append(f"=== {label} ({path.name}) ===")
    if not path.exists():
        out.append("  文件不存在")
        out.append("")
        return
    g = json.loads(path.read_text(encoding="utf-8"))
    out.append(f"  {len(g)} 节点")
    for nid, n in g.items():
        if "ReferenceToVideo" not in str(n.get("class_type", "")):
            continue
        out.append(f"  模型节点 #{nid}")
        ins = n.get("inputs", {})
        refish = {k: v for k, v in ins.items()
                  if k.startswith("ref_") or k == "prompt"}
        for k in sorted(refish):
            out.append(f"      {k} = {json.dumps(refish[k], ensure_ascii=False)[:80]}")
        # is there a nested dict anywhere?
        nested = {k: v for k, v in ins.items() if isinstance(v, dict)}
        if nested:
            out.append(f"      **嵌套 dict**: {list(nested)}")
            for k, v in nested.items():
                out.append(f"        {k} -> {json.dumps(v, ensure_ascii=False)[:120]}")
    out.append("")


show("现用工作流（管线一直在跑的）", old)
show("新工作流（短剧专用）", new)

# what the filling code reads
out.append("=== 填充代码读的是什么 ===")
u = Path(r"E:\dramakit\dramakit\providers\comfyui.py").read_text(encoding="utf-8")
i = u.index("pictures = list(extra.get")
out.append(u[i:i + 1400])

Path(r"C:\Users\David\AppData\Local\Temp\opencode\refshape.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
