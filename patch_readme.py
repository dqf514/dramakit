"""Refresh the QA section of the rounds README."""
from pathlib import Path

p = Path(r"E:\dramakit\rounds\README.md")
s = p.read_text(encoding="utf-8")

old = """- 素材是否够长到填满它的槽位（不够就是冻帧）
- 台词是不是切在镜头边界上（不是就说明画面停在上一句的镜头上）
"""
new = """- 素材是否够长到填满它的槽位（不够就是冻帧）
- 台词是不是切在镜头边界上（不是就说明画面停在上一句的镜头上）
- **景别**：连续三个同景别要报出来（那叫证件照连播）；第一镜不能是特写
- **节奏**：平均一刀多少秒、开场第一个镜头多长、前 3 秒切了几刀
- **钩子**：第一句台词是不是在 3 秒内出现、有没有太长
"""
assert old in s, "画面锚点没找到"
s = s.replace(old, new, 1)

old = """- 字幕之间会不会重叠、会不会比配音先消失
"""
new = """- 字幕之间会不会重叠、会不会比配音先消失
- **位置**：字幕必须落在画面下方三分之一（曾经落在 60% 高度，正好挡住脸）
"""
assert old in s, "字幕锚点没找到"
s = s.replace(old, new, 1)

old = """**叙事**
- 说话的人是不是在画面里（按角色整体比例判定，单个反应镜头是正常剪辑）
"""
new = """**叙事 / 合规**
- 说话的人是不是在画面里（按角色整体比例判定，单个反应镜头是正常剪辑）
- 可能过不了审的措辞（2026 年平台审"整剧立意"，敏感词会下架）

## 工具

```bash
# 拉片：量参考片的剪辑节奏，写进分镜提示词
dj ref-rhythm 参考片.mp4 --apply

# 一集成片的进度与体检
dj status 项目名
```
"""
assert old in s, "叙事锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("README 已更新")
