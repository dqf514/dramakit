"""Turn the native audio path on: H3 says the line itself."""
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\default.yaml")
s = p.read_text(encoding="utf-8")

old = "  i2v_workflow: config/comfyui/i2v_minimax_h3.json"
new = """  i2v_workflow: config/comfyui/i2v_minimax_h3_ref2v_audio.json
  # 让 H3 自己说话（画面+嘴型+人声+音效一次出）。
  # 只有 ref2va 模型走得通：fl2va 生成的人声是乱码，我们才不得不改用画外音。
  native_audio: true
  ref_audio_node: "900"                   # 工作流里装载参考音频的节点"""
assert old in s, "工作流锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("yaml: 原生音频打开")
