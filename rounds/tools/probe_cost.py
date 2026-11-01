"""What will the run in flight do next, and what would that cost?

The segment stage is cutting all 145 chapters because the instruction
could not say "these chapters". The question that matters now is what
happens when it finishes: if the run carries the later stages and no
episode limit, it will make pictures and video for every one of them.
This works out what that means before it happens.
"""
import json
from pathlib import Path

out = []

cfg = Path(r"E:\dramakit\config\default.yaml").read_text(encoding="utf-8")
for key in ("stages_enabled", "only_episodes", "stop_after"):
    for line in cfg.split("\n"):
        if line.strip().startswith(key):
            out.append(f"配置 {key}: {line.strip()[:120]}")
            break

out.append("")
out.append("=== 项目现状 ===")
pj = Path(r"E:\dramakit\projects\妖怪志")
d = json.loads((pj / "project.json").read_text(encoding="utf-8"))
m = d.get("meta", {})
out.append(f"  已切出的集原文: {len(list((pj / 'source').glob('ep_*.txt')))} 个文件")
out.append(f"  chosen_chapters: {m.get('chosen_chapters') or '（空）'}")
out.append(f"  chapters 总数: {len(m.get('chapters') or [])}")
out.append(f"  stage_status: {json.dumps(d.get('stage_status', {}), ensure_ascii=False)}")

# the book, and what an episode costs downstream
total_chars = sum(f.stat().st_size for f in (pj / "source").glob("ep_*.txt"))
per_ep_chars = total_chars / max(1, len(list((pj / "source").glob("ep_*.txt"))))
cleaned = (pj / "source" / "cleaned.txt").stat().st_size
n_eps = round(cleaned / per_ep_chars) if per_ep_chars else 0

out.append("")
out.append("=== 估算 ===")
out.append(f"  cleaned.txt: {cleaned:,} 字节")
out.append(f"  平均每集原文: {per_ep_chars:,.0f} 字节")
out.append(f"  推算总集数: 约 {n_eps} 集")

# a short drama episode is a few dozen shots; each shot needs a still and a
# clip, and the clip is the expensive part
shots_per_ep = 30
out.append("")
out.append("  按每集约 30 镜估算（每镜 1 张首帧 + 1 段视频）:")
out.append(f"    需要生成的首帧: 约 {n_eps * shots_per_ep:,} 张")
out.append(f"    需要生成的视频: 约 {n_eps * shots_per_ep:,} 段")

# measured: 19.3 min for a 10s 768p clip on the single 3090
mins_per_clip = 19.3
hours = n_eps * shots_per_ep * mins_per_clip / 60
out.append(f"    单卡 3090 出片 19.3 分钟/段 -> 约 {hours:,.0f} 小时（约 {hours/24:,.0f} 天）")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\cost.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote")
