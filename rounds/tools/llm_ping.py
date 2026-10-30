"""Is the LLM answering right now?"""
import sys
import time

sys.path.insert(0, r"E:\\dramakit")
from dramakit.config import Config
from dramakit.providers import Providers
from pathlib import Path

cfg = Config.load(r"E:\\dramakit\\config\\default.yaml")
p = Providers(cfg, Path(r"E:\\dramakit\\projects"))
llm = p.llm_for("storyboard")
t0 = time.time()
try:
    d = llm.complete_json(
        "你是分镜师。只输出JSON。",
        "为一场婚礼戏写 2 个片段，每个片段写景别/机位/时长/动作(中文)。"
        "JSON格式：{\"shots\":[{\"shot_type\":\"中景\",\"camera_move\":\"推\","
        "\"duration\":8.0,\"action\":\"...\",\"characters\":[],\"lines\":[]}]}")
    print(f"{time.time()-t0:.1f}s ->", str(d)[:300])
except Exception as e:  # noqa: BLE001
    print(f"{time.time()-t0:.1f}s 失败: {type(e).__name__}: {str(e)[:300]}")
