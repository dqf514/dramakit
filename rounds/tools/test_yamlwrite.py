"""Does the node writer put the settings back where they were.

The fleet is a list of mappings in the config, and the writer edits one
entry in place rather than rewriting the list - so the comments beside the
settings, which are the only record of why a card is set up the way it is,
survive. It also has to be able to add a key that was not there and to
replace the nested weight map without disturbing the entry after it.

So the file is copied, the writer is asked to change one node in several
ways, and the result is checked three ways: the YAML still parses, the
values are the ones asked for, and the rest of the file is untouched.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")

import yaml   # noqa: E402
from dramakit.ai import autoconfig   # noqa: E402
from dramakit.config import Config   # noqa: E402

SRC = Path(r"E:\dramakit\config\default.yaml")
out = []

tmp = Path(tempfile.mkdtemp()) / "default.yaml"
shutil.copy(SRC, tmp)
before_text = tmp.read_text(encoding="utf-8")
before = yaml.safe_load(before_text)

out.append("=== 原文件 ===")
for n in before["comfyui"]["nodes"]:
    out.append(f"  {n['name']}: enabled={n.get('enabled')} "
               f"base={n.get('base_url')} overrides={list((n.get('graph_overrides') or {}))}")

# --- write -------------------------------------------------------------
out.append("")
out.append("=== 写入测试 ===")
new_nodes = [
    {"name": "gpu3090-a",
     "enabled": False,
     "roles": ["i2v", "t2i"],
     "base_url": "http://10.0.0.9:9999",
     "transfer": "shared",
     "ssh_host": "10.0.0.9",
     "ssh_user": "someone",
     "remote_models": "/data/other/models",
     "graph_overrides": {"127": {"unet_name": "new_unet.safetensors"},
                         "119": {"vae_name": "new_vae.safetensors"}},
     "workflows": {"i2v": "config/comfyui/i2v_shortdrama.json"}},
    {"name": "gpu3090-b",
     "enabled": True,
     "base_url": "http://10.0.0.8:8189"},
]
try:
    autoconfig.save_nodes(tmp, new_nodes)
    out.append("  写入成功")
except Exception as e:  # noqa: BLE001
    import traceback
    out.append(f"  **写入失败**: {type(e).__name__}: {e}")
    out.append(traceback.format_exc()[-1500:])
    Path(r"C:\Users\David\AppData\Local\Temp\opencode\yamlwrite.txt").write_text(
        "\n".join(out), encoding="utf-8")
    print("wrote")
    raise SystemExit

after_text = tmp.read_text(encoding="utf-8")
after = yaml.safe_load(after_text)

out.append("")
out.append("=== 写入后的节点 ===")
for n in after["comfyui"]["nodes"]:
    out.append(f"  {n['name']}: enabled={n.get('enabled')} roles={n.get('roles')} "
               f"base={n.get('base_url')} transfer={n.get('transfer')} "
               f"ssh={n.get('ssh_host')}/{n.get('ssh_user')} "
               f"rm={n.get('remote_models')}")
    out.append(f"      overrides={n.get('graph_overrides')}")
    out.append(f"      workflows={n.get('workflows')}")

# --- checks ------------------------------------------------------------
out.append("")
out.append("=== 校验 ===")
a = {n["name"]: n for n in after["comfyui"]["nodes"]}
ok = True
for n in new_nodes:
    got = a.get(n["name"])
    if got is None:
        out.append(f"  ✗ {n['name']} 不见了")
        ok = False
        continue
    for k, v in n.items():
        if k == "name":
            continue
        if got.get(k) != v:
            out.append(f"  ✗ {n['name']}.{k} = {got.get(k)!r}，期望 {v!r}")
            ok = False
out.append("  值全部对上" if ok else "  **有不一致**")

# untouched parts
for key in ("llm", "tts", "characters", "comfyui"):
    if key == "comfyui":
        continue
    if before.get(key) != after.get(key):
        out.append(f"  ✗ 段 {key} 被改了")
        ok = False
out.append("  其他段未被改动" if ok else "  **其他段被动了**")

# comments kept?
n_before = before_text.count("#")
n_after = after_text.count("#")
out.append(f"  注释数 {n_before} -> {n_after}")

out.append("")
out.append("=== 写入后的那几行（看格式）===")
lines = after_text.split("\n")
show = False
for i, ln in enumerate(lines):
    if "- name: gpu3090-a" in ln:
        show = True
    if show:
        out.append(f"  {ln}")
        if i > 0 and "- name: gpu3090-b" in ln:
            break
    if show and i > lines.index(ln) + 30:
        break

# config still loads
try:
    cfg = Config.load(tmp)
    out.append("")
    out.append(f"  Config.load 通过；节点数 {len(cfg.comfyui.nodes)}")
    for n in cfg.comfyui.nodes:
        out.append(f"    {n.name}: enabled={n.enabled} {n.base_url} "
                   f"overrides={n.graph_overrides} workflows={n.workflows}")
except Exception as e:  # noqa: BLE001
    out.append(f"  **Config.load 失败**: {e}")

Path(r"C:\Users\David\AppData\Local\Temp\opencode\yamlwrite.txt").write_text(
    "\n".join(out), encoding="utf-8")
print("wrote")
