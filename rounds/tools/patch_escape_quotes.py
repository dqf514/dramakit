"""The quotes inside the templates have to be escaped.

A template that shows the model the shape of the original text writes
three double quotes around it - and three double quotes are also how
Python ends the string the template lives in.  The templates that were
written before escaped them; the new ones did not.
"""
import pathlib

P = pathlib.Path(r"E:\dramakit\dramakit\prompts\templates.py")
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

# the two templates that show the source text
old = '''原文：
"""
{{text}}
"""
'''
new = '''原文：
\\"\\"\\"
{{text}}
\\"\\"\\"
'''
n = text.count(old)
assert n >= 2, "找到 %d 处" % n
text = text.replace(old, new)

old2 = '''这一集的全部原文（这场戏的台词在里面）：
"""
{{text}}
"""
'''
new2 = '''这一集的全部原文（这场戏的台词在里面）：
\\"\\"\\"
{{text}}
\\"\\"\\"
'''
assert old2 in text, "没找到第二处"
text = text.replace(old2, new2, 1)

if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("引号转义好了")
