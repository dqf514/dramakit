"""Cut faster: the shots were carrying too much dialogue.

The rhythm of the finished episodes was measured at about four seconds a
cut; a short drama runs at two to three. A shot should carry one line,
and the budget has to leave room for that many shots.
"""
from pathlib import Path

# 1) the storyboard is told how much dialogue a shot may carry
p = Path(r"E:\dramakit\dramakit\prompts\templates.py")
s = p.read_text(encoding="utf-8")
old = """- **节奏：一个镜头最多承载 2 句台词，而且这 2 句必须是同一个说话人**。
  的一句约 2~3 秒，所以单镜控制在 3~5 秒。台词多的地方要拆成多个镜头，镜头短、节奏快，
  是短剧留人的关键。连续两个超过 5 秒的镜头会让观众划走。"""
old2 = """- **节奏：一个镜头最多承载 2 句台词，而且这 2 句必须是同一个说话人**。
  （一句约 2~3 秒，所以单镜控制在 3~5 秒）。台词多的地方要拆成多个镜头，镜头短、节奏快，
  是短剧留人的关键。连续两个超过 5 秒的镜头会让观众划走。"""
new = """- **节奏：一个镜头承载的对白不超过 3.5 秒，通常就是 1 句台词**（只有一句特别短时
  才带两句，而且必须是同一个说话人）。短剧的镜头平均 2~3 秒一刀，
  台词多的地方要拆成更多镜头。连续两个超过 4 秒的镜头会让观众划走。"""
if old in s:
    s = s.replace(old, new, 1)
elif old2 in s:
    s = s.replace(old2, new, 1)
else:
    raise SystemExit("节奏规则锚点没找到")
p.write_text(s, encoding="utf-8")

# 2) more shots fit in an episode
p = Path(r"E:\dramakit\dramakit\config.py")
s = p.read_text(encoding="utf-8")
old = """    # 一集最多几个镜头：短剧靠快切留人，镜头太多每段时长就被摊薄了
    max_shots_per_episode: int = 10"""
new = """    # 一集最多几个镜头：短剧靠快切留人，平均 2~3 秒一刀，
    # 三十多秒的一集要十几个镜头才切得起来
    max_shots_per_episode: int = 14"""
assert old in s, "镜头预算锚点没找到"
s = s.replace(old, new, 1)
old = """    max_shots_per_scene: int = 8"""
new = """    max_shots_per_scene: int = 10"""
assert old in s, "每场镜头锚点没找到"
s = s.replace(old, new, 1)
old = """    shot_duration_range: list[float] = Field(default_factory=lambda: [2.0, 5.0])"""
new = """    shot_duration_range: list[float] = Field(default_factory=lambda: [2.0, 4.0])"""
assert old in s, "时长区间锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# 3) the QA holds the line
p = Path(r"E:\dramakit\qa.py")
s = p.read_text(encoding="utf-8")
old = """        limit = 5.5 if len(lines) <= 1 else 7.0"""
new = """        limit = 4.0 if len(lines) <= 1 else 5.0"""
assert old in s, "节奏阈值锚点没找到"
s = s.replace(old, new, 1)
old = """    if p["avg_shot"] > 4.0:"""
new = """    if p["avg_shot"] > 3.5:"""
assert old in s, "平均镜头阈值锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

print("节奏规则已改")
