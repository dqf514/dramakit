import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.media import ffmpeg as ff

root = Path(r"E:\dramakit\projects\测试短剧")
refs = sorted((root / "characters").rglob("front.png"))
print("角色参考图:", len(refs))
src = refs[0]
print("原图:", src)
st = ff.probe_streams(src)
v = st.get("video") or {}
print(f"  {v.get('width')}x{v.get('height')}")

out = Path(r"C:\Users\David\AppData\Local\Temp\opencode\ref_fitted.png")
ff.fit_reference(src, out, 1344, 768)
st2 = ff.probe_streams(out)
v2 = st2.get("video") or {}
print(f"适配后: {v2.get('width')}x{v2.get('height')}  -> {out}")
