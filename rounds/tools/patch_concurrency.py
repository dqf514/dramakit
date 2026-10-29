"""Two concurrencies: the stills and the videos are different jobs.

The stills run on the local card, one at a time - the picture model and
the text encoder together are close to filling it. The videos run on the
other machines, one per card, so they can go several at a time: with one
concurrency the jobs queue up behind each other and one node does all of
them, because a single job at a time always looks like the same tie.
"""
from pathlib import Path

# 1) the config
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    concurrency: int = 1"""
new = """    concurrency: int = 1                              # 出图并发（本机一张卡，一次一个）
    video_concurrency: int = 2                        # 出视频并发（每个远端节点一个）"""
if old in s:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("config.py 已改（视频并发单独设置）")
else:
    print("config.py: concurrency 锚点没找到")

# 2) the yaml
p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
lines = s.splitlines()
for i, line in enumerate(lines):
    if line.strip().startswith("concurrency: 1") and "comfy" not in line:
        lines[i] = ("  concurrency: 1                            # 出图并发（本机一张卡，"
                    "一次一个）\n"
                    "  video_concurrency: 2                     # 出视频并发（每个远端节点一个）")
        break
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("yaml 已改")

# 3) the visual stage: the video phase uses its own number
p = Path(r"E:\\dramakit\\dramakit\\pipeline\\visual.py")
s = p.read_text(encoding="utf-8")
old = """    def _run_phase(label: str, fn, total: int, offset: int) -> int:
        nonlocal ok_count
        done = 0
        with ThreadPoolExecutor(max_workers=max(1, c.concurrency)) as ex:"""
new = """    def _run_phase(label: str, fn, total: int, offset: int,
                   workers: int = 0) -> int:
        nonlocal ok_count
        done = 0
        n = workers or c.concurrency
        with ThreadPoolExecutor(max_workers=max(1, n)) as ex:"""
assert old in s, "phase 锚点没找到"
s = s.replace(old, new, 1)

old = """            _run_phase("出视频", _gen_video, len(jobs), len(jobs))"""
new = """            _run_phase("出视频", _gen_video, len(jobs), len(jobs),
                       workers=max(1, int(c.video_concurrency or 0)
                                    or c.concurrency))"""
if old in s:
    s = s.replace(old, new, 1)
else:
    print("visual.py: 出视频的调用锚点没找到")
p.write_text(s, encoding="utf-8")
print("visual.py 已改")
