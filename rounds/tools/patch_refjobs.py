"""The prompt has to say what each picture is for.

The list is now: the still the shot continues from, then the faces of the
people in it, then the room.  So the prompt says that - the still is the
composition, the faces are the identity, the room is the place.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\promptgen.py")
s = p.read_text(encoding="utf-8")

old = '''def _reference_jobs(shot) -> str:
    """Say what each reference is for - and what it is not for."""
    n = len(shot.characters or [])
    if n:
        return (f"图片1 到 图片{n} 是人物定妆参考，锁定人物的脸、发型与服装；"
                f"图片{n+1} 以后是场景与光影参考，只用它的环境与光线，"
                "不要借用里面的服装、人物或文字。")
    return ("图片1 是场景与光影参考，只用它的环境与光线，"
            "不要借用里面的文字或人物。")'''

new = '''def _reference_jobs(shot, plan=None) -> str:
    """Say what each reference is for - and what it is not for."""
    kinds = [k for _p, _w, k in (plan or [])]
    n_face = kinds.count("character")
    n_room = kinds.count("room")
    bits = []
    if "frame" in kinds:
        bits.append("图片1 是这一镜的首帧：构图、站位、服装、光线都以它为准")
    if n_face:
        lo = 2 if "frame" in kinds else 1
        bits.append(f"图片{lo} 到 图片{lo + n_face - 1} 是画面里人物的面部特写，"
                    f"锁定他们的脸、发型与服装")
    if n_room:
        lo = (2 if "frame" in kinds else 1) + n_face
        bits.append(f"图片{lo} 是场景与光影参考，只用它的环境与光线，"
                    "不要借用里面的服装、人物或文字")
    if not bits:
        bits.append("图片1 是场景与光影参考，只用它的环境与光线，"
                    "不要借用里面的文字或人物")
    return "；".join(bits) + "。"'''

assert old in s, "参考图分工锚点没找到"
s = s.replace(old, new, 1)

# and the call site passes the list
old2 = """            references=_reference_jobs(shot),"""
new2 = """            references=_reference_jobs(shot, _plan_for(ctx, shot, sc)),"""
assert old2 in s, "参考图分工调用锚点没找到"
s = s.replace(old2, new2, 1)

# the helper
old3 = """def _gen_h3_prompt(ctx: Context, llm, shot: Shot, sc, visuals: str,"""
new3 = '''def _plan_for(ctx: Context, shot: Shot, sc) -> list[tuple[str, str, str]]:
    """The pictures this shot is given, in the order they are given."""
    from .refs import picture_plan
    try:
        return picture_plan(ctx, shot, sc)
    except Exception:  # noqa: BLE001
        return []


def _gen_h3_prompt(ctx: Context, llm, shot: Shot, sc, visuals: str,'''
assert old3 in s, "提示词函数锚点没找到"
s = s.replace(old3, new3, 1)

p.write_text(s, encoding="utf-8")
print("promptgen.py: 参考图分工按新清单写了")
