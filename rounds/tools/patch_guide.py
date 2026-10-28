"""Refresh the guide: the ninth round is now a vertical drama."""
from pathlib import Path

p = Path(r"E:\\dramakit\\rounds\\看片指南.md")
s = p.read_text(encoding="utf-8")

old = """# 看片指南：10 轮迭代的成片在哪、看什么

每一轮的正片在 `E:\\dramakit\\projects\\轮次NN_NN\\episodes\\ep_001.mp4`。
同一集的全部中间素材在同一个项目目录里，可以逐项回看。"""
new = """# 看片指南：成片在哪、看什么

每一轮的正片在 `E:\\dramakit\\projects\\轮次NN_NN\\episodes\\ep_001.mp4`。
同一集的全部中间素材在同一个项目目录里，可以逐项回看。

> **第 9 轮是竖屏的**（1080×1920，36 秒，13 个镜头）——它是被反复迭代了五遍的
> 那一个片子，从横屏改回竖屏、加了口型对齐、修了空间连续性。
> 其它九轮是改竖屏之前跑的，横屏。"""
assert old in s, "头部锚点没找到"
s = s.replace(old, new, 1)

old = """| 9 | 退婚 | ~33s | 霸总：退婚、三个月赌约、股份 |"""
new = """| 9 | 退婚 | ~36s | 霸总：退婚、三个月赌约、股份（**竖屏，反复迭代的那一集**） |"""
assert old in s, "轮次表锚点没找到"
s = s.replace(old, new, 1)

old = """├─ video/shot_sh-xxxxxx.mp4                          H3 生成的那段视频"""
new = """├─ video/shot_sh-xxxxxx.mp4                          H3 生成的那段视频
├─ lipsync/shot_sh-xxxxxx.mp4                        口型对齐后的（MuseTalk 重画的嘴）"""
assert old in s, "目录锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("看片指南已更新")
