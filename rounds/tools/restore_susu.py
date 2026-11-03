"""Put 素素 back, with one four-view sheet like everyone else.

She was added while a run was under way, and that run's context had been
loaded before she existed - its save wrote the project back without her,
which is the same overwrite that took the anchor and the pictures out of
the record earlier. So she is rebuilt here: the entry, the picture that
was already drawn for her last night, the sheet that matches everyone
else's, the anchor, the voice.

One context, one save, the repository as root - the three things that were
wrong last time.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.models import Character         # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.providers import Providers      # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import character as CH # noqa: E402

REPO = Path(r"E:\dramakit")
NAME = "素素"
out = []

cfg = Config.load(Config.discover())
proj = next(d for d in (REPO / "projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
store = ProjectStore.open(proj)
# The root has to be the repository: it is where config/comfyui lives, and
# a context built from the store alone resolves every workflow path inside
# the project directory instead.
ctx = Context(cfg, store, Providers(cfg, REPO))

char = ctx.project.character(NAME)
if char is None:
    # What she looks like is not in the book and not in the prompts that
    # already reference her, so it is set here: the girl 余飞 left behind,
    # the same age as him, dressed for the summer of 2012 - and it matches
    # the pictures that were drawn for her, shoulder-length black hair with
    # a fringe, white blouse, denim skirt, white sneakers.
    char = Character(
        name=NAME,
        role="女主",
        gender="女",
        age="约18岁",
        personality="温柔安静，感情重；说话轻而慢，眼眶常带泪意，"
                     "笑起来有一点克制，像是怕惊动什么",
        appearance=(
            "约18岁的中国少女，齐肩黑发、额前稀疏空气刘海，发梢自然微卷，"
            "鹅蛋脸，浅棕眼睛，睫毛长，皮肤白皙，身高中等偏瘦；"
            "白色短袖衬衫（小V领、泡泡袖、下摆略收）配浅色牛仔短裙和白色帆布鞋，"
            "2012年夏天的学生打扮，素净无首饰；"
            "神情干净安静，眉眼间有一点挥不去的忧郁"),
        visual_prompt=(
            "An 18-year-old Chinese girl with shoulder-length black hair and a "
            "wispy fringe, softly curled at the ends, oval face, light-brown "
            "eyes, long lashes, fair skin, slim build, wearing a white "
            "short-sleeve blouse with a small V-neck and a light-blue denim "
            "mini skirt with white canvas sneakers, understated student look "
            "of the summer of 2012, no jewellery, clean quiet presence with a "
            "trace of melancholy, realistic cinematic portrait, soft natural "
            "light"),
        outfit="白色短袖小V领衬衫 + 浅色牛仔短裙 + 白色帆布鞋（2012 夏，无首饰）",
        hair="齐肩黑发，额前稀疏空气刘海，发梢微卷",
    )
    ctx.project.characters.append(char)
    out.append(f"已创建 {NAME}")
else:
    out.append(f"{NAME} 已在角色表")

# --- a voice, without stealing one -------------------------------------
taken = {c.voice_id for c in ctx.project.characters
         if c.name != NAME and c.voice_id}
if not char.voice_id:
    CH.cast_voices(ctx, list(ctx.project.characters))
    if char.voice_id and char.voice_id in taken:
        voices, _doc = CH._curated_voices(ctx, [])
        free = [v for v in voices if v not in taken]
        if free:
            char.voice_id = free[0]
out.append(f"  音色 {char.voice_id or '（未分配）'}")

# --- the four-view sheet, like everyone else's -------------------------
# Clear first: generate_refs appends, and the five pictures from last night
# would come back out as five plus the new one.
char.ref_images = []
char.ref_sheet = ""
t0 = time.time()
made = CH.generate_refs(ctx, char)
out.append(f"  四视图生成 {made} 张（{time.time()-t0:.0f}s）")
files = sorted(f.name for f in (proj / "characters" / NAME).iterdir()) \
    if (proj / "characters" / NAME).exists() else []
out.append(f"  目录 {files}")

# --- the recording, and the anchor --------------------------------------
if not (proj / "characters" / NAME / "voice.mp3").exists():
    made_v = CH.generate_voice_refs(ctx, [char])
    out.append(f"  语音样本 {made_v}")
else:
    char.voice_ref = f"characters/{NAME}/voice.mp3"
    out.append(f"  语音样本 已在（{char.voice_ref}）")

CH.build_anchors(ctx, [char])
out.append(f"  锚点 {char.anchor_prompt[:150]!r}")

ctx.save()

# --- read it back ------------------------------------------------------
again = ProjectStore.open(proj).load()
c2 = again.character(NAME)
out.append("")
out.append("=== 重新读盘 ===")
if c2 is None:
    out.append("  **仍然不存在**")
else:
    for k in ("name", "role", "voice_id", "voice_ref", "ref_sheet"):
        out.append(f"  {k}: {getattr(c2, k, None)!r}")
    out.append(f"  ref_images: {c2.ref_images}")
    out.append(f"  anchor: {c2.anchor_prompt[:160]!r}")
out.append(f"  角色总数: {len(again.characters)}")

# --- the shots she is in ------------------------------------------------
from dramakit.pipeline import refs as R   # noqa: E402
ctx2 = Context(cfg, ProjectStore.open(proj), Providers(cfg, REPO))
out.append("")
out.append("=== 她的 6 个镜头 ===")
freed = blocked = 0
for ep in ctx2.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            if NAME not in (sh.characters or []):
                continue
            m = [x for x in R.missing_references(ctx2, sh, sc)
                 if "首帧" not in x]
            if m:
                blocked += 1
                out.append(f"  仍拦 {sh.id}: {m}")
            else:
                freed += 1
out.append(f"  放行 {freed}，仍拦 {blocked}")

total_blocked = 0
for ep in ctx2.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            if [x for x in R.missing_references(ctx2, sh, sc)
                    if "首帧" not in x]:
                total_blocked += 1
out.append("")
out.append(f"=== 全项目被拦（不含首帧）: {total_blocked} 镜 ===")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\restore_susu.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
