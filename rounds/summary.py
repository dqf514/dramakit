"""Compare every round: what the QA measured and what changed."""
import json
import re
import sys
from pathlib import Path

ROUNDS = Path(r"E:\dramakit\rounds")


def load():
    out = []
    for p in sorted((ROUNDS / "reports").glob("round*.qa.json")):
        try:
            out.append((int(re.search(r"round(\d+)", p.name).group(1)),
                        json.loads(p.read_text(encoding="utf-8"))))
        except Exception as e:  # noqa: BLE001
            print(f"跳过 {p.name}: {e}")
    return out


# what each round turned up, and what was changed because of it
FIXES = [
    (1, "一次 CUDA 显存溢出打死了整集（画面缺一个镜头）",
     "出图/出视频加自动重试；ComfyUI 启动加 --vram-headroom 1.5"),
    (1, "音乐垫底只比对白低 6.4 LU，音乐在盖人声",
     "垫底改为按每集实测自动配平，稳定在 12 LU"),
    (1, "剧本写了 22 句、分镜摊成 10 镜，信息量失控",
     "剧本与分镜都拿到时长预算，台词按预算收敛"),
    (2, "两个 LLM 调用串行，promptgen 慢到 10 分钟",
     "同一镜的两次调用与不同镜之间全部并行"),
    (3, "统一调色把镜头间差异放大了（亮度差 29 → 48.8）",
     "弃用 eq=contrast（绕中灰缩放），改用饱和度+白平衡+最后统一曝光，亮度差降到 6"),
    (4, "多场景时配音轨互相覆盖，第 2 轮丢了 22 秒对白",
     "每个场景单独的配音文件；质检加「成片长度必须等于时间线」"),
    (5, "素材比槽位短，画面被冻住；mux 取短的那条把结尾切掉",
     "补帧量按素材实际长度算；合成前两轨都补齐到时间线长度"),
    (6, "一句台词的音频写入被拒（WinError 5），整集报废",
     "每句配音多次重试，音频改成原子写；合成前两轨都补齐到时间线长度"),
    (6, "一集跑到 69 秒，超出一集短剧的长度",
     "剧本预算上限改成一分钟，质检加长度检查"),
    (7, "台词和镜头各走各的：换了说话人却没切镜（8~13 句）",
     "分镜声明每个镜头承载哪几句台词，镜头长度由台词决定，切点落在台词边界"),
    (7, "画面先拍、配音后录，两份时间线对不上",
     "阶段顺序改成先录音再拍"),
    (8, "H3 被要求描述角色说话，于是自己念出乱码语音压住配音",
     "H3 提示词只描述表情和动作，不出现任何发声描述"),
    (8, "同一场对话里人物一会儿站一会儿趴，站位乱跳",
     "下一镜的提示词带上上一镜结束时的状态"),
    (9, "复合情绪标签（\"冷笑（愤怒）\"）查不到映射，等于没有情绪",
     "情绪解析拆出括号里的本体；映射表补齐常用说法"),
    (9, "镜头偏长（5.6~19 秒），短剧的节奏被拖垮",
     "分镜规则限制单镜最多承载 2 句台词；质检加节奏检查"),
    (10, "字幕落在画面 60% 高度，正好挡住脸",
     "边距按字高算，紧贴底部一个文字高"),
    (10, "字幕上方的角色名重复了声音已经说过的事",
     "移除"),
    (10, "说话没有口型（H3 提示词被要求不要描述发声）",
     "恢复\"说话时的表演\"描述，画面里才有对得上的口型"),
    (10, "H3 自己念出乱码语音，压在配音上",
     "每场单独生成\"无人无声\"的纯配乐镜头做垫底，镜头原生音弃用"),
    (10, "台词背靠背，像在念清单",
     "每句之间留 0.35 秒呼吸"),
    (10, "八镜里六镜是特写近景，像证件照连播",
     "分镜强制景别变化、对话戏正反打；第一镜交代环境且人物开口"),
    (11, "节奏只有 12 刀/分（爆款要 20~40）",
     "单镜对白不超过 3.5 秒、一集最多 14 镜"),
    (11, "声音只有台词和音乐，缺了音效这一层",
     "配乐镜头带上本场关键动作的声音"),
    (11, "AI 生成没有标注（2026 年平台强制要求）",
     "成片片头烧上 AI 生成声明与备案号"),
    (11, "出图比例与成片比例各写各的，竖屏会裁掉人脸",
     "出图尺寸跟着成片尺寸走"),
    (11, "控制台进度条显示 58%，其实全部做完了",
     "项目级与集级阶段一起统计，阶段表补齐"),
    (11, "拉片：学不到参考片的节奏",
     "新增 dj ref-rhythm，把参考片的刀数与开场写进分镜提示词"),
]


