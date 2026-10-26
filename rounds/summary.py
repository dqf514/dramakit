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


def main():
    rows = load()
    if not rows:
        print("还没有质检报告")
        return
    print(f"{'轮':>3} {'项目':22s} {'结论':7s} {'问题':>4} "
          f"{'响度':>7} {'对白':>7} {'音乐':>7} {'锐度中位':>8} {'亮度差':>7} {'字幕':>5} {'音轨':>5}")
    print("-" * 108)
    for n, rep in rows:
        e = rep["episodes"][0] if rep["episodes"] else {}
        m = e.get("mix") or {}
        p = e.get("picture") or {}
        s = e.get("subtitle") or {}
        nl = e.get("nle") or {}
        def g(d, k):
            v = (d.get(k) or {}).get("i")
            return f"{v}" if v is not None else "-"
        print(f"{n:>3} {rep['project'][:22]:22s} {rep['verdict']:7s} {rep['issue_count']:>4} "
              f"{g(m.get('episode',{}),'i'):>7} {g(m.get('voice',{}),'i'):>7} {g(m.get('music',{}),'i'):>7} "
              f"{str(p.get('sharp_median','-')):>8} {str(p.get('luma_spread','-')):>7} "
              f"{str(s.get('cues','-')):>5} {str(len(nl.get('lanes',[]))):>5}")
    print("-" * 108)
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


if __name__ == "__main__":
    main()
