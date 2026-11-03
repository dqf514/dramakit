"""The two patterns, printed as they really are.

The matcher splits a spot name down to the room it sits in, and strips
punctuation so the same room written two ways still matches. The scene
names in this book join the spot to its weather with a full stop, and the
splitter may not be looking at that character - which would leave the
weather in the room name, and the room in the library would not contain it.

So the patterns are shown as the characters they are, and put against the
real names, rather than read out of a terminal that renders them as boxes.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.pipeline import refs as R   # noqa: E402

out = []

out.append("=== _base 的分隔符正则 ===")
src = R._base.__code__.co_consts
for c in src:
    if isinstance(c, str) and len(c) > 1:
        out.append("  %r" % c)
        out.append("      字符: " + " ".join("%s(U+%04X)" % (ch, ord(ch)) for ch in c))

out.append("")
out.append("=== _norm 的字符类正则 ===")
for c in R._norm.__code__.co_consts:
    if isinstance(c, str) and len(c) > 1:
        out.append("  %r" % c)
        out.append("      字符: " + " ".join("%s(U+%04X)" % (ch, ord(ch)) for ch in c))

out.append("")
out.append("=== 实测：分隔符是否认识「。」===")
tests = ["迷雾之森营地。夜", "迷雾之森营地·夜", "醉月古城街道。雨棚",
         "指挥官办公室", "迷雾之森林地。黄昏"]
for t in tests:
    out.append("  %-16s base=%-16s norm=%s"
               % (t, R._base(t), R._norm(t)))
out.append("")
out.append("  「。」在 base 里被切掉了吗: "
           + str(all("。" not in R._base(t) for t in tests if "。" in t)))
out.append("  「。」在 norm 里被去掉了吗: "
           + str(all("。" not in R._norm(t) for t in tests if "。" in t)))

# and the containment that decides it, on the real names
out.append("")
out.append("=== 真实名字的包含判断 ===")
pairs = [("迷雾之森营地。夜", "迷雾之森·营地"),
         ("迷雾之森林地。黄昏", "迷雾之森·营地"),
         ("迷雾之森外围树林", "迷雾之森·营地"),
         ("奥罗斯旧城上空", "醉月古城街道")]
for scene, asset in pairs:
    b = R._norm(R._base(scene))
    ln = R._norm(asset)
    out.append("  场景 %-16s base=%-14s" % (scene, b))
    out.append("  资产 %-16s norm=%-14s" % (asset, ln))
    out.append("      base in asset: %s   asset in base: %s"
               % (b in ln if ln and b else False,
                  ln in b if ln and b else False))
    out.append("      若先去掉「。」再取 base: %s" % R._norm(R._base(scene.split("。")[0])))
    out.append("")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\patterns.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
