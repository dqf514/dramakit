"""Make an episode five minutes long, with shots that can breathe.

Everything about the scale was set for a thirty second episode: the
script budget, the number of shots, the length of a shot and the limits
the QA checks. A five minute drama needs a different set of numbers, and
a shot that holds one long take instead of a cut every two seconds.
"""
from pathlib import Path

# 1) the config: the episode is five minutes now
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")

old = """    episode_duration: float = 90.0                    # seconds, for fixed_duration/auto"""
new = """    episode_duration: float = 300.0                   # 一集的目标时长（5 分钟）"""
assert old in s, "episode_duration 锚点没找到"
s = s.replace(old, new, 1)

old = """    min_episode_duration: float = 45.0"""
new = """    min_episode_duration: float = 180.0"""
assert old in s, "min_episode 锚点没找到"
s = s.replace(old, new, 1)

old = """    max_episode_duration: float = 180.0"""
new = """    max_episode_duration: float = 360.0"""
assert old in s, "max_episode 锚点没找到"
s = s.replace(old, new, 1)

old = """    max_episode_seconds: float = 60.0"""
new = """    max_episode_seconds: float = 330.0"""
assert old in s, "max_episode_seconds 锚点没找到"
s = s.replace(old, new, 1)

old = """    max_episode_seconds: float = 60.0"""
# the compose section has its own copy
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py: 一集 5 分钟")

# 2) the storyboard: many more shots, and a shot may be a long take
old = """    # 一集最多几个镜头：短剧靠快切留人，平均 2~3 秒一刀，
    # 三十多秒的一集要十几个镜头才切得起来
    max_shots_per_episode: int = 14"""
new = """    # 一集最多几个镜头：一集五分钟，按镜头三到五秒算要六七十个
    max_shots_per_episode: int = 90"""
assert old in s, "max_shots_per_episode 锚点没找到"
s = s.replace(old, new, 1)

old = """    max_shots_per_scene: int = 10"""
new = """    max_shots_per_scene: int = 26"""
assert old in s, "max_shots_per_scene 锚点没找到"
s = s.replace(old, new, 1)

old = """    shot_duration_range: list[float] = Field(default_factory=lambda: [2.5, 6.0])"""
new = """    # 镜头可以很长：一句台词说完，镜头可以停在脸上继续演
    shot_duration_range: list[float] = Field(default_factory=lambda: [2.5, 15.0])"""
assert old in s, "时长区间锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py: 镜头 2.5~15 秒，每集 90 镜")

# 3) the yaml
p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
repl = [
    ("  episode_duration: 90", "  episode_duration: 300"),
    ("  min_episode_duration: 45", "  min_episode_duration: 180"),
    ("  max_episode_duration: 180", "  max_episode_duration: 360"),
    ("  max_episode_seconds: 60", "  max_episode_seconds: 330"),
    ("  max_shots_per_episode: 14", "  max_shots_per_episode: 90"),
    ("  max_shots_per_scene: 10", "  max_shots_per_scene: 26"),
    ("  shot_duration_range: [2.5, 6.0]", "  shot_duration_range: [2.5, 15.0]"),
]
for old, new in repl:
    if old in s:
        s = s.replace(old, new, 1)
    else:
        print(f"  yaml 没找到: {old}")
p.write_text(s, encoding="utf-8")
print("yaml 已改")
