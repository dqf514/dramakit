"""Read the novel in its own encoding, not in whatever the browser assumes.

File.text() decodes as UTF-8 and replaces what it cannot read with U+FFFD.
A GBK novel is mangled in the browser, before the server ever sees it, and
the mangling is written to disk - so the chapter headings become question
marks, the regex finds no chapters, and the whole book lands as one
unreadable block. The damage is not recoverable: the original bytes are
gone by the time they leave the page.

So the file is read as bytes and decoded strictly - UTF-8 first, then the
encodings Chinese novels actually arrive in. Strict, not lenient: a decoder
that reports failure lets us try the next encoding, while one that silently
substitutes characters destroys the text and says nothing.
"""
from pathlib import Path

p = Path(r"E:\\dramakit\\dramakit\\web\\static\\index.html")
s = p.read_text(encoding="utf-8", errors="replace")

if "readNovelFile" in s:
    print("index.html: 已有编码探测读取，跳过")
    raise SystemExit(0)

# the reader itself, placed just before the function that needs it
anchor = "async function createProjectFromGuide(){"
assert anchor in s, "找不到 createProjectFromGuide"

helper = '''// Read a novel in the encoding it actually is. The browser's own text()
// assumes UTF-8 and swaps anything else for U+FFFD, which destroys a GBK
// book before it reaches the server - and destroys it for good, because
// the server is handed the already-mangled text.
async function readNovelFile(file){
  const buf = await file.arrayBuffer();
  const bytes = new Uint8Array(buf);
  const tries = ["utf-8", "gb18030", "gbk", "big5"];
  for(const enc of tries){
    try{
      // fatal:true makes an undecodable byte throw instead of becoming "?",
      // so a wrong guess fails loudly and the next encoding gets a turn
      return new TextDecoder(enc, {fatal:true}).decode(bytes);
    }catch(e){ /* not this encoding; try the next */ }
  }
  // nothing decoded cleanly: hand back what UTF-8 can make of it, and say so
  toast("这个文件的编码认不出来，可能有乱码","err",5000);
  return new TextDecoder("utf-8").decode(bytes);
}

'''
s = s.replace(anchor, helper + anchor, 1)

# use it in place of the lossy File.text()
old_call = "  const text=await picked.text();"
assert old_call in s, "找不到 picked.text() 调用"
s = s.replace(old_call, "  const text=await readNovelFile(picked);", 1)

p.write_text(s, encoding="utf-8")
print("index.html: 上传按文件真实编码解码（UTF-8 严格失败才试 GB18030/GBK/Big5）")
