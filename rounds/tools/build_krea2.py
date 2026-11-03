"""Krea-2 on the local card, in the two shapes the pipeline asks for.

The pipeline writes to a workflow by node id - prompt on 104, sampler on
107, latent on 106, loaders on 101-103 - and switches to a second file
when a shot has reference pictures to be conditioned on. Both files are
built here with those ids kept, so the mapping in the config does not
have to change with the model.

What does change is the shape of the graph. Krea-2 takes a qwen3vl text
encoder under its own type, an ordinary latent rather than flux's, and
needs no flux shift node; its negative conditioning is zeroed rather than
encoded, because the model runs at cfg 1 where a negative does nothing
either way. The reference file additionally carries the node that folds
pictures into the conditioning - whether that node serves this model as
well as it served flux is the thing the validation below is for.
"""
import json
import sys
from pathlib import Path

OUT = Path(r"E:\dramakit\config\comfyui")
UNET = "krea2_turbo_nvfp4.safetensors"
CLIP = "qwen3vl_4b_int8_convrot.safetensors"
VAE = "qwen_image_vae.safetensors"

out = []


def base_graph(prefix: str) -> dict:
    """The shared spine: loaders, encoding, sampling, decode, save.

    Node ids are the ones the config names, so the mapping that writes the
    prompt and the size keeps working without being rewritten.
    """
    return {
        "101": {"class_type": "UNETLoader",
                "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "102": {"class_type": "CLIPLoader",
                "inputs": {"clip_name": CLIP, "type": "krea2",
                           "device": "default"}},
        "103": {"class_type": "VAELoader",
                "inputs": {"vae_name": VAE}},
        "104": {"class_type": "CLIPTextEncode",
                "inputs": {"text": "portrait of a person, studio lighting",
                           "clip": ["102", 0]}},
        # Kept as an encoder rather than zeroed out: the model runs at cfg 1,
        # where the negative contributes nothing, and a real encoder is what
        # the config's `negative` semantic writes into.
        "105": {"class_type": "CLIPTextEncode",
                "inputs": {"text": "", "clip": ["102", 0]}},
        "106": {"class_type": "EmptyLatentImage",
                "inputs": {"width": 1344, "height": 768, "batch_size": 1}},
        "107": {"class_type": "KSampler",
                "inputs": {"seed": 12345, "steps": 8, "cfg": 1.0,
                           "sampler_name": "euler", "scheduler": "simple",
                           "denoise": 1.0, "model": ["101", 0],
                           "positive": ["104", 0], "negative": ["105", 0],
                           "latent_image": ["106", 0]}},
        "108": {"class_type": "VAEDecode",
                "inputs": {"samples": ["107", 0], "vae": ["103", 0]}},
        "109": {"class_type": "SaveImage",
                "inputs": {"filename_prefix": prefix, "images": ["108", 0]}},
    }


def main() -> None:
    # --- plain text to image -------------------------------------------
    plain = base_graph("dramakit/t2i")
    (OUT / "t2i_krea2.json").write_text(
        json.dumps(plain, ensure_ascii=False, indent=2), encoding="utf-8")
    out.append(f"t2i_krea2.json: {len(plain)} 节点")

    # --- with reference pictures ----------------------------------------
    # The pictures are folded into the conditioning by a node that sits
    # between the encoder and the sampler. Whether that node serves this
    # model is the open question: it was written for flux, and Krea-2 has a
    # style-reference node of its own, which does something different -
    # style, not identity. Identity is what a character sheet is for, so
    # this is the one to try first.
    ref = base_graph("dramakit/t2i_ref")
    ref["130"] = {
        "class_type": "ReferenceMultiLatent",
        "inputs": {"positive": ["104", 0], "negative": ["105", 0],
                   "vae": ["103", 0], "resolution": "keep resolution",
                   "images.image0": ["201", 0]},
    }
    ref["107"]["inputs"]["positive"] = ["130", 0]
    for i in range(4):
        ref[str(201 + i)] = {"class_type": "LoadImage",
                             "inputs": {"image": "example.png",
                                        "upload": "image"}}
    (OUT / "t2i_krea2_ref.json").write_text(
        json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")
    out.append(f"t2i_krea2_ref.json: {len(ref)} 节点")

    # --- what the config has to say --------------------------------------
    out.append("")
    out.append("=== 需要改的配置 ===")
    out.append("  t2i_workflow:     config/comfyui/t2i_krea2.json")
    out.append("  t2i_workflow_ref: config/comfyui/t2i_krea2_ref.json")
    out.append('  t2i_nodes.sampling: ""   # Krea-2 没有 ModelSamplingFlux')
    out.append('  t2i_nodes.checkpoint: "101"   # 已对')
    out.append("  checkpoint(模型名): krea2_turbo_nvfp4.safetensors")
    out.append("")
    out.append("=== 与 flux3 的结构差异 ===")
    out.append("  106 EmptyFlux2LatentImage -> EmptyLatentImage")
    out.append("  112 ModelSamplingFlux     -> 删除（Krea-2 不需要 flux shift）")
    out.append("  102 type flux3            -> krea2")
    out.append("  107 steps 16              -> 8（turbo 蒸馏版）")

    # the files the two graphs need, and whether they are on disk
    out.append("")
    out.append("=== 模型文件 ===")
    root = Path(r"E:\ComfyUI\models")
    for sub, name in (("diffusion_models", UNET), ("text_encoders", CLIP),
                      ("vae", VAE)):
        p = root / sub / name
        if p.exists():
            out.append(f"  ✓ {sub}/{name}  {p.stat().st_size/1024**3:.2f} GiB")
        else:
            out.append(f"  ✗ {sub}/{name}  **缺失**")

    (Path(r"C:\Users\David\AppData\Local\Temp\opencode\krea2.txt")
     .write_text("\n".join(out), encoding="utf-8"))
    print("wrote")


if __name__ == "__main__":
    main()
