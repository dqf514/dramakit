"""The sentence every voice sample is read in.

The constant was written into the patch script instead of the file, so
generate_voice_refs called a name that did not exist and every character
failed with the same error - caught per character, which is why eleven
warnings appeared instead of one crash.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\pipeline\\character.py")
s = p.read_text(encoding="utf-8")

if "VOICE_SAMPLE =" in s:
    print("character.py: VOICE_SAMPLE 已在")
    raise SystemExit(0)

anchor = "def generate_voice_refs("
i = s.find(anchor)
assert i > 0, "找不到 generate_voice_refs"

const = '''# The sentence every voice sample is read in. The same one for everyone:
# what is being compared is the voice, so if the words differ the
# difference is the script rather than the person.
VOICE_SAMPLE = ("这是角色的声音样本。用你平时说话的语气，"
                "自然地把这句话读出来，语速适中，情绪平稳。")


'''
s = s[:i] + const + s[i:]
p.write_text(s, encoding="utf-8")
print("character.py: VOICE_SAMPLE 定义补上了")
