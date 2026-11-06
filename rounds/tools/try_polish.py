"""Does the polish pass make the dialogue less flat?

It takes the episode that is already written, hands it to the editor,
and measures the same thing twice: how much of the dialogue is a
question answered straight.

    python rounds/tools/try_polish.py [episode]
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(r"E:\dramakit")
sys.path.insert(0, str(ROOT))

from dramakit.config import Config  # noqa: E402
from dramakit.pipeline.script import _flatness  # noqa: E402
from dramakit.prompts import templates as T  # noqa: E402
from dramakit.project import ProjectStore  # noqa: E402
from dramakit.providers import build_llm  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
cfg = Config.load(Config.discover())
store = ProjectStore.open(ROOT / "projects" / "穿成亿万总裁他前妻")
proj = store.load()
ep = next(e for e in proj.episodes if e.index == n)
block = store.abs(ep.source_path).read_text(encoding="utf-8")


def draft_text(scenes):
    out = []
    for sc in scenes:
        out.append("【%s / %s】%s" % (sc.location, sc.time_of_day, sc.summary))
        for ln in sc.lines:
            out.append("  %s：%s" % (ln.speaker, ln.text))
    return "\n".join(out)


def parse(data):
    if isinstance(data, list):
        data = data[0] if data else {}
    scenes = []
    for si, s in enumerate(data.get("scenes", []) or [], 1):
        lines = []
        for l in s.get("lines", []) or []:
            txt = (l.get("text") or "").strip()
            if txt:
                lines.append((l.get("speaker") or "旁白", txt, l.get("emotion", "")))
        if lines:
            scenes.append((s.get("summary", ""), lines))
    return scenes


before = parse([{"scenes": [{"location": sc.location, "time_of_day": sc.time_of_day,
                              "summary": sc.summary,
                              "lines": [{"speaker": ln.speaker, "text": ln.text,
                                         "emotion": ln.emotion}
                                        for ln in sc.lines]} for sc in ep.scenes]}])
b_pairs, b_lines = _flatness(ep.scenes)
print("  打磨前: %d 句, %d 处一问一答 = %d%%" % (b_lines, b_pairs, int(b_pairs * 100 / max(1, b_lines))))

llm = build_llm(cfg.llm)
print("  模型:", llm.cfg.model, llm.cfg.base_url)
data = llm.complete_json(T.SCRIPT_POLISH_SYSTEM,
                          T.render(T.SCRIPT_POLISH_USER, text=block[:8000],
                                   draft=draft_text(ep.scenes)))
after = parse(data)
a_lines = sum(len(s[1]) for s in after)
a_pairs = 0
for _summary, lines in after:
    for i, (spk, txt, emo) in enumerate(lines[:-1]):
        if "？" not in txt and "?" not in txt:
            continue
        nxt = lines[i + 1][1]
        if "？" in nxt or "?" in nxt or len(nxt) > 12:
            continue
        a_pairs += 1
print("  打磨后: %d 句, %d 处一问一答 = %d%%" % (a_lines, a_pairs, int(a_pairs * 100 / max(1, a_lines))))
print()
for summary, lines in after[:1]:
    print("  【%s】" % summary)
    for spk, txt, emo in lines:
        print("    %-6s %s" % (spk, txt))
