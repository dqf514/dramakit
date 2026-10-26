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


def write_markdown(rows) -> Path:
    """A human-readable report of every round."""
    out = ROUNDS / "总报告.md"
    lines = ["# 10 轮短剧全链路迭代报告", "",
             "每轮：换剧本 → 全流水线 → 自动质检 → 改代码 → 下一轮。", "",
             "## 汇总", "",
             "| 轮 | 项目 | 题材 | 结论 | 问题 | 成片响度 | 对白/垫底差 | 锐度中位 | 亮度差 | 字幕条 | 音轨 |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, rep in rows:
        e = rep["episodes"][0] if rep["episodes"] else {}
        m = e.get("mix") or {}
        p = e.get("picture") or {}
        s = e.get("subtitle") or {}
        nl = e.get("nle") or {}
        au = m.get("audibility") or {}
        title = (e.get("title") or "")[:18]
        lines.append(
            f"| {n} | {rep['project'][:16]} | {title} | {rep['verdict']} | "
            f"{rep['issue_count']} | {au.get('speech_lufs', '-')} / {au.get('gap_lu', '-')} LU | "
            f"{p.get('sharp_median', '-')} | {p.get('luma_spread', '-')} | "
            f"{s.get('cues', '-')} | {len(nl.get('lanes', []))} |")
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
