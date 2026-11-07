"""Set the look of this drama.

The look is the frame, the size and the style the whole drama is made
in - the camera language follows it, from the character sheets to the
last clip.
"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8080"
SLUG = sys.argv[1] if len(sys.argv) > 1 else ""
STYLE = sys.argv[2] if len(sys.argv) > 2 else "xianxia"
RATIO = sys.argv[3] if len(sys.argv) > 3 else "9:16"
SIZE = sys.argv[4] if len(sys.argv) > 4 else "1080x1920"


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


w, h = SIZE.split("x")
body = {"project": SLUG, "aspect_ratio": RATIO, "width": int(w), "height": int(h),
        "style": STYLE}
r = post("/api/project/look", body)
print("  ", json.dumps(r, ensure_ascii=False)[:500])
ad = r.get("art_direction") or {}
print("  画幅 %s %sx%s" % (ad.get("aspect_ratio"), ad.get("frame_width"),
                           ad.get("frame_height")))
print("  画风 %s" % ad.get("style"))
print("  提示词 %s" % (ad.get("style_prompt_prefix") or "")[:140])
print("  年代 %s  色调 %s" % (ad.get("era"), ad.get("color_palette")))
