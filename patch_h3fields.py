"""Feed the H3 prompt the timeline, the jobs of the references and the rules."""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\promptgen.py")
s = p.read_text(encoding="utf-8")

old = """        h3_user = T.render(
            T.H3_VIDEO_USER,
            shot_type=shot.shot_type.value, camera_move=shot.camera_move,
            action=shot.action, character_anchors=visuals,
            location=sc.location or "场景",
            location_visual=location_visual or "（按剧情合理生成）",
            scene_summary=sc.summary or "", time_of_day=sc.time_of_day,
            style=ad.style_prompt_prefix or ad.style, era=ad.era,
            color_palette=ad.color_palette, mood=sc.mood,
            dialogue=dlg_text, dialogue_note=note, continuity=continuity)"""
new = """        h3_user = T.render(
            T.H3_VIDEO_USER,
            shot_type=shot.shot_type.value, camera_move=shot.camera_move,
            action=shot.action, character_anchors=visuals,
            location=sc.location or "场景",
            location_visual=location_visual or "（按剧情合理生成）",
            scene_summary=sc.summary or "", time_of_day=sc.time_of_day,
            style=ad.style_prompt_prefix or ad.style, era=ad.era,
            color_palette=ad.color_palette, mood=sc.mood,
            dialogue=dlg_text, dialogue_note=note, continuity=continuity,
            duration=_shot_seconds(shot),
            references=_reference_jobs(shot),
            timeline=_shot_timeline(shot, lines),
            constraints=H3_CONSTRAINTS)"""
assert old in s, "H3 render 锚点没找到"
s = s.replace(old, new, 1)

helpers = '''
# The rules that stop the drift, written at the end of the prompt where the
# official guide says they work best.
H3_CONSTRAINTS = (
    "保持人物身份、脸部、发型与服装和第一帧完全一致；"
    "画面里不出现除第一帧已有文字以外的新文字，也不加字幕和水印；"
    "不出现多余人物、多余肢体或畸形的手；"
    "镜头不抖动、不跳帧、不慢动作；"
    "不要切换到别的场景或别的机位。"
)


def _shot_seconds(shot) -> float:
    """How long the shot is, for the prompt's timeline."""
    try:
        return max(1.0, float(shot.duration or 3.0))
    except (TypeError, ValueError):
        return 3.0


def _reference_jobs(shot) -> str:
    """Say what each reference is for - and what it is not for."""
    n = len(shot.characters or [])
    if n:
        return (f"图片1 到 图片{n} 是人物定妆参考，锁定人物的脸、发型与服装；"
                f"图片{n+1} 以后是场景与光影参考，只用它的环境与光线，"
                "不要借用里面的服装、人物或文字。")
    return ("图片1 是场景与光影参考，只用它的环境与光线，"
            "不要借用里面的文字或人物。")


def _shot_timeline(shot, lines) -> str:
    """The beat by beat timeline, matching the length of the clip."""
    dur = _shot_seconds(shot)
    if not lines:
        return (f"0-{dur:.1f}秒：{shot.action[:40]}，角色不说话，"
                "只用表情、眼神和动作推进")
    seg = dur / len(lines)
    out = []
    for i, (spk, _txt) in enumerate(lines[:4]):
        out.append(f"{i*seg:.1f}-{(i+1)*seg:.1f}秒：{spk} 开口说这句台词")
    if len(lines) > 4:
        out.append(f"之后到 {dur:.1f}秒：保持情绪与姿态")
    return "；".join(out)


'''

old = "def _gen_h3_prompt(ctx: Context, llm, shot: Shot, sc, visuals: str,"
assert old in s, "_gen_h3_prompt 锚点没找到"
s = s.replace(old, helpers.lstrip("\n") + "\n" + old, 1)

p.write_text(s, encoding="utf-8")
print("promptgen.py 已打补丁")
