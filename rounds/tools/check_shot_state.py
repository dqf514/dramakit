"""What does the project think, and what is on the disk?

The console says two shots failed. The card says the clips are there.
Those two statements can only both be true if the project was never
told - so this reads the project's own record of each shot and compares
it with the file on disk.
"""
import json
import pathlib

PROJ = pathlib.Path(r"E:\dramakit\projects\星际骷髅兵")
raw = json.loads((PROJ / "project.json").read_text(encoding="utf-8"))

print("=== 每一镜：项目记录的 vs 磁盘上的 ===")
for ep in raw.get("episodes") or []:
    for sc in ep.get("scenes") or []:
        for sh in sc.get("shots") or []:
            vp = sh.get("video_path")
            ip = sh.get("image_path")
            v_on_disk = bool(vp) and (PROJ / vp).exists()
            i_on_disk = bool(ip) and (PROJ / ip).exists()
            if not v_on_disk or sh.get("status") != "done":
                print(f"  第{ep['index']}集 场{sc.get('index')} {sh['id']}")
                print(f"     状态={sh.get('status')}  视频路径={vp}（磁盘上有={v_on_disk}）"
                      f"  图片路径={ip}（磁盘上有={i_on_disk}）")
                gm = sh.get("gen_meta") or {}
                print(f"     gen_meta={json.dumps(gm, ensure_ascii=False)[:160]}")

print()
print("=== 磁盘上的视频文件 ===")
for f in sorted((PROJ / "video").glob("*.mp4"), key=lambda x: x.stat().st_mtime):
    import time
    print(f"  {f.name:28} {f.stat().st_size/1048576:5.1f} MB  "
          f"{time.strftime('%m-%d %H:%M:%S', time.localtime(f.stat().st_mtime))}")
