"""The workflow as the API takes it, with the names the card declares.

Three loader nodes came through the first conversion with no inputs at all
- the model, the text encoder and the video VAE - because their widget
names were guessed and guessed wrong, and a wrong name does not fail
loudly: the input keeps its default and the card reports a missing file.
The names come from /object_info now, which lists a node's inputs in the
order its widgets are saved, so a widget is an input whose type is not a
wire.

The reference slots are the rest. The workflow ships with three voice
inputs unconnected, and a slot left alone loads a placeholder the file
does not contain - so a LoadAudio node is added and wired, and a
character's recorded voice reaches the model instead of being dropped by
the guard that removes empty slots. One, not three: the pipeline fills a
single node, named by ref_audio_node, and the others would sit in the graph
unread.

Three notes come out. The card does not define MarkdownNote, and ComfyUI
refuses a whole prompt that names a type it lacks - the render is lost,
not just the comment.

The model's path through the file also gets repaired. A switch chooses
between the bare loader and the LoRA, but its output goes nowhere: the
attention node takes its model straight from the loader, so the switch
controlled nothing and the LoRA was loaded and never used. The attention
node now reads the switch, which keeps the shipped default - the switch is
off, so the model is the bare loader, exactly as before - while making the
switch mean something when it is turned on.
"""
import json
from pathlib import Path

SRC = Path(r"D:\Downloads\短剧专用.json")
DST = Path(r"E:\dramakit\config\comfyui\i2v_shortdrama.json")
FIELDS = Path(r"E:\dramakit\rounds\tools\widget_fields.json")

# a widget-only node records no input names in the export, so these are
# the ones the export cannot answer for - every other node uses the card's
EXTRA = {
    "PrimitiveStringMultiline": ["value"],
    "PrimitiveFloat": ["value"],
    "PrimitiveInt": ["value"],
    "PrimitiveBoolean": ["value"],
    "ResolutionSelector": ["aspect_ratio", "megapixels", "multiple"],
    "RandomNoise": ["noise_seed", "control_after_generate"],
    "LoadImage": ["image"],
    "LoadAudio": ["audio"],
}


def ui_to_api(data: dict, fields: dict) -> tuple[dict, list, list]:
    """The workflow in API form, whatever form it arrived in.

    A UI export has a nodes array and a links table and needs converting;
    an API export is already the shape /prompt takes. That is all this
    step does - it is about how the file is written. What the workflow
    *does* is fixed afterwards, by the same code either way, because a
    switch that never reaches the LoRA is wrong in both shapes.
    """
    if "nodes" not in data:
        return data, [], []

    links = {}
    for row in data.get("links", []) or []:
        if isinstance(row, list) and len(row) >= 5:
            lid, frm, fslot, to, tslot = row[:5]
            links[str(lid)] = (str(frm), int(fslot), str(to), int(tslot))

    feeds: dict[str, dict[str, tuple[str, int]]] = {}
    for node in data.get("nodes", []) or []:
        nid = str(node.get("id"))
        for inp in node.get("inputs") or []:
            lid = inp.get("link")
            if lid is not None:
                feeds.setdefault(nid, {})[str(inp.get("name"))] = links.get(str(lid))

    out: dict = {}
    empty: list[str] = []
    dropped: list[str] = []
    for node in data.get("nodes", []) or []:
        nid = str(node.get("id"))
        cls = node.get("type")
        if not cls:
            continue
        # The card does not have these, and a prompt naming a type the card
        # lacks is refused in full - so they go, comments and all.
        if cls in ("MarkdownNote", "Note"):
            dropped.append(f"#{nid} {cls}")
            continue
        inputs: dict = {}
        wv = node.get("widgets_values")
        names = EXTRA.get(cls) or fields.get(cls) or []
        if isinstance(wv, list) and names:
            for name, val in zip(names, wv):
                if val is not None:
                    inputs[name] = val
        elif isinstance(wv, list) and len(wv) == 1:
            inputs["value"] = wv[0]
        elif isinstance(wv, dict):
            inputs.update(wv)
        for name, src in (feeds.get(nid) or {}).items():
            if src:
                inputs[name] = [src[0], src[1]]
        if not inputs and node.get("widgets_values") is not None:
            empty.append(f"#{nid} {cls}")
        out[nid] = {"class_type": cls, "inputs": inputs}

    # anything that pointed at a node now gone would be a dangling wire
    for node in out.values():
        for name, src in list((node.get("inputs") or {}).items()):
            if isinstance(src, list) and str(src[0]) in {
                    d.split()[0][1:] for d in dropped}:
                node["inputs"].pop(name)
    return out, empty, dropped


def fix_model_path(graph: dict) -> str:
    """Let the switch decide, instead of bypassing it.

    The file wires a switch that picks between the bare loader and the
    LoRA, and then takes the model from the loader directly - so the switch
    controlled nothing and the LoRA was loaded and never used. The attention
    node reads the switch instead. The switch ships off, which selects the
    bare loader: the render is the one the file already produced, and the
    LoRA becomes reachable by flipping it.
    """
    switch = next((nid for nid, n in graph.items()
                   if n.get("class_type") == "ComfySwitchNode"
                   and "on_true" in (n.get("inputs") or {})), None)
    if switch is None:
        return "没找到模型开关节点"
    model_in = None
    for nid, n in graph.items():
        if n.get("class_type") == "PathchSageAttentionKJ":
            model_in = (nid, n)
            break
    if model_in is None:
        return "没找到 PathchSageAttentionKJ"
    nid, node = model_in
    before = (node.get("inputs") or {}).get("model")
    node.setdefault("inputs", {})["model"] = [switch, 0]
    return (f"#{nid}.model: {before} -> [#{switch},0]（开关控制 LoRA）")