def write_markdown(rows) -> Path:
    """A human-readable report of every round."""
    out = ROUNDS / "总报告.md"
    lines = ["# 10 轮短剧全链路迭代报告", "",
             "每轮：换剧本 → 全流水线 → 自动质检 → 改代码 → 下一轮。",
             "",
             "所有素材都在 `projects/轮次NN_*` 下：角色定妆照、场景参考图、每镜首帧、",
             "每段视频、逐句配音、字幕文件、成片、FCPXML，可逐一回看。",
             "",
             "## 汇总", "",
             "| 轮 | 项目 | 题材 | 结论 | 问题 | 成片/时间线 | 对白−垫底 | 相对锐度 | 亮度差 | 字幕 | 音轨 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, rep in rows:
        e = rep["episodes"][0] if rep["episodes"] else {}
        m = e.get("mix") or {}
        p = e.get("picture") or {}
        s = e.get("subtitle") or {}
        nl = e.get("nle") or {}
        au = m.get("audibility") or {}
        c = e.get("completeness") or {}
        title = (e.get("title") or "")[:16]
        lines.append(
            f"| {n} | {rep['project'][:14]} | {title} | {rep['verdict']} | "
            f"{rep['issue_count']} | {c.get('duration','-')} / {c.get('timeline','-')}s | "
            f"{au.get('gap_lu','-')} LU | {p.get('sharp_median','-')} | "
            f"{p.get('luma_spread','-')} | {s.get('cues','-')} | "
            f"{len(nl.get('lanes', []))} |")
    lines += ["", "## 逐轮问题与处理", ""]
    for n, rep in rows:
        lines.append(f"### 第 {n} 轮 · {rep['project']} — {rep['verdict']}")
        lines.append("")
        if not rep["issues"]:
            lines.append("无问题。")
            lines.append("")
            continue
        for i in rep["issues"]:
            lines.append(f"- **{i['area']}/{i['kind']}** ({i['where']}): {i['detail']}")
        lines.append("")
    lines += ["", "## 这一轮迭代改掉的东西", "",
              "| 轮 | 发现的问题 | 改法 |", "|---|---|---|"]
    for n, found, fix in FIXES:
        lines.append(f"| {n} | {found} | {fix} |")
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    rows = load()
    if not rows:
        print("还没有质检报告")
        return
    print(f"{'轮':>3} {'项目':22s} {'结论':7s} {'问题':>4} "
          f"{'响度':>7} {'对白段':>7} {'垫底段':>7} {'差LU':>6} "
          f"{'锐度中位':>8} {'亮度差':>7} {'字幕':>5} {'音轨':>5} "
          f"{'成片秒':>7} {'时间线秒':>8}")
    print("-" * 116)
    for n, rep in rows:
        e = rep["episodes"][0] if rep["episodes"] else {}
        m = e.get("mix") or {}
        p = e.get("picture") or {}
        s = e.get("subtitle") or {}
        nl = e.get("nle") or {}
        au = m.get("audibility") or {}
        c = e.get("completeness") or {}

        def g(d, k):
            v = (d.get(k) if isinstance(d, dict) else None)
            return f"{v}" if v is not None else "-"

        print(f"{n:>3} {rep['project'][:22]:22s} {rep['verdict']:7s} {rep['issue_count']:>4} "
              f"{g(m.get('episode',{}),'i'):>7} {str(au.get('speech_lufs','-')):>7} "
              f"{str(au.get('bed_lufs','-')):>7} {str(au.get('gap_lu','-')):>6} "
              f"{str(p.get('sharp_median','-')):>8} {str(p.get('luma_spread','-')):>7} "
              f"{str(s.get('cues','-')):>5} {str(len(nl.get('lanes',[]))):>5} "
              f"{str(c.get('duration','-')):>7} {str(c.get('timeline','-')):>8}")
    print("-" * 116)
    print("\n逐轮问题:")
    for n, rep in rows:
        kinds = {}
        for i in rep["issues"]:
            kinds.setdefault(f"{i['area']}/{i['kind']}", []).append(i["detail"])
        print(f"  第{n:>2}轮 ({rep['verdict']}):")
        if not kinds:
            print("     无")
        for k, v in kinds.items():
            print(f"     {k}: {v[0][:70]}" + (f"  (共{len(v)}处)" if len(v) > 1 else ""))
    md = write_markdown(rows)
    print(f"\n总报告: {md}")


if __name__ == "__main__":
    main()
