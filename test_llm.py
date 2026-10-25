import sys
import time

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.providers.llm import build_llm

c = Config.load(r"E:\dramakit\config\default.yaml")
llm = build_llm(c.llm)
t0 = time.time()
r = llm.complete_json(
    "鍙緭鍑篔SON",
    '缁欒繖涓暅澶村啓涓€鍙ヨ嫳鏂囨彁绀鸿瘝锛岃緭鍑?{"prompt":"..."}',
)
print(f"鑰楁椂 {time.time()-t0:.1f}s")
print(str(r)[:400])

