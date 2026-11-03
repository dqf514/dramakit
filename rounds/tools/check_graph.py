"""The graph as it is finally sent, with the extra loaders gone.

Two shots were refused by the card: one had fewer pictures than the
workflow has slots, the other had no recording to go in the voice slot.
In both cases the slot was removed from the model's list and the loader
behind it was left in the graph with nothing in it - and a loader with
nothing in it fails validation, which refuses the whole job rather than
the one reference.

The job is stopped just before it is queued, so the graph the card would
receive can be read: no loader without a picture, no voice node without a
file. Then it is sent with its output removed, which makes the card
validate everything and then say it produces nothing - the check that
costs no GPU.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

from dramakit.config import Config            # noqa: E402
from dramakit.providers.comfyui import ComfyUIClient, ComfyUIError  # noqa: E402

CARD = "http://192.168.31.7:8188"
out = []

cfg = Config.load(Config.discover())
cfg.comfyui.base_url = CARD
client = ComfyUIClient(cfg.comfyui, root=Path(r"E:\dramakit"))

proj = next(d for d in Path(r"E:\dramakit\projects").iterdir()
            if d.is_dir() and (d / "project.json").exists())
raw = json.loads((proj / "project.json").read_text(encoding="utf-8"))
who = next(c for c in raw["characters"] if isinstance(c, dict) and c.get("voice_ref"))
refs = [str(proj / p) for p in who.get("ref_images") or []]
refs = [p for p in refs if Path(p).exists()]
frames = sorted((proj / "images").glob("*.png"))

# --- capture instead of queue -----------------------------------------
captured: dict = {}


class Stopped(Exception):
    pass


def fake_queue(graph: dict) -> str:
    captured["graph"] = graph
    raise Stopped()


client._queue = fake_queue


def attempt(label: str, pictures: list[str], audio: str) -> None:
    captured.clear()
    out.append(f"=== {label} ===")
    out.append(f"  参考图 {len(pictures)} 张"
               + (f"，配音 {Path(audio).name}" if audio else "，**无配音**"))
    try:
        client.generate_video(
            prompt="test", negative="",
            image_path=str(frames[0]) if frames else "",
            frames=22, fps=24, seed=7,
            out_path=str(proj / "_render_test" / "x.mp4"),
            extra={"ref_pictures": pictures,
                   **({"ref_audio_path": audio,
                       "ref_audio_node": cfg.comfyui.ref_audio_node}
                      if audio else {})})
    except Stopped:
        pass
    except ComfyUIError as e:
        out.append(f"  **提交前就失败**: {e}")
        return
    except Exception as e:  # noqa: BLE001
        out.append(f"  **异常**: {type(e).__name__}: {e}")
        return

    g = captured.get("graph") or {}
    model = next((n for n in g.values()
                  if "ReferenceToVideo" in str(n.get("class_type", ""))), {})
    ins = model.get("inputs") or {}

    # every loader still in the graph must hold something
    bad = []
    for nid, n in g.items():
        ct = str(n.get("class_type", ""))
        if ct == "LoadImage" and not (n.get("inputs") or {}).get("image"):
            bad.append(f"#{nid} LoadImage 空")
        if ct == "LoadAudio" and not (n.get("inputs") or {}).get("audio"):
            bad.append(f"#{nid} LoadAudio 空")
        if not ct:
            bad.append(f"#{nid} 无 class_type")
    out.append(f"  节点数 {len(g)}")
    out.append(f"  ref_images 槽: "
               f"{sorted(k for k in ins if k.startswith('ref_images.'))}")
    out.append(f"  ref_audios 槽: "
               f"{sorted(k for k in ins if k.startswith('ref_audios.'))}")
    out.append(f"  空/坏节点: {bad or '无'}")

    # --- the free validation ------------------------------------------
    no_out = {k: v for k, v in g.items()
              if v.get("class_type") not in ("SaveVideo", "SaveImage")}
    import urllib.request, urllib.error   # noqa: E402
    req = urllib.request.Request(
        CARD + "/prompt",
        data=json.dumps({"prompt": no_out,
                         "client_id": "dramakit-validate"}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read().decode("utf-8", "replace")
            st = r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        st = e.code
    except Exception as e:  # noqa: BLE001
        body, st = f"{type(e).__name__}: {e}", 0
    out.append(f"  校验提交 HTTP {st}  {body.replace(chr(10), ' ')[:300]}")
    if "prompt_no_outputs" in body:
        out.append("  => **通过**（除输出节点外全部合格）")
    elif "validation" in body:
        out.append("  => **失败：校验不通过**")
        # pull the offending node out
        try:
            d = json.loads(body)
            for nid, e in (d.get("node_errors") or {}).items():
                for err in (e.get("errors") or []):
                    out.append(f"      节点 {nid}: {err.get('details') or err}")
        except Exception:  # noqa: BLE001
            pass
    else:
        out.append("  => 见上")
    out.append("")


audio = str(proj / who["voice_ref"]) if who.get("voice_ref") else ""
attempt("三张图 + 有配音（典型镜头）", refs[:3], audio)
attempt("两张图 + 无配音（房间和配音都缺）", refs[:2], "")
attempt("一张图 + 无配音（最省）", refs[:1], "")
attempt("九张图 + 有配音（全部槽位）", refs, audio)

Path(r"C:\Users\David\AppData\Local\Temp\opencode\graphcheck.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
