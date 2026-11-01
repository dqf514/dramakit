"""Is the budget what makes the stage's call slow?

The stage sends no max_tokens, so it inherits the configured 102400; a
test call with 2048 returns in three seconds. If the budget is what costs
the time, the same prompt at the stage's budget will cost it too - and
that is the difference between a stage that takes twenty minutes and one
that takes four hours.
"""
import sys
import time

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.providers.llm import OpenAICompatLLM

cfg = Config.load(Config.discover())
llm = OpenAICompatLLM(cfg.llm)

prompt = ("把下面这个镜头写成 FLUX 3 的出图提示词，英文，包含景别、运镜、"
          "人物动作、光线和场景。镜头内容：中景，固定镜头，2012年6月25日中午，"
          "网吧里，一个十八岁的男生对着480分的成绩单发呆，周围同学喧闹，"
          "屏幕的冷光照在他脸上。只输出 JSON：{\"prompt\": \"...\"}")

for budget in (2048, 16384, 102400):
    t0 = time.time()
    try:
        r = llm.complete(
            "你是短剧导演和提示词工程师。只输出JSON。",
            prompt, max_tokens=budget, json_mode=True)
        dt = time.time() - t0
        print(f"  max_tokens={budget:>7}  {dt:6.1f} 秒   输出 {len(str(r))} 字")
    except Exception as e:  # noqa: BLE001
        print(f"  max_tokens={budget:>7}  {time.time() - t0:6.1f} 秒   失败 {type(e).__name__}: {str(e)[:110]}")

print()
print("=== 阶段实际的调用参数 ===")
print(f"  没传 max_tokens -> 用配置的 {cfg.llm.max_tokens}")
print(f"  json_mode={cfg.llm.json_mode}  temperature={cfg.llm.temperature}")
print(f"  超时 {cfg.llm.timeout}s  重试 {cfg.llm.max_retries}")
