"""More shots per episode, and the QA holds the line on the cutting speed."""
from pathlib import Path

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

print("配置与质检已改")
