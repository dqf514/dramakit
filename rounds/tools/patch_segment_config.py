"""The drama is cut for a phone.

A short drama is not a long one cut short: the episodes are short, the
turns come fast, and every episode ends on something that makes the
next one necessary.  So the episode is two and a half minutes, the
book is cut into thirty of them, and the script is written to fit the
time it has.
"""
import pathlib
import re

ROOT = pathlib.Path(r"E:\dramakit")

# ---- the config file ----------------------------------------------------- #
P = ROOT / "config" / "default.yaml"
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

m = re.search(r"^segment:\n(?:[ \t]+.*\n)*", text, re.M)
assert m, "配置里没找到 segment 段"
block = m.group(0)

new_block = block
new_block = re.sub(r"(?m)^(\s*)strategy:.*$", r"\1strategy: fixed_count", new_block)
new_block = re.sub(r"(?m)^(\s*)episode_count:.*$", r"\1episode_count: 30", new_block)
new_block = re.sub(r"(?m)^(\s*)episode_duration:.*$", r"\1episode_duration: 150", new_block)
new_block = re.sub(r"(?m)^(\s*)max_episode_seconds:.*$",
                   r"\1max_episode_seconds: 180", new_block)

text = text[:m.start()] + new_block + text[m.end():]
if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("  配置里的分集参数改了")
for line in new_block.split("\n"):
    if any(k in line for k in ("strategy", "episode_count", "episode_duration",
                               "max_episode_seconds", "respect_chapters")):
        print("   ", line.strip())
