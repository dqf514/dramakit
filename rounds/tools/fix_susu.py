"""Match 素素's card to the pictures that already exist, and register them.

The pictures were drawn last night and are on disk - face, front, side,
three-quarter, back - but the character entry has no record of them, so
every shot she is in still refuses to draw. Re-drawing would throw away a
face that was already chosen and cost a pass over the card for nothing.

So the description is rewritten to say what the pictures actually show -
shoulder-length black hair with a fringe, white blouse, denim skirt,
white sneakers, which is not what was written down before - the files are
registered, and the anchor is generated from the corrected description.

One context, one save: the previous attempt wrote the anchor through a
second context and then saved the first one over it, which is how the
record ended up empty while the anchor existed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.project import ProjectStore     # noqa: E402
from dramakit.providers import Providers      # noqa: E402
from dramakit.pipeline.base import Context    # noqa: E402
from dramakit.pipeline import character as CH # noqa: E402

REPO = Path(r"E:\dramakit")
out = []

cfg = Config.load(Config.discover())
proj = next(d for d in (REPO / "projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
store = ProjectStore.open(proj)
# The root has to be the repository, not the project: it is where
# config/comfyui lives, and a context built from the store alone resolves
# every workflow path inside the project directory instead.
ctx = Context(cfg, store, Providers(cfg, REPO))

NAME = "素素"
char = ctx.project.character(NAME)
if char is None:
    out.append(f"**{NAME} 不在角色表**")
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\susu_fix.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

# --- say what the pictures show ----------------------------------------
# Read off the images rather than invented: shoulder-length black hair with
# a wispy fringe, white short-sleeve blouse, light denim skirt, white
# sneakers - a student in the summer of 2012, which is the setting the
# episodes are staged in.
char.appearance = (
    "约18岁的中国少女，齐肩黑发、额前稀疏空气刘海，发梢自然微卷，"
    "鹅蛋脸，浅棕眼睛，睫毛长，皮肤白皙，身高中等偏瘦；"
    "白色短袖衬衫（小V领、泡泡袖、下摆略收）配浅色牛仔短裙和白色帆布鞋，"
    "2012年夏天的学生打扮，素净无首饰；"
    "神情干净安静，眉眼间有一点挥不去的忧郁")
char.hair = "齐肩黑发，额前稀疏空气刘海，发梢微卷"
char.outfit = "白色短袖小V领衬衫 + 浅色牛仔短裙 + 白色帆布鞋（2012 夏，无首饰）"
char.visual_prompt = (
    "An 18-year-old Chinese girl with shoulder-length black hair and a "
    "wispy fringe, softly curled at the ends, oval face, light-brown eyes, "
    "long lashes, fair skin, slim build, wearing a white short-sleeve "
    "blouse with a small V-neck and a light-blue denim mini skirt with "
    "white canvas sneakers, understated student look of the summer of "
    "2012, no jewellery, clean quiet presence with a trace of melancholy, "
    "realistic cinematic portrait, soft natural light")
if not char.personality:
    char.personality = ("温柔安静，感情重；说话轻而慢，眼眶常带泪意，"
                        "笑起来有一点克制，像是怕惊动什么")
if not char.age:
    char.age = "约18岁"
if not char.gender:
    char.gender = "女"
if not char.role:
    char.role = "女主"

# --- the pictures that are already there -------------------------------
views = ["face", "front", "side", "three_quarter", "back"]
made = []
for v in views:
    rel = f"characters/{NAME}/{v}.png"
    if (proj / rel).exists():
        made.append(rel)
    else:
        out.append(f"  缺 {rel}")
char.ref_images = made
char.ref_sheet = made[0] if made else ""
out.append(f"  登记参考图 {len(made)} 张: {[Path(m).name for m in made]}")

# --- the anchor, from the corrected description ------------------------
CH.build_anchors(ctx, [char])
out.append(f"  锚点: {char.anchor_prompt!r}")

ctx.save()

# --- read it back the way a fresh process would ------------------------
again = ProjectStore.open(proj).load()
c2 = again.character(NAME)
out.append("")
out.append("=== 重新读盘确认 ===")
for k in ("name", "role", "age", "voice_id", "voice_ref", "ref_sheet"):
    out.append(f"  {k}: {getattr(c2, k, None)!r}")
out.append(f"  ref_images ({len(c2.ref_images)}): {c2.ref_images}")
out.append(f"  anchor_prompt: {c2.anchor_prompt!r}")
out.append(f"  appearance: {c2.appearance[:120]!r}...")

# --- are the blocked shots free now ------------------------------------
from dramakit.pipeline import refs as R   # noqa: E402
ctx2 = Context(cfg, ProjectStore.open(proj), Providers(cfg, REPO))
out.append("")
out.append("=== 6 个镜头的门禁 ===")
still = freed = 0
for ep in ctx2.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            if NAME not in (sh.characters or []):
                continue
            m = [x for x in R.missing_references(ctx2, sh, sc)
                 if "首帧" not in x]
            if m:
                still += 1
                out.append(f"  仍拦 {sh.id}: {m}")
            else:
                freed += 1
                out.append(f"  ✓ 放行 {sh.id}")
out.append(f"  放行 {freed}，仍拦 {still}")

# and the whole project
blocked = 0
for ep in ctx2.project.episodes:
    for sc in ep.scenes:
        for sh in sc.shots:
            if [x for x in R.missing_references(ctx2, sh, sc)
                    if "首帧" not in x]:
                blocked += 1
out.append("")
out.append(f"=== 全项目仍被拦（不含首帧等待）: {blocked} 镜 ===")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\susu_fix.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
