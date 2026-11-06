"""The dialogue is polished, and the flatness is counted.

The script came out as an interrogation: every line a question and
every answer one line long, nobody lying, nobody interrupting, nobody
with an agenda.  The rules said all of that - a character has a want,
a flaw and an arc, and the lines have to sound like that character -
but rules are abstract and the model needs to see what the difference
looks like.

So the draft goes through an editor: the same scenes, the same
speakers, the same order, the same information, and every line with
somebody's fingerprints on it.  Three before-and-after pairs show what
"polished" means, because that is what the model reads.

And the flatness is counted, so it can be seen rather than felt: how
many of the lines are a question answered straight.
"""
import pathlib

ROOT = pathlib.Path(r"E:\dramakit")


def edit(path, old, new, what):
    p = ROOT / path
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    assert old in text, "没找到：%s（%s）" % (what, path)
    text = text.replace(old, new, 1)
    if crlf:
        text = text.replace("\n", "\r\n")
    p.write_bytes(text.encode("utf-8"))


# --------------------------------------------------------------------------- #
# 1. the editor
# --------------------------------------------------------------------------- #
edit("dramakit/prompts/templates.py",
     '''SCRIPT_USER = """把下面这一集原文改编成短剧剧本。题材：{{genre}}。''',
     '''SCRIPT_POLISH_SYSTEM = """你是短剧剧本编辑，接手一集已经写好的剧本。

结构和情节是对的，台词太机械——一问一答像填表，人物没有态度，没有人在
撒谎、回避、打断、抢白、沉默。你的活是把台词磨成能演的：同样的戏、同样的
信息、同样的顺序，但每一句都带着说话人此刻的算盘。

只输出JSON。"""

SCRIPT_POLISH_USER = """下面是这一集已经写好的剧本，以及它对应的原文。

【原文（只作参照，不要改情节）】
{{text}}

【待打磨的剧本】
{{draft}}

打磨规则：
- 不增删场、不改说话人、不改顺序、不改事件
- 台词句数基本不变（可以少一两句）
- **每场至少要有一处不是"问—答"**：打断、沉默、反问、岔开、撒谎、
  抢白，或者用动作代替回答
- 每个人说话要像他自己：此刻他想要什么、怕什么、瞒什么。台词里要听得
  出他的立场，不要人人都客客气气把话说完
- 重要信息不要靠一问一答直接递出来：让人绕、让人挡、让人说一半
- 旁白只留必要的时空/身份信息，而且不能重复画面已经说出来的
- 保留原文里的关键信息和反转

对照着磨（这是要达到的效果，不是要照抄）：

差：「这是哪儿？」「您自己的卧室。」
好：「这是哪儿……（环顾）这不是我房间。」「太太，这是您的卧室。」

差：「沈总是谁？」「您丈夫，沈律。」
好：「沈总？」（她心口一跳）「谁姓沈。」「太太，您说笑了，夫人也姓沈。」

差：「程菲是谁？」「沈总的新秘书。」
好：「程菲？」（她攥紧杯壁）「这个名字……她是谁？」
「新来的秘书，沈总很看重。」「看重？」陈嫂的手顿了一下，「太太，您今天问得太多了。」

输出JSON：
{"scenes":[{"location":"","time_of_day":"日","summary":"","mood":"","lines":[{"kind":"dialogue","speaker":"","text":"","emotion":"平静"}]}]}"""


SCRIPT_USER = """把下面这一集原文改编成短剧剧本。题材：{{genre}}。''',
     "the polish template")

# --------------------------------------------------------------------------- #
# 2. the flag
# --------------------------------------------------------------------------- #
edit("dramakit/config.py",
     """    opening_recap: bool = True                        # 前情提要
    cold_open: bool = True                            # 开场即冲突""",
     """    opening_recap: bool = True                        # 前情提要
    cold_open: bool = True                            # 开场即冲突
    # 初稿之后再磨一遍台词：同样的戏、同样的信息，但每一句都带态度。
    # 关掉就只写初稿（快，但容易写成一问一答）。
    polish_dialogue: bool = True""",
     "the polish flag")

