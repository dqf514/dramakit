#!/usr/bin/env python3
"""Put the strata engine on the second card, and only the second card.

The engine serves Qwen3.8-27B-FP8: twenty-nine gigabytes of weights, and
a card has twenty-four. Split across two cards it fitted; on one card it
has to give something back to the host's memory, and the part that lives
there is fetched over the bus for every token.

The other card is not free - it is making the films - so the engine is
put on the second one alone, with the context sized to what is left
after the weights. The old file is kept, so this is one command to undo.
"""
import shutil
import sys
from pathlib import Path

COMPOSE = Path("/opt/deploy/docker-compose.yml")
BACKUP = Path("/opt/deploy/docker-compose.yml.bak-before-single-card")

text = COMPOSE.read_text(encoding="utf-8")
if BACKUP.exists():
    print("备份已存在，不覆盖")
else:
    shutil.copy2(COMPOSE, BACKUP)
    print("备份 ->", BACKUP)

old_env = "- CUDA_VISIBLE_DEVICES=0,1"
new_env = "- CUDA_VISIBLE_DEVICES=1"
if old_env not in text:
    if new_env in text:
        print("显存选择已经是 1 了")
    else:
        print("找不到 CUDA_VISIBLE_DEVICES 这一行，没动")
        sys.exit(1)
else:
    text = text.replace(old_env, new_env)
    print("CUDA_VISIBLE_DEVICES: 0,1 -> 1")

replacements = [
    ("--tensor-parallel-size 2", "--tensor-parallel-size 1"),
    ("--max-model-len 131072", "--max-model-len 32768"),
    ("--max-num-seqs 96", "--max-num-seqs 16"),
    ("--gpu-memory-utilization 0.95", "--gpu-memory-utilization 0.92"),
]
for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        print(f"  {old} -> {new}")
    else:
        print(f"  （没找到 {old}）")

# the weights that do not fit on the card live in the host's memory
if "--cpu-offload-gb" not in text:
    text = text.replace("--kv-cache-dtype fp8",
                        "--kv-cache-dtype fp8 --cpu-offload-gb 7")
    print("  加了 --cpu-offload-gb 7（29G 权重单卡放不下，挪 7G 到内存）")

COMPOSE.write_text(text, encoding="utf-8")
print("写好了", COMPOSE)
print()
print("--- 现在的 vllm 那一段 ---")
block = text.split("  vllm:")[1].split("\n  admin-app:")[0]
print("  vllm:" + block[:1400])
