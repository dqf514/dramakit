"""Let the storyboard cut at the speed of a reference film."""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\prompts\templates.py")
s = p.read_text(encoding="utf-8")

old = "- 镜头时长之和应≈本场台词总时长({{narration_seconds}}秒)"
new = """- 镜头时长之和应≈本场台词总时长({{narration_seconds}}秒)
{% if ref_rhythm %}
- **参考片的剪辑节奏（照着这个速度切）**：平均 {{ref_avg}} 秒一刀，中位 {{ref_median}} 秒，
  最长不超过 {{ref_max}} 秒，开场第一个镜头 {{ref_open}} 秒，每分钟约 {{ref_cpm}} 刀。
  本集的镜头要切得和它一样密。
{% endif %}"""
assert old in s, "镜头时长锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# the storyboard stage passes the numbers in
p = Path(r"E:\dramakit\dramakit\pipeline\storyboard.py")
s = p.read_text(encoding="utf-8")
old = """            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            time_of_day=sc.time_of_day, mood=sc.mood, summary=sc.summary,
                            lines_text=lines_text, min_shots=cfg.min_shots_per_scene,
                            max_shots=max_shots, prefer_dynamic=prefer,
                            dur_min=dmin, dur_max=dmax, narration_seconds=narration_sec,
                            character_names=char_names)"""
new = """            user = T.render(T.STORYBOARD_USER, location=sc.location or "场景",
                            time_of_day=sc.time_of_day, mood=sc.mood, summary=sc.summary,
                            lines_text=lines_text, min_shots=cfg.min_shots_per_scene,
                            max_shots=max_shots, prefer_dynamic=prefer,
                            dur_min=dmin, dur_max=dmax, narration_seconds=narration_sec,
                            character_names=char_names,
                            **_ref_rhythm_args(cfg.ref_rhythm))"""
assert old in s, "storyboard render 锚点没找到"
s = s.replace(old, new, 1)

helper = '''

def _ref_rhythm_args(profile: dict) -> dict:
    """The numbers of a reference film's rhythm, for the storyboard."""
    if not profile or not profile.get("shots"):
        return {"ref_rhythm": False}
    return {
        "ref_rhythm": True,
        "ref_avg": profile.get("avg_shot", 3.0),
        "ref_median": profile.get("median_shot", 3.0),
        "ref_max": profile.get("max_shot", 5.0),
        "ref_open": profile.get("opening_shot", 2.0),
        "ref_cpm": profile.get("cuts_per_min", 24),
    }

'''
old = "\ndef run(ctx: Context) -> dict:"
assert old in s, "run 锚点没找到"
s = s.replace(old, helper + "\ndef run(ctx: Context) -> dict:", 1)
p.write_text(s, encoding="utf-8")
print("模板与分镜已打补丁")
