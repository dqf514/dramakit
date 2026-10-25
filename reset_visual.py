"""Reset the visual stage so every shot is regenerated.

Used when the image model or the video resolution changes: the old assets
were rendered with a different pipeline and must not be reused.
"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
from dramakit.config import Config
from dramakit.project import ProjectStore
from dramakit.models import Status

cfg = Config.load(r"E:\dramakit\config\default.yaml")
root = Path(r"E:\dramakit\projects\测试短剧")
store = ProjectStore(root)
project = store.load()

clear_prompt = "--keep-prompt" not in sys.argv
delete_files = "--delete" in sys.argv

n_shot = n_img = n_vid = n_prompt = 0
for ep in project.episodes:
    ep.stage_status.pop("visual", None)
    ep.stage_status.pop("precheck", None)
    ep.stage_status.pop("compose", None)
    ep.stage_status.pop("qc", None)
    for sc in ep.scenes:
        for sh in sc.shots:
            n_shot += 1
            if sh.image_path:
                n_img += 1
                if delete_files:
                    p = store.abs(sh.image_path)
                    p.unlink(missing_ok=True)
                sh.image_path = ""
            if sh.video_path:
                n_vid += 1
                if delete_files:
                    p = store.abs(sh.video_path)
                    p.unlink(missing_ok=True)
                sh.video_path = ""
            sh.end_image_path = ""
            sh.status = Status.PENDING
            sh.gen_meta = {}
            if clear_prompt:
                if sh.prompt:
                    n_prompt += 1
                sh.prompt = ""
                sh.negative_prompt = ""
                sh.end_prompt = ""

store.save(project)
print(f"镜头 {n_shot} 个：清掉图片 {n_img}、视频 {n_vid}、提示词 {n_prompt}")
