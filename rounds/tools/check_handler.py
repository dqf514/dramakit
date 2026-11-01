"""The web handler is created by the app, so the config is the app's."""
from pathlib import Path
import re

p = Path(r"E:\\dramakit\\dramakit\\web\\server.py")
s = p.read_text(encoding="utf-8")

# find how the handler class is created and what attribute holds the app
m = re.search(r"class (\w+)\(.*?BaseHTTPRequestHandler.*?\):\n(.*?)def _route_get_api", s, re.S)
cls = m.group(1) if m else ""
print("handler 类:", cls)

# how the app passes itself: look for make_handler / partial / functools
for pat in ("functools.partial", "make_server", "serve(", "ThreadingHTTPServer", "HTTPServer"):
    i = s.find(pat)
    if i > 0:
        print("  找到:", pat, "→", s[i - 80:i + 160].replace("\n", " | ")[:220])
