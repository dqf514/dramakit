"""Let H3 speak the line itself.

Three changes:

1. The client can upload an audio file, so a shot's recorded line can go
   to ComfyUI as the voice-timbre reference.
2. The prompt generator writes the full-reference (R2V) format when the
   reference workflow is in use: the picture is the reference, the line is
   the dialogue, and the recorded voice is the timbre.
3. The voice track of the episode is taken from the clips, not from the
   separate recordings - the mouth and the voice come out of the same
   generation, which is the whole point.
"""
from pathlib import Path

# 1) the client: upload audio
p = Path(r"E:\\dramakit\\dramakit\\providers\\comfyui.py")
s = p.read_text(encoding="utf-8")
old = """    # ------------------------------------------------------------- submit
    def _queue(self, graph: dict) -> str:"""
new = '''    def upload_audio(self, audio_path: str | Path) -> str:
        """Upload a local audio file to ComfyUI /input; returns the name."""
        p = Path(audio_path)
        with open(p, "rb") as fh:
            files = {"audio": (p.name, fh, "audio/mpeg")}
            data = {"overwrite": "true", "type": "input"}
            r = self._post("/upload/image", files=files, data=data, timeout=180)
        if r.status_code >= 400:
            raise ComfyUIError(f"上传音频失败 {r.status_code}: {r.text[:200]}")
        return r.json().get("name", p.name)

    # ------------------------------------------------------------- submit
    def _queue(self, graph: dict) -> str:'''
assert old in s, "上传锚点没找到"
s = s.replace(old, new, 1)

# the reference audio slot: the client fills it when the graph has one
old = """        if image_path and Path(image_path).exists():
            server_name = extra.get("uploaded_image") or self.upload_image(image_path)
            extra["uploaded_image"] = server_name
            self._set(graph, nm, "image", "image", server_name)"""
new = """        if image_path and Path(image_path).exists():
            server_name = extra.get("uploaded_image") or self.upload_image(image_path)
            extra["uploaded_image"] = server_name
            self._set(graph, nm, "image", "image", server_name)
        # the voice reference: the recording of the line goes in as the
        # timbre the character speaks with
        ref_audio = extra.get("ref_audio_path")
        slot = str(extra.get("ref_audio_node") or "")
        if ref_audio and slot and Path(ref_audio).exists():
            server_audio = extra.get("uploaded_audio") or self.upload_audio(ref_audio)
            extra["uploaded_audio"] = server_audio
            graph.setdefault(slot, {}).setdefault("inputs", {})["audio"] = server_audio"""
assert old in s, "参考音频锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("comfyui.py 已改（可以上传参考音频）")

# 2) the config
p = Path(r"E:\\dramakit\\dramakit\\config.py")
s = p.read_text(encoding="utf-8")
old = """    i2v_nodes: dict = Field(default_factory=lambda: {"""
new = """    # 让 H3 自己说话：画面、嘴型、人声、音效一次出。
    # 这条路只有 ref2va 模型走得通——fl2va 生成的人声是乱码。
    native_audio: bool = False
    ref_audio_node: str = "900"          # 工作流里装载参考音频的节点
    i2v_nodes: dict = Field(default_factory=lambda: {"""
assert old in s, "config 锚点没找到"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("config.py 已改")
