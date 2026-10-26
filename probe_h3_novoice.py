"""Does the fixed H3 prompt keep the model from describing any speech?"""
import re
import sys

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.promptgen import _gen_h3_prompt
from dramakit.project import ProjectStore
from dramakit.pipeline.base import Context

cfg = Config.load(r"E:\dramakit\config\default.yaml")
proj = r"E:\dramakit\projects\轮次08_08"
store = ProjectStore(proj)
ctx = Context(cfg, store)
ep = ctx.target_episodes()[0]
llm = ctx.providers.llm_for("promptgen")

WORDS = ["speaks", "says", "voice", "talking", "speaking", "lips", "shouts",
         "whispers", "murmur", "dialogue", "argues", "replies", "utters"]
bad = 0
shots = [sh for sc in ep.scenes for sh in sc.shots][:4]
for sh in shots:
    sc = next(s for s in ep.scenes if sh in s.shots)
    _gen_h3_prompt(ctx, llm, sh, sc, "", sc.location or "", [])
    vp = sh.video_prompt or ""
    found = [w for w in WORDS if w in vp.lower()]
    tag = "OK " if not found else "含发声词"
    print(f"[{tag}] {sh.id}: {found}")
    print(f"    {vp[:230]}")
    bad += bool(found)
print(f"\n{len(shots)} 个镜头，{bad} 个仍提到发声")
