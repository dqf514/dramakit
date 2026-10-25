"""Test the FLUX 3 character reference prompt and the multi-reference path."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.pipeline.base import Context
from dramakit.pipeline.character import _ref_prompt
from dramakit.project import ProjectStore
from dramakit.providers.comfyui import ComfyUIClient

OUT = Path(r"C:\Users\David\AppData\Local\Temp\opencode\ref_test")
OUT.mkdir(parents=True, exist_ok=True)

cfg = Config.load(r"E:\dramakit\config\default.yaml")
store = ProjectStore(Path(r"E:\dramakit\projects\测试短剧"))
ctx = Context(cfg, store)
client = ComfyUIClient(cfg.comfyui, Path("E:/dramakit"))

c = ctx.project.characters[0]
prompt = _ref_prompt(ctx, c, "front")
print("提示词:", prompt[:400], "\n")

t0 = time.time()
client.generate_image(prompt, "", width=1024, height=1024, seed=1234,
                      steps=16, cfg=1.0, out_path=str(OUT / "char_ref.png"))
print(f"角色卡生成 {time.time()-t0:.0f}s -> {OUT / 'char_ref.png'}")
