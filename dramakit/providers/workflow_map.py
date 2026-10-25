"""Infer semantic node ids from a ComfyUI API-format workflow.

A workflow export only carries class_type + links. DramaKit needs to know which
node holds the positive prompt, the seed, the image, etc. Instead of asking the
user to hand-copy node numbers, walk the graph and infer them. Explicit ids in
config still win; inference fills the blanks (and repairs stale ids at runtime).
"""
from __future__ import annotations

from typing import Any, Iterable

CLIP_TYPES = {
    "CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeSDXLRefiner",
    "CLIPTextEncodeFlux", "CLIPTextEncodePixArtAlpha", "T5TextEncode",
    "TextEncodeQwenImageEdit",
}
SAMPLER_TYPES = {
    "KSampler", "KSamplerAdvanced", "SamplerCustom", "SamplerCustomAdvanced",
}
LATENT_TYPES = {
    "EmptyLatentImage", "EmptySD3LatentImage", "EmptyLatentImagePresets",
    "EmptyFlux2LatentImage",
}
CHECKPOINT_TYPES = {"CheckpointLoaderSimple", "CheckpointLoader", "UNETLoader"}
TEXT_ENCODER_TYPES = {"CLIPLoader"}
VAE_TYPES = {"VAELoader"}
SAMPLING_TYPES = {"ModelSamplingFlux"}
LOAD_IMAGE_TYPES = {"LoadImage", "LoadImageMask"}
VIDEO_OUT_TYPES = {
    "VHS_VideoCombine", "SaveVideo", "SaveAnimatedWEBP", "SaveAnimatedPNG",
    "CreateVideo", "WanVideoCombine",
}
VIDEO_MARKERS = (
    "AnimateDiff", "ADE_", "SVD", "WanVideo", "HunyuanVideo", "LTX",
    "CogVideo", "Mochi", "VideoLinearCFGGuidance",
)

_SEMANTIC_KEYS = (
    "positive", "negative", "seed", "width", "height",
    "steps", "cfg", "sampler", "checkpoint", "ref_image", "clip", "vae",
)


