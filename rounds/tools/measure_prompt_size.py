"""How big is the prompt the stage actually sends?

Test calls return in three seconds; the stage's take about ninety. The
difference has to be what it sends, and the stage appends the skill rules
to every video-prompt call. This measures that string, and times one call
with it, so the cost is a number rather than a suspicion.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.project import ProjectStore
from dramakit.providers.llm import OpenAICompatLLM

store = ProjectStore.open(Path(r"E:\dramakit\projects\魔兽世界"))
cfg = Config.load(Config.discover())
ctx = Context(cfg, store)

# what the stage appends
try:
    from dramakit.skills import loader
    rules = loader.for_stage(ctx, "promptgen")
    out = [f"skills for promptgen: {len(rules):,} 字  ({len(rules):,} 字符)"]
    out.append("  开头 120 字: " + repr(rules[:120]))
except Exception as e:  # noqa: BLE001
    out = [f"loader 失败: {type(e).__name__}: {e}"]
    rules = ""

# and the constraint block it ships with
import dramakit.prompts.templates as T
consts = getattr(T, "H3_CONSTRAINTS", "")
out.append(f"H3_CONSTRAINTS: {len(consts):,} 字")

# one real call, with what the stage sends
llm = OpenAICompatLLM(cfg.llm)
shot_desc = ("中景，固定镜头，2012年6月25日中午，网吧里，十八岁的男生对着480分的"
             "成绩单发呆，屏幕冷光照脸，周围同学喧闹。台词：为什么！480分！")
user = (f"镜头内容：{shot_desc}\n\n"
        f"约束：\n{consts}\n\n技能规则：\n{rules[:20000]}\n\n"
        '只输出 JSON：{"prompt": "...", "negative": "..."}')

out.append("")
out.append(f"测试提示词总长: {len(user):,} 字")
t0 = time.time()
try:
    r = llm.complete("你是提示词工程师。只输出JSON。", user,
                     max_tokens=cfg.llm.max_tokens, json_mode=True)
    out.append(f"带规则的调用: {time.time() - t0:.1f} 秒  输出 {len(str(r))} 字")
except Exception as e:  # noqa: BLE001
    out.append(f"带规则的调用: {time.time() - t0:.1f} 秒  失败 {type(e).__name__}: {str(e)[:140]}")

# and without, for the comparison
t0 = time.time()
try:
    r2 = llm.complete("你是提示词工程师。只输出JSON。",
                      f"镜头：{shot_desc}\n只输出 JSON：{{\"prompt\": \"...\"}}",
                      max_tokens=cfg.llm.max_tokens, json_mode=True)
    out.append(f"不带规则的调用: {time.time() - t0:.1f} 秒  输出 {len(str(r2))} 字")
except Exception as e:  # noqa: BLE001
    out.append(f"不带规则的调用: {time.time() - t0:.1f} 秒  失败 {type(e).__name__}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\promptsize.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
