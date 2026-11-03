"""What a re-run would actually do, without doing any of it.

The project stopped with promptgen marked interrupted and five of nine
episodes carrying prompts. The system has no button that starts itself
again: the boot cleanup only writes down what was left running, and the
resume flag lives inside each stage, where it takes a run to reach it.

So before starting one, the run is simulated - the same context, the same
episode list, the same per-shot test the stage uses - to see how many
shots it would redo and how many it would leave alone. That is the whole
question: whether resuming continues at episode six or starts the book
over.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
from dramakit.config import Config            # noqa: E402
from dramakit.pipeline.base import Context     # noqa: E402

cfg = Config.load(Config.discover())
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
slug = json.loads((proj / "project.json").read_text(encoding="utf-8")) \
    .get("meta", {}).get("name") or proj.name

# the same construction the CLI uses: a store, then a context over it
from dramakit.project import ProjectStore          # noqa: E402

try:
    store = ProjectStore.open(proj)
    ctx = Context(cfg, store)
except Exception as e:  # noqa: BLE001
    out.append(f"打不开 Context: {type(e).__name__}: {e}")
    ctx = None

if ctx is not None:
    out.append("=== Context 打开成功 ===")
    out.append(f"  项目 {ctx.project.meta.name!r}")

    out.append("")
    out.append("=== stage_status ===")
    for k, v in ctx.project.stage_status.items():
        out.append(f"  {k:14} {v}")

    eps = []
    try:
        eps = list(ctx.target_episodes())
    except Exception as e:  # noqa: BLE001
        out.append(f"  target_episodes 失败: {type(e).__name__}: {e}")
    out.append("")
    out.append(f"=== target_episodes() -> {len(eps)} 集 ===")
    for ep in eps:
        out.append(f"  ep{ep.index} {str(ep.title)[:16]:18} "
                   f"stage={ep.stage_status}")

    # the per-shot test promptgen uses
    out.append("")
    out.append("=== promptgen 会跑多少镜头 ===")
    total_shots = 0
    need_img = 0
    need_h3 = 0
    for ep in eps:
        ep_total = ep_done = 0
        for sc in ep.scenes:
            for shot in sc.shots:
                ep_total += 1
                total_shots += 1
                if not shot.prompt:
                    need_img += 1
                if not (shot.video_prompt or ""):
                    need_h3 += 1
                if shot.prompt and shot.video_prompt:
                    ep_done += 1
        out.append(f"  ep{ep.index}: {ep_total} 镜，两提示词齐 {ep_done} 镜")

    out.append("")
    out.append(f"  总镜头 {total_shots}")
    out.append(f"  缺图提示词（要生成）: {need_img}")
    out.append(f"  缺 H3 提示词（要生成）: {need_h3}")
    out.append(f"  已齐（会跳过）: {total_shots - max(need_img, need_h3)}")

    # visual
    out.append("")
    out.append("=== visual 会跑多少镜头 ===")
    v_need = v_done = 0
    for ep in eps:
        for sc in ep.scenes:
            for shot in sc.shots:
                if shot.video_path:
                    v_done += 1
                else:
                    v_need += 1
    out.append(f"  已有视频 {v_done}，待出 {v_need}")

    out.append("")
    out.append("=== 阶段启用配置 ===")
    out.append(f"  stages_enabled = {cfg.pipeline.stages_enabled}")
    out.append(f"  resume = {cfg.pipeline.resume}")
    out.append(f"  stop_after = {cfg.pipeline.stop_after}")
    out.append(f"  fail_fast = {cfg.pipeline.fail_fast}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\resume_sim.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
