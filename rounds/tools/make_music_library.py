"""Fill the music library, once, so every run afterwards has a score.

The pipeline asks for a track by mood and the library hands back a file.
An empty library means the finished film has only the sound the video
model made, which is not a score.

So the library is made here rather than during a run: one track per
mood, written by a local music model, named after the mood so the
library can find it by name. Doing it once and keeping it means a run
never waits for a model, and the same tracks serve every project.

The brief for each mood is written by hand rather than translated - the
music model answers to a description of instruments and pace, not to a
mood word on its own.
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, r"E:\dramakit")
sys.path.insert(0, r"E:\dramakit\rounds\tools")

from build_music_wf import build  # noqa: E402

BASE = "http://127.0.0.1:8188"
LIB = Path(r"E:\dramakit\assets\music")
TMP = Path(r"E:\dramakit\assets\music\.tmp")

# mood -> (brief, bpm, key, seconds, seed)
# The brief says what to hear: the instruments, the pace, the texture.
# The seed is per mood: a fixed seed makes the same track every time, and
# a brief the model does not answer to needs another try, not another
# copy of the same silence.
BRIEFS = {
    "紧张": ("cinematic tension, instrumental, no vocals, pulsing low strings, "
             "distant percussion, rising heartbeat, no resolution", 108, "D minor", 60, 1001),
    "悬疑": ("mysterious suspense, instrumental, no vocals, sparse detuned piano, "
             "low drone, occasional high string note, hollow room", 76, "A minor", 60, 1002),
    "悲伤": ("sad melancholy, instrumental, no vocals, solo piano, slow strings, "
             "long silence between notes, winter", 62, "F minor", 60, 1003),
    "欢快": ("cheerful bright pop, instrumental, no vocals, acoustic guitar, "
             "light clapping percussion, bouncy bass, sunny", 118, "C major", 60, 1004),
    "温馨": ("warm gentle acoustic, instrumental, no vocals, soft piano, "
             "fingerpicked guitar, soft brush drums, home", 82, "G major", 60, 1005),
    "恢弘": ("epic heroic orchestral, instrumental, no vocals, brass fanfare, "
             "wide timpani, choir swell, slow majestic rise", 84, "D minor", 60, 1006),
    "激昂": ("energetic driving rock orchestra, instrumental, no vocals, "
             "electric guitar riff, pounding drums, rising build", 132, "E minor", 60, 1007),
    "恐怖": ("horror scene, instrumental, no vocals, low tremolo strings, "
             "dissonant violin, timpani hits, ominous drone", 92, "C minor", 60, 7717),
    "浪漫": ("tender romantic, instrumental, no vocals, soft piano and violin, "
             "warm strings, slow sway", 72, "F major", 60, 1009),
    "愤怒": ("aggressive anger, instrumental, no vocals, heavy percussion, "
             "brass stabs, distorted low end, relentless", 140, "E minor", 60, 1010),
    "平静": ("calm minimal ambient, instrumental, no vocals, soft synth pads, "
             "slow breath, no percussion, open space", 66, "C major", 60, 1011),
    "搞笑": ("playful quirky comedy, instrumental, no vocals, pizzicato strings, "
             "marimba, bouncy tuba, comic timing", 124, "F major", 60, 1012),
    "中性": ("neutral cinematic underscore, instrumental, no vocals, soft pads "
             "and muted piano, unobtrusive, steady", 84, "C major", 60, 1013),
}


def post(path, body, timeout=180):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(path, timeout=300):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


def one(mood: str, tags: str, seconds: float, bpm: int, key: str,
        seed: int, variant: int) -> Path | None:
    dest = LIB / (f"{mood}.mp3" if variant == 0 else f"{mood}_{variant}.mp3")
    if dest.exists() and dest.stat().st_size > 50_000:
        print(f"  {dest.name} 已有，跳过", flush=True)
        return dest
    g = build(tags, seconds=seconds, seed=seed, bpm=bpm, key=key)
    g["10"]["inputs"]["filename_prefix"] = "music/lib"
    t0 = time.time()
    try:
        pid = post("/prompt", {"prompt": g, "client_id": "musiclib"})["prompt_id"]
    except urllib.error.HTTPError as e:
        print(f"  {mood} 提交失败: {e.code} {e.read().decode('utf-8','replace')[:300]}",
              flush=True)
        return None
    rec = None
    while time.time() - t0 < 1200:
        time.sleep(4)
        hist = json.loads(get("/history/" + pid))
        rec = hist.get(pid)
        if rec and (rec.get("status") or {}).get("status_str") in ("success", "error"):
            break
    if not rec or (rec.get("status") or {}).get("status_str") != "success":
        print(f"  {mood} 渲染失败", flush=True)
        return None
    name = sub = typ = None
    for out in (rec.get("outputs") or {}).values():
        for a in (out.get("audio") or []) + (out.get("gifs") or []):
            name, sub, typ = a.get("filename"), a.get("subfolder") or "", a.get("type") or "output"
    if not name:
        print(f"  {mood} 没有音频输出", flush=True)
        return None
    raw = get("/view?filename=%s&subfolder=%s&type=%s" % (name, sub, typ))
    TMP.mkdir(parents=True, exist_ok=True)
    tmp = TMP / name
    tmp.write_bytes(raw)
    # The model writes at whatever level it likes: some tracks come out
    # twenty decibels under the others, and one came out silent. A bed
    # that is quiet under one scene and loud under the next is worse than
    # no bed, so every track is brought to the same loudness here - once,
    # in the library, rather than every time a scene asks for one.
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp),
                        "-af", "loudnorm=I=-18:TP=-1.5:LRA=11",
                        "-c:a", "libmp3lame", "-q:a", "3", str(dest)],
                       capture_output=True)
    tmp.unlink(missing_ok=True)
    if r.returncode != 0 or not dest.exists():
        print(f"  {mood} 转 mp3 失败: {r.stderr.decode('utf-8','replace')[:200]}", flush=True)
        return None
    print(f"  {dest.name}  {time.time()-t0:.0f} 秒  "
          f"{dest.stat().st_size/1024:.0f} KB", flush=True)
    return dest


def main():
    LIB.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    made = 0
    for i, (mood, (tags, bpm, key, secs, seed)) in enumerate(BRIEFS.items()):
        if only and mood not in only:
            continue
        print(f"[{time.strftime('%H:%M:%S')}] {mood}", flush=True)
        if one(mood, tags, secs, bpm, key, seed, 0):
            made += 1
    print(f"=== 曲库：{made} 首 ===", flush=True)
    for f in sorted(LIB.glob("*.mp3")):
        print(f"  {f.name:16} {f.stat().st_size/1024:7.0f} KB", flush=True)


if __name__ == "__main__":
    main()
