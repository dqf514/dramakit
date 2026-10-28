"""torch 2.6 loads weights with weights_only=True by default.

The weights here are the ones the MuseTalk authors published: the face
parser is an old .tar file and the detector a pickle, and both need the
old behaviour. They are our own downloads, so loading them is fine.
"""
from pathlib import Path

targets = [
    Path(r"E:\\musetalk\\musetalk\\utils\\face_parsing\\__init__.py"),
    Path(r"E:\\musetalk\\musetalk\\utils\\face_parsing\\resnet.py"),
    Path(r"E:\\musetalk\\musetalk\\utils\\face_detection\\detection\\sfd\\sfd_detector.py"),
]
for p in targets:
    if not p.exists():
        print(f"跳过（不存在）: {p}")
        continue
    s = p.read_text(encoding="utf-8")
    if "weights_only" in s:
        print(f"已处理: {p.name}")
        continue
    s2 = s.replace("torch.load(model_pth)",
                   "torch.load(model_pth, weights_only=False)")
    s2 = s2.replace("torch.load(model_pth, map_location=torch.device('cpu'))",
                    "torch.load(model_pth, map_location=torch.device('cpu'), "
                    "weights_only=False)")
    s2 = s2.replace("torch.load(model_path)",
                    "torch.load(model_path, weights_only=False)")
    s2 = s2.replace("torch.load(path_to_detector)",
                    "torch.load(path_to_detector, weights_only=False)")
    if s2 != s:
        p.write_text(s2, encoding="utf-8")
        print(f"已改: {p.name}")
    else:
        print(f"没找到要改的地方: {p.name}")
