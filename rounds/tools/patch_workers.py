"""The video concurrency follows the number of workers that are there."""
from pathlib import Path

# 1) the visual stage: never send more jobs at once than there are workers
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py")
s = p.read_text(encoding="utf-8")
old = """        offset += _run_phase("出视频", _gen_video, total, offset,
                             workers=max(1, int(c.video_concurrency or 0)
                                          or c.concurrency))"""
new = """        # as many at once as there are workers, and no more: one worker
        # means one video at a time, two cards means two
        workers = max(1, int(c.video_concurrency or 0) or c.concurrency)
        workers = min(workers, _video_workers(ctx))
        offset += _run_phase("出视频", _gen_video, total, offset, workers=workers)"""
assert old in s, "视频并发锚点没找到"
s = s.replace(old, new, 1)

old = """def _extra(ctx: Context) -> dict:"""
new = '''def _video_workers(ctx: Context) -> int:
    """How many machines can take a video job right now."""
    vis = ctx.providers.visual
    nodes = list(getattr(vis, "nodes", None) or [])
    if not nodes:
        return 1
    ok = 0
    for n in nodes:
        roles = {r.strip().lower() for r in (n.roles or [])}
        if roles and "i2v" not in roles:
            continue
        try:
            if n.client.ping():
                ok += 1
        except Exception:  # noqa: BLE001
            continue
    return max(1, ok)


def _extra(ctx: Context) -> dict:'''
assert old in s, "_extra 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("visual.py: 并发跟着能用的节点走")

# 2) the config: the second worker is there but not switched on
p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = """    - name: gpu3090-b
      base_url: http://192.168.31.7:8189
      enabled: true"""
new = """    - name: gpu3090-b
      base_url: http://192.168.31.7:8189
      enabled: false                    # 机器现在只剩一张卡，第二个实例起不来"""
assert old in s, "节点 b 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml: 第二个节点先关着")