def _links(node: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for field, value in (node.get("inputs") or {}).items():
        if isinstance(value, list) and len(value) == 2 and isinstance(value[0], (str, int)):
            out[field] = str(value[0])
    return out


def _nkey(nid: str):
    return (0, int(nid)) if str(nid).isdigit() else (1, str(nid))


def _of_type(graph: dict, types: Iterable[str]) -> list[str]:
    wanted = set(types)
    return [nid for nid, node in graph.items()
            if (node.get("class_type") or "") in wanted]


def _walks(graph: dict, start: str, max_depth: int = 8) -> list[str]:
    """Breadth-first ancestors of `start` (nearest first).

    Order is stable: a set would make the result depend on hashing, and the
    caller picks the first CLIPTextEncode it finds.
    """
    seen: set[str] = set()
    order: list[str] = []
    queue = [(start, 0)]
    while queue:
        cur, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        for up in _links(graph.get(cur, {})).values():
            if up in graph and up not in seen and up != start:
                seen.add(up)
                order.append(up)
                queue.append((up, depth + 1))
    return order


def _ancestor_of_type(graph: dict, start: str, types: Iterable[str]) -> str:
    wanted = set(types)
    direct = _links(graph.get(start, {}))
    for up in direct.values():
        if up in graph and (graph[up].get("class_type") or "") in wanted:
            return up
    for up in _walks(graph, start):
        if (graph[up].get("class_type") or "") in wanted:
            return up
    return ""


def _input_value(graph: dict, nid: str, field: str) -> Any:
    return (graph.get(nid, {}).get("inputs") or {}).get(field)


def _is_video_graph(graph: dict) -> bool:
    classes = {(n.get("class_type") or "") for n in graph.values()}
    if classes & VIDEO_OUT_TYPES:
        return True
    if any(any(m in c for m in VIDEO_MARKERS) for c in classes):
        return True
    for nid in _of_type(graph, LATENT_TYPES):
        batch = _input_value(graph, nid, "batch_size")
        if isinstance(batch, (int, float)) and batch > 1:
            return True
    return False


def _pick_sampler(graph: dict) -> str:
    samplers = sorted(_of_type(graph, SAMPLER_TYPES), key=_nkey)
    for nid in samplers:
        links = _links(graph[nid])
        if "positive" in links and "latent_image" in links:
            return nid
    return samplers[0] if samplers else ""


def _positive_negative(graph: dict, sampler: str) -> tuple[str, str]:
    links = _links(graph.get(sampler, {}))

    def from_field(field: str) -> str:
        up = links.get(field, "")
        if not up or up not in graph:
            return ""
        if (graph[up].get("class_type") or "") in CLIP_TYPES:
            return up
        # a reference-conditioning node carries its own positive/negative
        # inputs, so follow the same field one level down
        inner = _links(graph[up]).get(field, "")
        if inner in graph and (graph[inner].get("class_type") or "") in CLIP_TYPES:
            return inner
        for anc in _walks(graph, up):
            if (graph[anc].get("class_type") or "") in CLIP_TYPES:
                return anc
        return ""

    return from_field("positive"), from_field("negative")


def _loader_of_type(graph: dict, sampler: str, types: Iterable[str]) -> str:
    """The loader node feeding the sampler, else the first one of that type."""
    wanted = set(types)
    for nid in _of_type(graph, wanted):
        if nid in _walks(graph, sampler) or nid in _links(graph.get(sampler, {})).values():
            return nid
    found = _of_type(graph, wanted)
    return sorted(found, key=_nkey)[0] if found else ""


def _checkpoint(graph: dict, sampler: str) -> str:
    for nid in _of_type(graph, CHECKPOINT_TYPES):
        if nid in _walks(graph, sampler) or nid in _links(graph.get(sampler, {})).values():
            return nid
    found = _of_type(graph, CHECKPOINT_TYPES)
    return sorted(found, key=_nkey)[0] if found else ""


def _latent(graph: dict, sampler: str) -> str:
    up = _links(graph.get(sampler, {})).get("latent_image", "")
    if not up or up not in graph:
        return ""
    if (graph[up].get("class_type") or "") in LATENT_TYPES:
        return up
    anc = _ancestor_of_type(graph, up, LATENT_TYPES)
    return anc or up


def _ref_slots(graph: dict) -> list[str]:
    """LoadImage nodes feeding an IP-Adapter / reference-only node."""
    slots: list[str] = []
    for nid, node in graph.items():
        ct = node.get("class_type") or ""
        if "IPAdapter" not in ct and "Reference" not in ct and "InstantID" not in ct:
            continue
        fields = ("image", "image2", "ref_image", "reference_image")
        # ReferenceMultiLatent names its slots images.image0, images.image1, ...
        fields += tuple(f"images.image{i}" for i in range(8))
        for field in fields:
            up = _links(node).get(field, "")
            if not up or up not in graph:
                continue
            target = ""
            if (graph[up].get("class_type") or "") in LOAD_IMAGE_TYPES:
                target = up
            else:
                anc = _ancestor_of_type(graph, up, LOAD_IMAGE_TYPES)
                target = anc
            if target and target not in slots:
                slots.append(target)
    return sorted(slots, key=_nkey)


def _video_image_slots(graph: dict, sampler: str, refs: list[str]) -> list[str]:
    """LoadImage nodes that can drive i2v, most-connected first."""
    refs_set = set(refs)
    candidates = [nid for nid in _of_type(graph, LOAD_IMAGE_TYPES) if nid not in refs_set]
    sampler_up = set(_walks(graph, sampler)) if sampler else set()

    def score(nid: str) -> tuple[int, int]:
        used = any(nid in _links(node).values() for node in graph.values())
        connected = nid in sampler_up
        order = int(nid) if nid.isdigit() else 10**6
        return (2 if connected else 1 if used else 0, -order)

    return sorted(candidates, key=score, reverse=True)


def _frames_node(graph: dict, latent: str, sampler: str) -> str:
    if latent and isinstance(_input_value(graph, latent, "batch_size"), (int, float)):
        return latent
    for nid in _of_type(graph, LATENT_TYPES):
        if isinstance(_input_value(graph, nid, "batch_size"), (int, float)):
            return nid
    for anc in _walks(graph, sampler):
        ct = graph.get(anc, {}).get("class_type") or ""
        if any(m in ct for m in VIDEO_MARKERS):
            if _input_value(graph, anc, "length") not in (None, ""):
                return anc
    return latent


def _size_node(graph: dict, sampler: str) -> str:
    """The node that carries the video width/height (e.g. MiniMaxH3ImageToVideo)."""
    for nid in _walks(graph, sampler):
        inp = graph[nid].get("inputs") or {}
        if "width" in inp and "height" in inp:
            return nid
    for nid, node in graph.items():
        inp = node.get("inputs") or {}
        if "width" in inp and "height" in inp:
            return nid
    return ""


def _fps_node(graph: dict) -> str:
    outputs = sorted(_of_type(graph, VIDEO_OUT_TYPES), key=_nkey)
    for nid in outputs:
        if _input_value(graph, nid, "frame_rate") is not None or \
                _input_value(graph, nid, "fps") is not None:
            return nid
    return outputs[0] if outputs else ""


def infer_workflow(graph: dict) -> dict:
    """Return {kind, t2i, i2v, ref_slots, warnings}.

    `t2i` / `i2v` are semantic-name -> node-id maps ready for config/comfyui.
    Empty values mean "not present in this workflow".
    """
    warnings: list[str] = []
    sampler = _pick_sampler(graph)
    if not sampler:
        return {"kind": "unknown", "t2i": {}, "i2v": {},
                "ref_slots": [], "warnings": ["没有找到采样器节点"]}

    positive, negative = _positive_negative(graph, sampler)
    checkpoint = _checkpoint(graph, sampler)
    latent = _latent(graph, sampler)
    refs = _ref_slots(graph)
    video = _is_video_graph(graph)

    t2i = {
        "positive": positive, "negative": negative, "seed": sampler,
        "width": latent if latent in _of_type(graph, LATENT_TYPES) else "",
        "height": latent if latent in _of_type(graph, LATENT_TYPES) else "",
        "steps": sampler, "cfg": sampler, "sampler": sampler,
        "checkpoint": checkpoint,
        "clip": _loader_of_type(graph, sampler, TEXT_ENCODER_TYPES),
        "vae": _loader_of_type(graph, sampler, VAE_TYPES),
        "sampling": _loader_of_type(graph, sampler, SAMPLING_TYPES),
        "ref_image": refs[0] if refs else "",
    }
    images = _video_image_slots(graph, sampler, refs) if video else []
    size = _size_node(graph, sampler)
    i2v = {
        "image": images[0] if images else "",
        "last_image": images[1] if len(images) > 1 else "",
        "positive": positive, "negative": negative, "seed": sampler,
        "frames": _frames_node(graph, latent, sampler) if video else "",
        "fps": _fps_node(graph) if video else "",
        "width": size if video else "",
        "height": size if video else "",
    }

    if positive and negative and positive == negative:
        warnings.append("正向与负向指向同一个 CLIPTextEncode 节点")
    if not positive:
        warnings.append("未找到正向提示词节点（CLIPTextEncode）")
    if not checkpoint:
        warnings.append("未找到 checkpoint 加载节点")
    if video and images:
        used = any(images[0] in _links(n).values() for n in graph.values())
        if not used:
            warnings.append(f"LoadImage {images[0]} 未接入任何节点，注入首帧可能不生效")

    kind = "i2v" if video else "t2i"
    return {"kind": kind, "t2i": t2i, "i2v": i2v,
            "ref_slots": refs, "warnings": warnings}


def score_workflow(info: dict) -> int:
    """Higher is a better match for its inferred kind."""
    if info.get("kind") == "i2v":
        m = info.get("i2v") or {}
        return sum(3 for k in ("image", "positive", "negative", "seed", "frames", "fps")
                   if m.get(k)) + (2 if m.get("last_image") else 0)
    m = info.get("t2i") or {}
    return sum(2 for k in ("positive", "negative", "seed", "checkpoint", "width")
               if m.get(k)) + (1 if m.get("ref_image") else 0)
