"""Rebuild the plan the interrupted run was following, and record it.

The run stopped before any of this existed, so there is no record of what
it was asked to do - only of how far it got. The two together are enough:
the stages that are not done are the ones still owed, and the chapters
the project chose are what the episodes were cut from.

Recording it rather than calling /api/run directly is the point of the
mechanism: the next interruption, whenever it happens, will have its own
plan on file and can be resumed without this reconstruction.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

out = []
from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.pipeline.runner import ORDER, SETUP  # noqa: E402

cfg = Config.load(Config.discover())
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
store = ProjectStore.open(proj)
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))

done = [k for k, v in (raw.get("stage_status") or {}).items() if v == "done"]
pending = [k for k, v in (raw.get("stage_status") or {}).items() if v != "done"]
out.append(f"项目 {raw['meta']['name']!r}")
out.append(f"  已完成阶段: {done}")
out.append(f"  未完成阶段: {pending}")

# the stages still owed, in the order the runner takes them
wanted = list(cfg.pipeline.stages_enabled)
stages = [s for s in ORDER if s in wanted and s not in done]
# SETUP stages that are done must not be re-entered: they are the ones
# that rebuild the cast and the cut, and re-entering them is how a resume
# ends up making the book twice.
setup_done = [s for s in SETUP if s in done]
stages = [s for s in stages if s not in setup_done]
out.append(f"  本次续跑阶段（按 ORDER 排序）: {stages}")
out.append(f"  跳过的已完成 SETUP: {setup_done}")

plan = {
    "chapters": list(raw["meta"].get("chosen_chapters") or []),
    "episodes": [],
    "stages": stages,
    "overrides": {},
    "season": None,
}
out.append("")
out.append("=== 补录的 last_run ===")
out.append(json.dumps(plan, ensure_ascii=False, indent=2))

raw["meta"]["last_run"] = plan
(proj / "project.json").write_text(
    json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
out.append("")
out.append("已写入 project.json")

# --- what it will cost -------------------------------------------------
out.append("")
out.append("=== 续跑的工作量 ===")
episodes = raw.get("episodes") or []
need_prompt = 0
need_video = 0
have_prompt = 0
for ep in episodes:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            if sh.get("prompt") and sh.get("video_prompt"):
                have_prompt += 1
            else:
                need_prompt += 1
            if not sh.get("video_path"):
                need_video += 1
out.append(f"  镜头总数 {need_prompt + have_prompt}")
out.append(f"  提示词已齐（跳过）: {have_prompt}，待生成: {need_prompt}")
out.append(f"  视频待出: {need_video}")
frames = cfg.comfyui.frames
fps = cfg.comfyui.fps
per = frames / fps
out.append(f"  每段 {frames} 帧 @{fps}fps = {per:.1f} 秒")
out.append(f"  按实测 22 帧 142 秒推算，124 帧约 {142 * frames / 22 / 60:.0f} 分钟/段")
out.append(f"  {need_video} 段 ≈ {need_video * 142 * frames / 22 / 3600:.0f} 小时（3090 连续跑）")
out.append(f"  视频走节点: 3090（roles=i2v），SageAttention 已接入")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\seed.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