# --------------------------------------------------------------------------- #
# 3. the stage: the draft, the polish, and the count
# --------------------------------------------------------------------------- #
edit("dramakit/pipeline/script.py",
     """    def _one(job):
        ep, user = job
        data = pool.next().complete_json(T.SCRIPT_SYSTEM, user)
        if isinstance(data, list):
            data = data[0] if data else {}
        scenes = []
        for si, s in enumerate(data.get("scenes", []) or [], 1):
            sc = Scene(id=_id("sc"), index=si, location=s.get("location", ""),
                       time_of_day=s.get("time_of_day", "日"),
                       summary=s.get("summary", ""), mood=s.get("mood", "中性"),
                       bgm_mood=s.get("bgm_mood", ""))
            for li, l in enumerate(s.get("lines", []) or [], 1):
                txt = (l.get("text") or "").strip()
                if not txt:
                    continue
                sc.lines.append(Line(id=_id("ln"), kind=_to_kind(l.get("kind", "dialogue")),
                                     speaker=(l.get("speaker") or "旁白").strip(),
                                     text=txt, emotion=l.get("emotion", "平静")))
            if sc.lines:
                scenes.append(sc)
        # the episode is written and saved here, not after the whole
        # batch: a run that is stopped halfway keeps the episodes that
        # were already done
        ep.scenes = scenes
        ctx.mark(ep, "script", Status.DONE)
        ctx.save()
        return len(scenes)
""",
     """    def _parse(data) -> list:
        \"\"\"The model's answer, as scenes and lines.\"\"\"
        if isinstance(data, list):
            data = data[0] if data else {}
        scenes = []
        for si, s in enumerate(data.get("scenes", []) or [], 1):
            sc = Scene(id=_id("sc"), index=si, location=s.get("location", ""),
                       time_of_day=s.get("time_of_day", "日"),
                       summary=s.get("summary", ""), mood=s.get("mood", "中性"),
                       bgm_mood=s.get("bgm_mood", ""))
            for li, l in enumerate(s.get("lines", []) or [], 1):
                txt = (l.get("text") or "").strip()
                if not txt:
                    continue
                sc.lines.append(Line(id=_id("ln"), kind=_to_kind(l.get("kind", "dialogue")),
                                     speaker=(l.get("speaker") or "旁白").strip(),
                                     text=txt, emotion=l.get("emotion", "平静")))
            if sc.lines:
                scenes.append(sc)
        return scenes

    def _draft_text(scenes: list) -> str:
        \"\"\"The scenes as the editor will see them.\"\"\"
        out = []
        for sc in scenes:
            out.append("【%s / %s】%s" % (sc.location, sc.time_of_day, sc.summary))
            for ln in sc.lines:
                out.append("  %s：%s" % (ln.speaker, ln.text))
        return "\\n".join(out)

    def _one(job):
        ep, user, block = job
        data = pool.next().complete_json(T.SCRIPT_SYSTEM, user)
        scenes = _parse(data)
        # The editor. The same scenes, the same speakers, the same
        # information - and every line with somebody's fingerprints on it.
        # A draft that cannot be polished is kept as it is: a second
        # failure must not cost the first one.
        if scenes and getattr(cfg.segment, "polish_dialogue", True):
            try:
                pol = pool.next().complete_json(
                    T.SCRIPT_POLISH_SYSTEM,
                    T.render(T.SCRIPT_POLISH_USER, text=block[:8000],
                             draft=_draft_text(scenes)))
                polished = _parse(pol)
                if polished:
                    scenes = polished
                    ctx.log.info("script: 第%d集台词已打磨", ep.index)
                else:
                    ctx.log.warning("script: 第%d集打磨没有结果，保留初稿", ep.index)
            except Exception as e:  # noqa: BLE001
                ctx.log.warning("script: 第%d集打磨失败(%s)，保留初稿",
                                ep.index, str(e)[:120])
        # the episode is written and saved here, not after the whole
        # batch: a run that is stopped halfway keeps the episodes that
        # were already done
        ep.scenes = scenes
        ctx.mark(ep, "script", Status.DONE)
        ctx.save()
        return len(scenes)
""",
     "the polish pass")

edit("dramakit/pipeline/script.py",
     """        jobs.append((ep, user))""",
     """        jobs.append((ep, user, block))""",
     "the job carries the text")

edit("dramakit/pipeline/script.py",
     """    for (job, _scenes, err) in results:
        ep, _user = job""",
     """    for (job, _scenes, err) in results:
        ep = job[0]""",
     "the job tuple")

print("台词打磨加上了")
