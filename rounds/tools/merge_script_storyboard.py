"""The screenplay and the shots, written in one breath.

They were two stages: the writer made a script, and the director read
it and made a shot list.  That is how a film is made - but a film's
script is written for people to act, and here it is written for a model
to draw.  Between the two there was a translation, and a translation
loses things: the novel's pictures were dropped on the way.

So they are one stage now.  The episode's shape and its beats are
settled first, and then each scene is written in one call - the lines
and the shots that cover them - so the coverage is designed for the
words instead of guessing what they were about.

    python rounds/tools/merge_script_storyboard.py
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
# 1. the two templates
# --------------------------------------------------------------------------- #
P = ROOT / "dramakit" / "prompts" / "templates.py"
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

marker = "# --------------------------------------------------------------------------- #\n# STORYBOARD — shot list per scene"
assert marker in text, "没找到分镜那节"

new_templates = '''# --------------------------------------------------------------------------- #
# SCREENPLAY — the scenes of an episode, and then each scene whole
#
# Two calls, and the scene is written in one: the lines and the shots
# that cover them.  The writer and the director were two people in two
# rooms, and what the second one did not understand was lost on the way.
# --------------------------------------------------------------------------- #
SCRIPT_PLAN_SYSTEM = """你是短剧编剧，把小说的一集拆成若干场戏。

每一场戏要有：地点、时间、这一场发生了什么、以及**这一场看得见的几下**（拍）。
拍就是小说里写得出来的画面：谁在哪儿、在做什么、环境是什么样。
**小说的描写不要丢**——它们不是台词，是这一集要拍出来的东西。

只输出JSON。"""

SCRIPT_PLAN_USER = """把下面这一集原文拆成若干场戏。题材：{{genre}}。

- 拆成 {{min_scenes}}~{{max_scenes}} 场（同一时空为一场）
- 每一场给出：
  - location：只能用下面这些已有的场景（要再细分就在后面加"·子区域"，
    比如"五星级酒店婚礼宴会厅·主舞台"，但前半截必须一字不差）：
    {{location_names}}
    场景没有对应的参考图，这一集的镜头就生成不出来
  - time_of_day：日/夜/晨/昏
  - summary：一句话，这一场发生了什么
  - mood：氛围（用于配乐：紧张/悲伤/欢快/恢弘/浪漫/平静等）
  - beats：这一场**看得见**的几下，按顺序排
    - action：画面里发生的事（写给镜头看）
    - 至少一拍是不说话的（环境、物件、身体反应、对方的沉默）
    - 一场戏三到八拍

- 只使用这些已确定角色（不要凭空新增主要角色）：{{character_names}}

原文：
"""
{{text}}
"""

{{screenwriter_rules}}

输出JSON：
{"scenes":[{"location":"","time_of_day":"日","summary":"","mood":"",
 "beats":[{"action":""}]}]}"""


SCRIPT_SCENE_SYSTEM = """你是短剧的编剧兼导演。

给你一场戏的原文和这场戏要拍的几下，你交出这一场的**台词**和**镜头**——
台词和镜头是一次写出来的，因为镜头就是为这些台词设计的。

只输出JSON。"""

SCRIPT_SCENE_USER = """这是第 {{ep_index}} 集（全书共 {{ep_total}} 集）的一场戏。

地点：{{location}} / {{time_of_day}} / 氛围 {{mood}}
这一场发生了什么：{{summary}}
这一场要拍的几下（**拍要拍到，镜头要拍的是它们**）：
{{beats_text}}

这一集的全部原文（这场戏的台词在里面）：
"""
{{text}}
"""

出镜角色及锁定锚点（外貌/发型/服装一个字都不要改写）：
{{character_anchors}}

{{screenwriter_rules}}

## 台词

- 一场戏的台词写在 lines 里：kind(dialogue/narration/monologue/caption)、
  speaker、text、emotion
- **不要写成问答流水**：每一场至少有一处不是"问—答"——打断、沉默、反问、
  岔开、撒谎、抢白，或者用动作代替回答
- 每个人说话要像他自己：此刻他想要什么、怕什么、瞒什么
- 一句不超过 12 个字；括号里的表演提示写进 emotion，不要写进 text
  ——text 会被配音念出来，也会变成字幕
- 旁白只留交代必要的时空/身份信息，而且不能重复画面已经说出来的

## 镜头

- shots 里是这一场的镜头，每一镜：shot_type(特写/近景/中景/全景/远景/过肩/主观/空镜)、
  angle(正面/斜侧/正侧/后斜侧/背面)、height(地平/低/平视/高/顶视)、
  lens(广/标准/长)、camera_move(固定/推/拉/摇/移/跟)、subject(画面主体)、
  purpose(这一镜为什么存在)、duration(秒)、action(这一镜里发生的事)、
  characters(出镜角色)、beats(这一镜拍的是第几拍)、lines(这一镜承载的台词行号)
- **一镜到底**：一个机位从头到尾，运镜可以走，但不要在段里切。
  需要换角度、要看对方的反应、要看一个物件，**另起一镜**，让它有自己的首帧。
  切是在镜头之间做的
- **说话的人不许正对镜头**：台词镜头用斜侧或正侧，只有空镜、道具特写、
  蒙太奇和极少数刻意的正面定帧可以用正面。**正面怼脸讲台词 = 业余**
- **两个角色对话必须正反打**：A 说完切 B，B 说完切 A（这是两镜）。
  切到对方时用**过肩**——镜头在说话人的肩后，看着对方
- **对方听完之后的反应要单独给一镜**：怔住、眼泪、攥紧手、别过脸、转身。
  这一镜**不承载台词**（台词跟着说话人的镜头走），画面给的是听的人
- **关键词要有画面**：台词里的关键名词（合同、戒指、股份、病历）要有对应的
  插入特写或空镜，别让观众只听说明书
- **蒙太奇**：时间流逝、重复劳动、往返奔走，用 3~5 个短镜头快切（每个 1~2 秒），
  每个镜头角度和景别都不一样。一场戏里最多一次
- **相邻两镜必须至少变一项**：景别、角度、主体三者不能全一样
- **不要一上来就给特写**：第一镜交代人物和环境，之后再收进去
- **动作要跟着台词走**：说"三个月"就抬三根手指，别把动作写在不属于它的镜头里
- 一个镜头承载的对白不超过 8 秒（通常 2~4 句）
- 这一场大约 {{scene_seconds}} 秒，请分成大约 {{scene_shots}} 个镜头

输出JSON：
{"lines":[{"kind":"dialogue","speaker":"","text":"","emotion":"平静"}],
 "shots":[{"shot_type":"中景","angle":"斜侧","height":"平视","lens":"标准",
 "camera_move":"固定","subject":"","purpose":"","duration":8.0,
 "action":"","characters":[""],"beats":[1],"lines":[1,2]}]}"""


'''
text = text.replace(marker, new_templates + marker, 1)
if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("模板写好了")
