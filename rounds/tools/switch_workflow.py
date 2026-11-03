"""Point the pipeline at the short-drama workflow, and name its nodes.

The config named the nodes of the workflow it was using: prompt on 104,
seed on 15, size on 104. The new file numbers its nodes differently and
keeps its prompt in a control node rather than on the model, so every one
of those ids would land on the wrong node - a prompt written to a node
that has no such input leaves the placeholder in place, and the card
renders the words that were in the file.

The mapping is written from the file as it now stands: the first frame
goes to the picture loader that feeds ref_image_0, the prompt and the
size to the model node that has those inputs, the seed to the noise node
and the frame rate to the video writer.

The remote card's weight overrides name nodes too - 13, 6, 11 - and those
ids belong to the old file. They are updated to the new ones, or the card
would go looking for a text encoder at a node that does not exist and fall
back to weights Ampere cannot run.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\config\\default.yaml")
lines = p.read_text(encoding="utf-8").split("\n")

# ---------------------------------------------------------- workflow -----
wf_i = next(i for i, l in enumerate(lines) if l.strip().startswith("i2v_workflow:"))
indent = lines[wf_i][: len(lines[wf_i]) - len(lines[wf_i].lstrip())]
lines[wf_i] = f'{indent}i2v_workflow: config/comfyui/i2v_shortdrama.json'
print(f"  i2v_workflow 行 {wf_i + 1} -> i2v_shortdrama.json")

# ------------------------------------------------------------ nodes -------
n_i = next(i for i, l in enumerate(lines) if l.strip() == "i2v_nodes:")
n_indent = lines[n_i][: len(lines[n_i]) - len(lines[n_i].lstrip())]
child = n_indent + "  "
new_nodes = [
    ('image', '"137"', "LoadImage（ref_image_0），首帧落这里"),
    ('last_image', '"165"', "交接帧（ref_video_0）"),
    ('positive', '"136"', "MiniMaxH3ReferenceToVideo 节点写 prompt"),
    ('negative', '""', "H3 无负向提示词"),
    ('seed', '"129"', "RandomNoise 节点写 noise_seed"),
    ('frames', '"136"', "节点写 length"),
    ('fps', '"130"', "CreateVideo 节点写 fps"),
    ('width', '"136"', "节点写 width"),
    ('height', '"136"', "节点写 height"),
]
j = n_i + 1
while j < len(lines) and (lines[j].startswith(child) or not lines[j].strip()):
    if not lines[j].strip():
        break
    j += 1
print(f"  i2v_nodes 行 {n_i + 1}~{j} 替换为 {len(new_nodes)} 项")
lines[n_i + 1:j] = [
    f'{child}{k}: {v}   # {note}' for k, v, note in new_nodes
]

# ------------------------------------------------------ weight overrides --
# the new file's loader nodes: text encoder, sampler model, video VAE
repl = {
    '"13": {clip_name:': '"128": {clip_name:',
    '"6": {unet_name:': '"127": {unet_name:',
    '"11": {vae_name:': '"119": {vae_name:',
}
changed = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    for old, new in repl.items():
        if stripped.startswith(old):
            lines[i] = line.replace(old, new, 1)
            changed += 1
print(f"  graph_overrides 改了 {changed} 行节点 id")

p.write_text("\n".join(lines), encoding="utf-8")
print("default.yaml 已更新")
