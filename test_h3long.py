"""Can H3 do a full 15-second shot at 960x544 on this card?"""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.providers.comfyui import ComfyUIClient
from dramakit.media import ffmpeg as ff

cfg = Config.load(r"E:\dramakit\config\default.yaml")
client = ComfyUIClient(cfg.comfyui, Path("E:/dramakit"))

img = sorted(Path(r"E:\dramakit\projects\测试短剧\images").glob("*.png"))[0]
PROMPT = ("[Shot 1] Full-color outdoor photograph, medium shot, a man in a black "
          "suit walks along a city sidewalk, overcast daylight, steady tracking "
          "camera, buses and glass towers behind him. <d>[zh-CN]你终于肯回来了。</d>")

for frames in (124, 243, 360):
    out = Path(rf"C:\Users\David\AppData\Local\Temp\opencode\h3_{frames}.mp4")
    t0 = time.time()
    try:
        client.generate_video(PROMPT, "", image_path=str(img), frames=frames,
                              fps=24, seed=4242, out_path=str(out),
                              extra={"uploaded_image": client.upload_image(img)})
        dt = time.time() - t0
        st = ff.probe_streams(out)
        v = st.get("video") or {}
        print(f"{frames:4d} 帧 ({frames/24:5.2f}s): {dt:6.1f}s  "
              f"输出 {v.get('width')}x{v.get('height')} 时长 {v.get('duration')}  "
              f"{out.stat().st_size/1024/1024:.2f} MB")
    except Exception as e:  # noqa: BLE001
        print(f"{frames:4d} 帧: 失败 {str(e)[:200]}")
