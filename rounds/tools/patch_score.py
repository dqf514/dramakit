"""The music bed must never be missing.

The score prompt was one LLM call among a dozen, and when that call came
back empty the episode quietly lost its music. It is retried now, and if
the model still will not answer, the prompt is written from the scene
itself.
"""
from pathlib import Path

p = Path(r"E:\dramakit\dramakit\pipeline\promptgen.py")
s = p.read_text(encoding="utf-8")

old = '''    user = T.render(T.H3_SCORE_USER, location=sc.location or "场景",
                    time_of_day=sc.time_of_day,
                    location_visual=location_visual or "（按剧情合理生成）",
                    mood=sc.mood, scene_summary=sc.summary or "",
                    scene_actions="；".join(actions) or "（无特别动作）",
                    style=ad.style_prompt_prefix or ad.style)
    try:
        data = llm.complete_json(T.H3_SCORE_SYSTEM, user)
        if isinstance(data, list):
            data = data[0] if data else {}
        desc = str(data.get("integrated_multimodal_description") or "").strip()
        soundscape = str(data.get("overall_soundscape") or "").strip()
        music = str(data.get("non_diegetic_music") or "").strip()
        if desc:
            sc.score_prompt = _assemble_h3_prompt(desc, soundscape or "N/A",
                                                  music or "N/A")
    except Exception as e:  # noqa: BLE001
        ctx.log.warning("promptgen: 场%d 配乐提示词失败(%s)", sc.index, str(e)[:120])'''

new = '''    user = T.render(T.H3_SCORE_USER, location=sc.location or "场景",
                    time_of_day=sc.time_of_day,
                    location_visual=location_visual or "（按剧情合理生成）",
                    mood=sc.mood, scene_summary=sc.summary or "",
                    scene_actions="；".join(actions) or "（无特别动作）",
                    style=ad.style_prompt_prefix or ad.style)
    for attempt in range(3):
        try:
            data = llm.complete_json(T.H3_SCORE_SYSTEM, user)
            if isinstance(data, list):
                data = data[0] if data else {}
            desc = str(data.get("integrated_multimodal_description") or "").strip()
            soundscape = str(data.get("overall_soundscape") or "").strip()
            music = str(data.get("non_diegetic_music") or "").strip()
            if desc:
                sc.score_prompt = _assemble_h3_prompt(desc, soundscape or "N/A",
                                                      music or "N/A")
                return
        except Exception as e:  # noqa: BLE001
            ctx.log.warning("promptgen: 场%d 配乐提示词失败(%s)，重试",
                            sc.index, str(e)[:120])
        time.sleep(2.0 * (attempt + 1))
    # the model will not answer: write the prompt from the scene itself, the
    # episode still gets its music
    sc.score_prompt = _assemble_h3_prompt(
        f"[Shot 1] An empty {sc.location} at {sc.time_of_day}, "
        f"{location_visual or 'an ordinary interior'}. The camera drifts "
        "slowly through the empty space. No people, no characters, no voices.",
        f"Ambient sound of {sc.location} at {sc.time_of_day}"
        + (f", with the sounds of {actions[0]}" if actions else ""),
        f"Emotional underscore for {sc.mood}: restrained, slow build.")
    ctx.log.warning("promptgen: 场%d 配乐提示词用兜底模板", sc.index)'''

assert old in s, "配乐提示词锚点没找到"
s = s.replace(old, new, 1)

if "\nimport time\n" not in s:
    s = s.replace("import hashlib\n", "import hashlib\nimport time\n", 1)

p.write_text(s, encoding="utf-8")
print("promptgen.py 已打补丁")
