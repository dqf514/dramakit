"""The plan prompt, in the screenplay's own words.

The prompt used to ask the model to think about the drama - who wants
what, what stands in the way - and the screenplay came out as a list of
things that happen to somebody.  A screenplay is three things: the
scene, a stretch of action, and what is said.  The inner voice is the
fourth, and it is a sound of its own.
"""
import pathlib

P = pathlib.Path(r"E:\dramakit\dramakit\prompts\templates.py")
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

start = text.index("SCRIPT_PLAN_SYSTEM = ")
end = text.index("SCRIPT_SCENE_SYSTEM = ")

NEW = '''SCRIPT_PLAN_SYSTEM = """你是短剧编剧，把小说的一集拆成若干场戏。

剧本是给人看的，所以每一场只有三样东西：**场景、一段动作、说出口的话**
（还有心里的话）。拍是这一段动作里看得见的几下，写给镜头看。

只输出JSON。"""

SCRIPT_PLAN_USER = """把下面这一集原文拆成若干场戏。题材：{{genre}}。

## 每一场只有三样东西

- **场景**：内/外 · 地点 · 时间。
  地点只能用下面这些已有的（要再细分就在后面加"·子区域"，
  比如"五星级酒店婚礼宴会厅·主舞台"，但前半截必须一字不差）：
  {{location_names}}
  场景没有对应的参考图，这一集的镜头就生成不出来
- **一段动作**：现在时，白描，写给人看——谁在哪儿、在做什么、环境是什么样。
  **不要写心理活动**（心理活动是后面 [VO] 的事），也不要写"她很伤心"
  这种感受，写她做了什么。
- **拍**：这一段动作里看得见的几下，按顺序排（写给镜头看）
  - 至少一拍是不说话的（环境、物件、身体反应、对方的沉默）
  - 一场戏三到八拍
- mood：氛围（用于配乐：紧张/悲伤/欢快/恢弘/浪漫/平静等）

## 不许发明

- **只拆这一集原文里真有的事**。原文没写的话，不能编出来当情节。
- 原文写"我不明白母亲那句话是什么意思"，那就让观众和她一起不明白——
  **不要把那句话演出来**。那是后面几十集才揭的底，演早了整本书就废了。
- 原文里"我想起母亲的话"这种一句带过的事，**不要扩写成一场回忆戏**。
- 人物只能知道这一集原文里他知道的事。

## 这一集要立得住

- **开头三秒观众就要知道她要什么、谁挡着她**（从她当下的处境里找）
- **结尾不能是回忆、旁白或者"她还不知道"的疑问**：要有一个落在实处的
  动作或一句话——她做了决定、她被挡在门外、有人替她把话说出口
- 私下说的心里话不算戏。**能让对方在场的话，就让对方在场**

- 只使用这些已确定角色（不要凭空新增主要角色）：{{character_names}}

原文：
\\"\\"\\"
{{text}}
\\"\\"\\"

{{screenwriter_rules}}

输出JSON：
{"scenes":[{"slug":"内 · 地点 · 晨","action":"","mood":"紧张",
 "beats":[{"action":""}]}]}"""


'''

text = text[:start] + NEW + text[end:]
if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("计划那段的模板换了")
