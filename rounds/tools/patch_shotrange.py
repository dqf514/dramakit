"""Let a shot be a little longer - the episode needs to breathe."""
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")
old = "  shot_duration_range: [2.0, 4.0]"
new = "  shot_duration_range: [2.5, 6.0]"
assert old in s, "时长区间锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml: 镜头时长区间 2.5~6.0")

p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    shot_duration_range: list[float] = Field(default_factory=lambda: [2.0, 4.0])"""
new = """    shot_duration_range: list[float] = Field(default_factory=lambda: [2.5, 6.0])"""
assert old in s, "config 时长区间锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py: 镜头时长区间 2.5~6.0")
