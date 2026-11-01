"""How long does one model call take?

The prompt stage has run forty minutes without finishing a single episode,
which would need about sixty calls each. If a call is what the arithmetic
says it is, one episode is done in twelve minutes; if it is four times
that, the stage is not going to finish tonight. This times one real call,
and then four at once, since that is how the stage runs them.
"""
import sys
import time

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config
from dramakit.providers.llm import OpenAICompatLLM

cfg = Config.load(Config.discover())
llm = OpenAICompatLLM(cfg.llm)
print(f"模型 {cfg.llm.model} @ {cfg.llm.base_url}")
print(f"并发配置 {cfg.llm.concurrency}   超时 {cfg.llm.timeout}s   重试 {cfg.llm.max_retries}")

out = []
for i in range(2):
    t0 = time.time()
    try:
        r = llm.complete(
            "你是短剧导演。只输出JSON。",
            '把这一句扩写成一个镜头的出图提示词，输出 {"prompt": "..."}',
            max_tokens=2048, json_mode=True)
        out.append(f"  单次调用 {i + 1}: {time.time() - t0:.1f} 秒  ->  {str(r)[:90]!r}")
    except Exception as e:  # noqa: BLE001
        out.append(f"  单次调用 {i + 1}: {time.time() - t0:.1f} 秒  失败 {type(e).__name__}: {str(e)[:120]}")

print()
print("=== 4 个并发（和 stage 一样）===")
import threading

results = [None] * 4


def one(i):
    t0 = time.time()
    try:
        OpenAICompatLLM(cfg.llm).complete(
            "你是短剧导演。只输出JSON。",
            f'把这一句扩写成出图提示词，输出 {{"prompt": "...", "n": {i}}}',
            max_tokens=2048, json_mode=True)
        results[i] = time.time() - t0
    except Exception as e:  # noqa: BLE001
        results[i] = f"失败 {type(e).__name__}"


t0 = time.time()
ths = [threading.Thread(target=one, args=(i,)) for i in range(4)]
for t in ths:
    t.start()
for t in ths:
    t.join()
wall = time.time() - t0
print(f"  4 个并发总耗时 {wall:.1f} 秒")
for i, r in enumerate(results):
    print(f"    第 {i + 1} 个: {r if isinstance(r, str) else f'{r:.1f} 秒'}")

print()
print("=== 推算 ===")
if all(isinstance(r, float) for r in results):
    per = max(results)
    shots, calls_per_shot, workers = 288, 2, int(cfg.llm.concurrency or 1)
    total_calls = shots * calls_per_shot
    seconds = total_calls / workers * per
    print(f"  每次调用最慢 {per:.0f} 秒")
    print(f"  总调用 {total_calls} 次，并发 {workers}")
    print(f"  promptgen 预计 {seconds / 60:.0f} 分钟（约 {seconds / 3600:.1f} 小时）")
    per_ep = 30 * calls_per_shot / workers * per
    print(f"  每集约 {per_ep / 60:.0f} 分钟（30 镜）")
