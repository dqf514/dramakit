"""Two things were wrong with the pictures the job was given.

Every character's sheet is called sheet.jpg.  The upload used the file's
name, so all of them arrived on the server under the same name and the last
one uploaded overwrote the others: two slots in the same job held the same
face, and the person who was supposed to be in the shot was in neither.

And the slots that were not filled kept the workflow's placeholder - a
file that is not on the server.  The node behind it tried to load it, and
the model was handed a broken picture in the middle of its references.

So: a picture is uploaded under a name that says which picture it is, and
a slot that has no picture is taken out of the job.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\providers\\comfyui.py")
s = p.read_text(encoding="utf-8")

# --------------------------------------------------------------------------- #
# 1. the upload name has to say which picture this is
# --------------------------------------------------------------------------- #
old = '''    def upload_image(self, image_path: str | Path) -> str:
        """Upload a local image to ComfyUI /input; returns the server-side name."""
        p = Path(image_path)
        with open(p, "rb") as fh:
            files = {"image": (p.name, fh, "image/png")}
            data = {"overwrite": "true"}
            r = self._post("/upload/image", files=files, data=data, timeout=180)
        if r.status_code >= 400:
            raise ComfyUIError(f"上传图片失败 {r.status_code}: {r.text[:200]}")
        return r.json().get("name", p.name)'''

new = '''    def upload_image(self, image_path: str | Path) -> str:
        """Upload a local image to ComfyUI /input; returns the server-side name.

        The name on the server has to say which picture this is.  Every
        character's sheet is called sheet.jpg, and a name taken from the
        file would put all of them at the same address on the server - the
        last upload overwrites the others and two slots of the same job end
        up holding the same face.  The name carries the picture's own
        fingerprint, so a picture that was drawn again gets a new address
        and a picture that did not change keeps the one it had.
        """
        p = Path(image_path)
        name = self._fingerprint(p) + "_" + p.name
        with open(p, "rb") as fh:
            files = {"image": (name, fh, "image/png")}
            data = {"overwrite": "true"}
            r = self._post("/upload/image", files=files, data=data, timeout=180)
        if r.status_code >= 400:
            raise ComfyUIError(f"上传图片失败 {r.status_code}: {r.text[:200]}")
        return r.json().get("name", name)

    @staticmethod
    def _fingerprint(path: Path, size: int = 10) -> str:
        """A short fingerprint of the file's content."""
        import hashlib
        h = hashlib.md5()
        try:
            with open(path, "rb") as fh:
                h.update(fh.read(1 << 20))
        except OSError:
            h.update(str(path).encode("utf-8", "replace"))
        return h.hexdigest()[:size]'''
assert old in s, "upload_image 锚点没找到"
s = s.replace(old, new, 1)

# --------------------------------------------------------------------------- #
# 2. a slot with no picture is taken out of the job
# --------------------------------------------------------------------------- #
old = """        pictures = list(extra.get("ref_pictures") or [])
        if pictures:
            slots: list[tuple[str, str]] = []
            for nid, node in graph.items():
                if not isinstance(node, dict):
                    continue
                if "ReferenceToVideo" in str(node.get("class_type", "")):
                    for slot, link in sorted(
                            (node.get("inputs", {}).get("ref_images") or {}).items()):
                        if isinstance(link, list) and link:
                            slots.append((str(link[0]), slot))
                    break
            for (load_id, _slot), path in zip(slots, pictures):
                if load_id not in graph or not Path(path).exists():
                    continue
                graph[load_id].setdefault("inputs", {})["image"] = self.upload_image(path)"""

new = """        pictures = list(extra.get("ref_pictures") or [])
        if pictures:
            slots: list[tuple[str, str]] = []
            ref_node = None
            for nid, node in graph.items():
                if not isinstance(node, dict):
                    continue
                if "ReferenceToVideo" in str(node.get("class_type", "")):
                    ref_node = node
                    for slot, link in sorted(
                            (node.get("inputs", {}).get("ref_images") or {}).items()):
                        if isinstance(link, list) and link:
                            slots.append((str(link[0]), slot))
                    break
            used: set[str] = set()
            for (load_id, slot), path in zip(slots, pictures):
                if load_id not in graph or not Path(path).exists():
                    continue
                graph[load_id].setdefault("inputs", {})["image"] = self.upload_image(path)
                used.add(slot)
            # The slots that got no picture are taken out of the job: the
            # node behind them would go on loading the placeholder, and the
            # model would be handed a picture that is not there.
            if ref_node is not None:
                imgs = dict(ref_node.get("inputs", {}).get("ref_images") or {})
                for slot in list(imgs):
                    if slot not in used:
                        imgs.pop(slot)
                ref_node.setdefault("inputs", {})["ref_images"] = imgs"""
assert old in s, "参考图槽位锚点没找到"
s = s.replace(old, new, 1)

# --------------------------------------------------------------------------- #
# 3. the same for the voice reference
# --------------------------------------------------------------------------- #
old = """        if ref_audio and slot and Path(ref_audio).exists():
            server_audio = extra.get("uploaded_audio") or self.upload_audio(ref_audio)
            extra["uploaded_audio"] = server_audio
            graph.setdefault(slot, {}).setdefault("inputs", {})["audio"] = server_audio"""

new = """        if ref_audio and slot and Path(ref_audio).exists():
            server_audio = extra.get("uploaded_audio") or self.upload_audio(ref_audio)
            extra["uploaded_audio"] = server_audio
            graph.setdefault(slot, {}).setdefault("inputs", {})["audio"] = server_audio
            # and the slots that got no recording are taken out too
            for nid, node in graph.items():
                if not isinstance(node, dict):
                    continue
                if "ReferenceToVideo" not in str(node.get("class_type", "")):
                    continue
                auds = dict(node.get("inputs", {}).get("ref_audios") or {})
                for aslot in list(auds):
                    if str(auds[aslot][0]) != slot:
                        auds.pop(aslot)
                node.setdefault("inputs", {})["ref_audios"] = auds"""
assert old in s, "音频参考锚点没找到"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("comfyui.py: 上传名唯一了，空槽位从任务里拿掉了")
