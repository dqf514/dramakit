"""Does the model answer?  And can it write a shot list?

The storyboard rules are only worth what the model does with them, so
this asks the model for a shot list of its own and prints what came
back: the sizes, the angles and who each shot is on.
"""
import json
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.prompts import templates as T
from dramakit.providers.llm import OpenAICompatLLM

cfg = Config.load(r"E:\dramakit\config\default.yaml")
print("端点:", cfg.llm.base_url, "| 模型:", cfg.llm.model)

llm = OpenAICompatLLM(cfg.llm)

LINES = "\n".join([
    "- 1. 苏念(愤怒): 你到底想怎样",
    "- 2. 陆沉(冷): 我想要你签了这份合同",
    "- 3. 苏念(怒): 做梦",
    "- 4. 陆沉(冷): 你没得选",
])

user = T.render(
    T.STORYBOARD_USER,
    location="苏念家客厅", time_of_day="夜", mood="紧张",
    summary="苏念发现陆沉拿她父亲的医药费逼她签合同",
    lines_text=LINES,
    min_shots=4, max_shots=8,
    episode_seconds=300, avg_seconds=3.5, scene_seconds=30,
    scene_avg=3.8, scene_shots=8,
    prefer_dynamic="多用运动镜头增强节奏",
    dur_min=2.0, dur_max=5.0, narration_seconds=8.0,
    character_names="苏念, 陆沉",
    director_rules="",
    ref_rhythm=False,
)

try:
    data = llm.complete_json(T.STORYBOARD_SYSTEM, user)
except Exception as e:  # noqa: BLE001
    print("模型没答上:", type(e).__name__, str(e)[:300])
    raise SystemExit(1)

if isinstance(data, list):
    data = data[0] if data else {}
shots = data.get("shots") or []
print(f"\n模型给了 {len(shots)} 镜：\n")
for i, s in enumerate(shots, 1):
    print(f"  {i}. {s.get('shot_type','?'):4} {s.get('angle','?'):4} "
          f"{s.get('height','?'):3} {s.get('lens','?'):3} "
          f"主体={s.get('subject','?'):6} "
          f"线={s.get('lines', [])}  "
          f"职责={s.get('purpose','')}")
    print(f"     动作: {str(s.get('action',''))[:100]}")
    print(f"     人物: {s.get('characters', [])}")

print("\n原始 JSON 里有没有 angle 字段:",
      "angle" in json.dumps(shots, ensure_ascii=False))

# what the mechanical rules do to it
from dramakit.models import Line, Scene, Shot, ShotType
from dramakit.pipeline import storyboard as sb

sc = Scene(id="sc-1", index=1, location="苏念家客厅", time_of_day="夜",
           summary="对峙")
sc.lines = [
    Line(id="l1", speaker="苏念", text="你到底想怎样", emotion="愤怒"),
    Line(id="l2", speaker="陆沉", text="我想要你签了这份合同", emotion="冷"),
    Line(id="l3", speaker="苏念", text="做梦", emotion="怒"),
    Line(id="l4", speaker="陆沉", text="你没得选", emotion="冷"),
]
for i, s in enumerate(shots):
    idxs = []
    for v in (s.get("lines") or []):
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= len(sc.lines) and n not in idxs:
            idxs.append(n)
    sc.shots.append(Shot(
        id=f"sh-{i}", index=i, shot_type=sb._to_shot_type(s.get("shot_type", "中景")),
        camera_move=s.get("camera_move", "固定"),
        angle=sb._to_angle(s.get("angle", "")), height=sb._to_height(s.get("height", "")),
        lens=sb._to_lens(s.get("lens", "")),
        purpose=s.get("purpose", ""), subject=s.get("subject", ""),
        duration=float(s.get("duration") or 3.0),
        action=sb._strip_facing_camera(s.get("action", "")),
        characters=[str(c) for c in (s.get("characters") or [])],
        line_indices=idxs))

before = [(s.shot_type.value, s.angle, s.subject) for s in sc.shots]
changed = sb._enforce_coverage(sc)
after = [(s.shot_type.value, s.angle, s.subject) for s in sc.shots]
print(f"\n机械约束改了 {changed} 处：")
for i, (b, a) in enumerate(zip(before, after), 1):
    mark = "  " if b == a else "→ "
    print(f"  {i}. {mark}{b}  {a if b != a else ''}")
