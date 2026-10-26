"""Patch promptgen so each shot knows what the previous one ended with."""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\promptgen.py")
lines = p.read_text(encoding="utf-8").splitlines()


def find(needle, start=0):
    for j in range(start, len(lines)):
        if needle in lines[j]:
            return j
    raise SystemExit(f"锚点没找到: {needle}")


# 1) the jobs.append tuple gains the continuity
j = find("jobs.append((shot, sc, visuals, flf, location_visual,")
assert "need_img, need_h3))" in lines[j + 1], lines[j + 1]
new = [
    "                # the shot before it decides where the people are standing:",
    "                # without it the same conversation keeps re-posing itself",
    '                continuity = prev_action[:180] if prev_action else ""',
    lines[j + 1].replace("need_img, need_h3))", "need_img, need_h3, continuity))"),
    "                prev_action = shot.action or prev_action",
]
lines[j + 1:j + 2] = new

# 2) the worker unpacks it
j = find("shot, sc, visuals, flf, location_visual, need_img, need_h3 = job")
lines[j] = lines[j].replace("need_img, need_h3 = job", "need_img, need_h3, cont = job")
k = find("_gen_image_prompt(ctx, llm, shot, sc, visuals, flf, location_visual)")
lines[k] = ("                _gen_image_prompt(ctx, llm, shot, sc, visuals, flf, "
            "location_visual,\n                                  continuity=cont)")
k = find("_gen_h3_prompt(ctx, llm, shot, sc, visuals, location_visual,")
lines[k + 1] = "                               dlg_map.get(shot.id, []), continuity=cont)"

# 3) the H3 helper takes the continuity
j = find("def _gen_h3_prompt(ctx: Context, llm, shot: Shot, sc, visuals: str,")
assert "location_visual: str, lines: list[tuple[str, str]]) -> None:" in lines[j + 1]
lines[j + 1] = ("                   location_visual: str, lines: list[tuple[str, str]],"
                '\n                   continuity: str = "") -> None:')

# 4) and passes it on
j = find("dialogue=dlg_text, dialogue_note=note)")
lines[j] = "            dialogue=dlg_text, dialogue_note=note, continuity=continuity)"

p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("promptgen.py 已打补丁")
