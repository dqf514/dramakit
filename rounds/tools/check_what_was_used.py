"""What did the card actually load for the last clip?

The workflow says which LoRA and how many steps. What matters is what
the card was given - a file that is not there, a name that fell back to
something else, a step count that was quietly changed. The card keeps
the graph it was given, so it can be read back.
"""
import json
import sys
import urllib.request


def history(host, limit=8):
    with urllib.request.urlopen(f"http://{host}/history?max_items={limit}",
                                timeout=90) as r:
        return json.loads(r.read())


def show(host, label):
    print(f"=== {label} ({host}) ===")
    try:
        hist = history(host)
    except Exception as e:  # noqa: BLE001
        print("  读不到:", type(e).__name__)
        return
    for pid, rec in hist.items():
        p = rec.get("prompt")
        g = p[2] if isinstance(p, list) and len(p) > 2 else {}
        if not g:
            continue
        if not any("ReferenceToVideo" in str(n.get("class_type", "")) for n in g.values()):
            continue
        st = rec.get("status") or {}
        print(f"  --- pid {pid[:8]}  {st.get('status_str')} ---")
        for nid, node in sorted(g.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            ct = str(node.get("class_type", ""))
            ins = node.get("inputs") or {}
            if ct == "LoraLoaderModelOnly":
                print(f"      LoRA: {ins.get('lora_name')}  strength={ins.get('strength_model')}")
            elif ct == "PrimitiveInt":
                print(f"      步数: {ins.get('value')}")
            elif ct == "UNETLoader":
                print(f"      模型: {ins.get('unet_name')}  dtype={ins.get('weight_dtype')}")
            elif ct == "CLIPLoader":
                print(f"      编码器: {ins.get('clip_name')}  device={ins.get('device')}")
            elif ct == "VAELoader":
                print(f"      VAE: {ins.get('vae_name')}")
            elif ct == "PathchSageAttentionKJ":
                print(f"      SageAttention: 在")
            elif ct == "MiniMaxH3ReferenceToVideo":
                print(f"      长度: {ins.get('length')}  参考图槽: "
                      + str(len([k for k in ins if k.startswith('ref_images.ref_image_')])))
        break
    print()


if __name__ == "__main__":
    show("127.0.0.1:8188", "本机 5080")
    show("192.168.31.8:8188", "远端 3090-a")
    show("192.168.31.8:8189", "远端 3090-b")