def set_run_settings(graph: dict) -> list[str]:
    """Turn the accelerator on, and set the step count it was trained for.

    The file ships with the switch off, which puts the bare model in the
    path and twenty steps through it: the LoRA is loaded and never used,
    and the sampler does two and a half times the work the eight-step
    adapter was made for. Measured on this card, that combination costs
    thirty minutes for a ten-second clip where the eight-step one with the
    LoRA costs eleven.

    The step count on the fast branch is four in the file, left over from
    a Lightning setup, while the adapter is named for eight steps and the
    workflow this replaces ran eight. Eight it is - the fast branch is
    what the switch reaches, so one boolean turns all of this on.
    """
    notes = []
    switch = next((nid for nid, n in graph.items()
                   if n.get("class_type") == "PrimitiveBoolean"), None)
    if switch is not None:
        was = (graph[switch].get("inputs") or {}).get("value")
        graph[switch].setdefault("inputs", {})["value"] = True
        notes.append(f"#{switch} 开关 {was} -> True（LoRA + 快速分支生效）")

    # the step value behind the switch's true branch
    steps_switch = None
    for nid, n in graph.items():
        if n.get("class_type") != "ComfySwitchNode":
            continue
        ins = n.get("inputs") or {}
        if "on_true" not in ins:
            continue
        true_src = ins.get("on_true")
        if not (isinstance(true_src, list) and true_src):
            continue
        src = graph.get(str(true_src[0])) or {}
        if src.get("class_type") == "PrimitiveInt":
            steps_switch = str(true_src[0])
            break
    if steps_switch:
        was = (graph[steps_switch].get("inputs") or {}).get("value")
        graph[steps_switch].setdefault("inputs", {})["value"] = 8
        notes.append(f"#{steps_switch} 快速分支步数 {was} -> 8"
                     f"（4 步出的片偏软/有伪影，回到 8 步；"
                     f"配 turbo_8step LoRA 实测 243 帧约 14.5 分钟）")
    return notes


def add_references(graph: dict) -> list[str]:
    """Connect the reference slots the workflow left unconnected.

    The model takes as many pictures as are wired to it, and the pipeline
    sends as many as a shot has: the frame it continues from, where the
    shot before it ended, then a face and a turnaround for each character,
    then the room and any prop in the action. Two characters make eight.
    The file wired two, so a shot with a second character lost its sheets
    and its room to a zip that stops at the shorter of the two lists -
    silently, since the pictures it dropped were simply never sent.

    Nine, matching the workflow this replaced. A slot with no picture is
    taken out of the job before it is sent, so extra slots cost nothing
    when a shot has fewer.
    """
    notes = []
    model = next((nid for nid, n in graph.items()
                  if n.get("class_type") == "MiniMaxH3ReferenceToVideo"), None)
    if model is None:
        return ["找不到 MiniMaxH3ReferenceToVideo"]

    ins = graph[model].setdefault("inputs", {})
    next_id = max((int(k) for k in graph if str(k).isdigit()), default=100) + 10

    if not ins.get("ref_audios.ref_audio_0"):
        graph[str(next_id)] = {"class_type": "LoadAudio", "inputs": {}}
        ins["ref_audios.ref_audio_0"] = [str(next_id), 0]
        notes.append(f"ref_audio_0 -> 节点 {next_id}（ref_audio_node 要指向它）")
        next_id += 1

    added = 0
    for i in range(9):
        slot = f"ref_images.ref_image_{i}"
        if ins.get(slot):
            continue
        graph[str(next_id)] = {"class_type": "LoadImage", "inputs": {}}
        ins[slot] = [str(next_id), 0]
        added += 1
        next_id += 1
    if added:
        notes.append(f"ref_image 槽补到 9 个（新增 {added} 个 LoadImage）")
    return notes


if __name__ == "__main__":
    fields = json.loads(FIELDS.read_text(encoding="utf-8"))
    api, empty, dropped = ui_to_api(json.loads(SRC.read_text(encoding="utf-8")), fields)
    notes = add_references(api)
    notes.append(fix_model_path(api))
    notes += set_run_settings(api)
    DST.write_text(json.dumps(api, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"转换完成: {len(api)} 个节点 -> {DST}")
    print()
    print("=== 删掉的节点（卡上没有）===")
    for d in dropped:
        print("  " + d)
    if not dropped:
        print("  （无）")
    print()
    print("=== 没拿到输入的节点（应为空）===")
    for e in empty:
        print("  " + e)
    if not empty:
        print("  （无）")
    print()
    for n in notes:
        print("  " + n)
    print()
    print("=== 关键节点 ===")
    for nid in ("127", "128", "119", "120", "145", "151", "141", "136",
                "138", "115", "130", "129", "137", "139"):
        node = api.get(nid)
        if node:
            print(f"  #{nid:<5} {node['class_type']:<32} "
                  f"{json.dumps(node['inputs'], ensure_ascii=False)[:130]}")
