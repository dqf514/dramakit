"""Find the workflow file without asking a client for it.

The provider is now a pool of machines, and the pool has no workflow of
its own - so asking it for the file raised, the H3 prompts were never
written, and the video stage fell back to the picture prompt: the model
was handed a scene description instead of a performance, and read the
actions out loud as a voice over.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")

old = '''def _h3_needed(ctx: Context) -> bool:
    """True when the configured video workflow uses the native MiniMax H3 nodes."""
    try:
        wf = ctx.providers.visual._load_workflow(  # noqa: SLF001
            ctx.cfg.comfyui.i2v_workflow)
    except Exception:  # noqa: BLE001
        return False
    return any("MiniMaxH3" in str(n.get("class_type", "")) for n in wf.values())'''
new = '''def _h3_needed(ctx: Context) -> bool:
    """True when the configured video workflow uses the native MiniMax H3 nodes.

    The workflow file is read straight from disk: the provider may be a
    pool of machines now, and a pool has no workflow of its own.
    """
    rel = ctx.cfg.comfyui.i2v_workflow
    if not rel:
        return False
    roots: list[Path] = []
    vis = ctx.providers.visual
    for node in (getattr(vis, "nodes", None) or []):
        root = getattr(getattr(node, "client", None), "root", None)
        if root:
            roots.append(Path(root))
    roots.append(Path("."))
    for root in roots:
        p = Path(rel) if Path(rel).is_absolute() else root / rel
        if not p.exists():
            continue
        try:
            import json as _json
            wf = _json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        return any("MiniMaxH3" in str(n.get("class_type", "")) for n in wf.values())
    return False'''
assert old in s, "_h3_needed 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("promptgen.py 已改（H3 提示词检测不再依赖客户端）")
