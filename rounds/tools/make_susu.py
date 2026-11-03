"""Give 素素 a card, a voice and a face, and nothing else.

She is in six shots whose prompts all say her appearance comes from her
reference close-ups - and she has no entry, no pictures and no recording,
so those shots cannot be drawn. The book never describes what she looks
like, and neither do the prompts, so the look has to be decided here: she
is the girl 余飞 left on Earth, eighteen, a student in the summer of 2012,
and she appears in episode six as a figure condensing at a window.

Everything else in the cast is left alone. The voice picker only dedupes
within the list it is given, so it is handed the whole cast and her result
checked against the voices already taken - otherwise she can be given
余飞's voice and read as the same person.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.models import Character         # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import character as CH # noqa: E402

out = []
cfg = Config.load(Config.discover())
proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
store = ProjectStore.open(proj)
ctx = Context(cfg, store)

NAME = "素素"
if ctx.project.character(NAME) is not None:
    out.append(f"{NAME} 已存在，跳过创建（只刷新锚点与参考图）")
    char = ctx.project.character(NAME)
else:
    # What she looks like is not in the book and not in the prompts that
    # already reference her, so it is set here: the girl 余飞 left behind,
    # the same age as him, dressed for the summer of 2012.
    char = Character(
        name=NAME,
        role="女主",
        gender="女",
        age="约18岁",
        personality="温柔安静，感情重；说话轻而慢，眼眶常带泪意，"
                     "笑起来有一点克制，像是怕惊动什么",
        appearance="约18岁的中国少女，长直黑发自然垂落，鹅蛋脸，杏眼，睫毛长，"
                   "皮肤白皙，身高中等偏瘦；2012年夏天的学生打扮，"
                   "浅蓝色棉布连衣裙内搭白色短袖衬衫，素净无首饰；"
                   "神情干净温柔，眉眼间有一点挥不去的忧郁",
        visual_prompt=(
            "An 18-year-old Chinese girl with long straight black hair falling "
            "past her shoulders, oval face, gentle almond eyes, fair skin, "
            "slim build, wearing a simple pale-blue cotton dress over a white "
            "short-sleeve blouse, understated student look of the summer of "
            "2012, no jewellery, clean and quiet presence with a trace of "
            "melancholy, realistic cinematic portrait, soft natural light"),
        outfit="浅蓝色棉布连衣裙 + 白色短袖衬衫（2012 夏，学生打扮，无首饰）",
        hair="长直黑发，自然垂落",
    )
    ctx.project.characters.append(char)
    ctx.save()
    out.append(f"已创建 {NAME}（{char.role}，{char.age}）")

# --- a voice, without stealing one -------------------------------------
taken = {c.voice_id for c in ctx.project.characters
         if c.name != NAME and c.voice_id}
before = char.voice_id
CH.cast_voices(ctx, list(ctx.project.characters))
if char.voice_id and char.voice_id in taken:
    out.append(f"  音色 {char.voice_id} 与现有角色冲突，重新分配")
    # hand it something nobody else has, keeping the gender-appropriate pool
    voices, _doc = CH._curated_voices(
        ctx, [v for v in (ctx.providers.tts.list_voices() or [])
              if v not in taken] or [])
    if voices:
        free = [v for v in voices if v not in taken]
        if free:
            char.voice_id = free[0]
    if char.voice_id in taken:
        char.voice_id = ""
out.append(f"  音色: {before or '（新）'} -> {char.voice_id or '未分配'}")

# --- the recording, and the anchor, and the pictures --------------------
made = CH.generate_voice_refs(ctx, [char])
out.append(f"  语音样本: {made}")

res = CH.generate_for_one(store, cfg, NAME)
out.append(f"  锚点与参考图: {json.dumps(res, ensure_ascii=False)[:400]}")

ctx.save()
out.append("")
out.append("=== 最终状态 ===")
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
for c in raw.get("characters") or []:
    if isinstance(c, dict) and c.get("name") == NAME:
        for k in ("name", "role", "gender", "age", "voice_id", "voice_ref",
                  "ref_sheet", "locked"):
            out.append(f"  {k}: {c.get(k)!r}")
        out.append(f"  ref_images ({len(c.get('ref_images') or [])}): "
                   f"{c.get('ref_images')}")
        out.append(f"  anchor_prompt: {str(c.get('anchor_prompt'))[:300]!r}")

# the files on disk
cdir = proj / "characters" / NAME
out.append("")
out.append(f"=== {cdir.name}/ ===")
if cdir.exists():
    for f in sorted(cdir.iterdir()):
        out.append(f"  {f.name:24} {f.stat().st_size/1024:8.0f} KB")
else:
    out.append("  目录不存在")

# --- the shots that were blocked ---------------------------------------
from dramakit.pipeline import refs as R   # noqa: E402
out.append("")
out.append("=== 之前被拦的镜头，现在 ===")
still = 0
freed = 0
for ep in ctx.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            m = [x for x in R.missing_references(ctx, sh, sc)
                 if "首帧" not in x]
            if m:
                still += 1
                if still <= 6:
                    out.append(f"  仍拦 {sh.id}: {m}")
            elif sh.characters and NAME in sh.characters:
                freed += 1
out.append(f"  仍被拦（不含首帧等待）: {still}")
out.append(f"  素素的镜头现已放行: {freed}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\susu_make.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
