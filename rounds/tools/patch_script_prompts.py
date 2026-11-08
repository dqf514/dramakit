"""The prompts, in MiniMax's own structure.

Task / Context / Source / Constraints / Output format - and a constraint
that says why it is there.  The old prompts were a wall of "do not"
bullets, and a wall of prohibitions is exactly what a model handles
worst: every one of them puts the forbidden thing into the prompt.

    python rounds/tools/patch_script_prompts.py
"""
import pathlib

P = pathlib.Path(r"E:\dramakit\dramakit\prompts\templates.py")
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

# ---------------------------------------------------------------- the plan
start = text.index("SCRIPT_PLAN_SYSTEM = ")
end = text.index("SCRIPT_SCENE_SYSTEM = ")
PLAN = '''SCRIPT_PLAN_SYSTEM = """你是短剧编剧，把小说的一集拆成若干场戏。

剧本是给人看的，所以每一场只有三样东西：**场景、一段动作、说出口的话**
（还有心里的话）。拍是这一段动作里看得见的几下，写给镜头看。

只输出JSON。"""

SCRIPT_PLAN_USER = """任务：
把下面这一集小说原文拆成若干场戏。

背景：
题材：{{genre}}。

来源：
这一集原文：
\\"\\"\\"
{{text}}
\\"\\"\\"
可以用的地点（地点只能用这些，前半截一字不差；要再细分就在后面加"·子区域"）：
{{location_names}}
可以用的角色（不要凭空新增主要角色）：
{{character_names}}

约束：
- 每一场只有三样东西：**场景、一段动作、拍**。
  - **场景**：内/外 · 地点 · 时间。场景没有对应的参考图，这一集的镜头就
    生成不出来，所以地点只能从上面那份里挑。
  - **一段动作**：现在时、白描，写给人看——谁在哪儿、在做什么、环境是什么
    样子。心理活动不写进动作（那是心里的话的事），感受也不写："她很伤心"
    不写，写她做了什么。
  - **拍**：这一段动作里看得见的几下（写给镜头看），按顺序排，三到八拍，
    其中至少一拍是不说话的（环境、物件、身体反应、对方的沉默）。
- **只拆原文里真有的事**。原文没写的话不能编出来当情节；原文里"我想起
  母亲的话"这种一句带过的事，不要扩写成一场回忆戏；后面几十集才揭的底
  （原文写着"我不明白那句话是什么意思"），不要在这一集演出来——演早了
  整本书就废了。人物只能知道这一集原文里他知道的事。
- 这一集要立得住：开头三秒观众就知道她要什么、谁挡着她；结尾要有一个
  落在实处的动作或一句话，不能停在回忆、旁白或者"她还不知道"的疑问上。
  私下说的心里话不算戏——能让对方在场的话，就让对方在场。

输出格式：
{"scenes":[{"slug":"内 · 地点 · 晨","action":"","mood":"紧张",
 "beats":[{"action":""}]}]}"""


'''
text = text[:start] + PLAN + text[end:]

# ---------------------------------------------------------------- the scene
start = text.index("SCRIPT_SCENE_USER = ")
end = text.index("# --------------------------------------------------------------------------- #\n# STORYBOARD")
SCENE = '''SCRIPT_SCENE_USER = """任务：
把这一集原文写成**这一场**的剧本——这一场的位置和动作已经定好，你要写的是
这一场的动作、说出口的话、心里的话，和这一场的镜头。

背景：
题材：{{genre}}。全书第 {{ep_index}} 集（共 {{ep_total}} 集）。
这一场：{{location}} / {{time_of_day}} / {{mood}}
这一场定好的动作：{{action}}
这一场要拍到的那几下：
{{beats_text}}

来源：
这一集原文（这场戏的台词在里面）：
\\"\\"\\"
{{text}}
\\"\\"\\"
出镜角色的外貌（一个字都不要改写）：
{{character_anchors}}

{{screenwriter_rules}}

约束：
- **只演原文里真有的事**。原文没写的对话不能编出来当情节——后面几十集才
  揭的底，演早了整本书就废了；人物只能知道这一集原文里他知道的事。
- 这一场写成三样东西：**一段动作、说出口的话、心里的话**。
  - **动作**：现在时、白描，只写看得见、能演的。心理活动不写进动作。
  - **对白**（kind=dialogue）：角色（提示）：台词，一句不超过 12 个字。
  - **心里的话**（kind=voice_over）：这个人**没有开口**，声音只在他自己心里
    响——观众听得见，别的角色听不见。这是心理活动的标准写法；能用一个
    动作或一句台词说清楚的，就不要用它。一场戏最多两句。
  - **画外对白**（kind=off_screen）：这个人**在画面外**说话（门那边、楼下、
    远处），人不出画。
  - **旁白**（kind=narration）：只交代必要的时空和身份，不重复画面已经
    说出来的。
- 台词之间要有来回，不是各说各的；要有一句扎人的话——不是最狠的那句，
  是最准的那句，一句话就把这场的劲顶起来；每个人说话像他自己，此刻他
  想要什么、怕什么、瞒什么。括号里的表演提示写进 emotion，不要写进
  text——text 会被配音念出来，也会变成字幕。
- **这一场是一组镜头，不是一串人脸**：第一镜给全景或远景交代场子；对话
  排成正反打（说话的人 → 切对方的过肩，镜头在说话人肩后）；特写最多三个，
  只给最要紧的那句和最要紧的那个反应；至少一镜不是人（那个物件或身体
  细节，subject 写那个东西）；至少一镜是对方的反应；角度不要都选斜侧；
  相邻两镜的景别不能一样。**一镜到底**：一个机位从头到尾，换角度、要看
  对方的反应、要看一个物件，就另起一镜，让它有自己的首帧。
- 每一镜写清：景别、角度、机位高度、焦段、运镜、主体、这一镜为什么
  存在、几秒、画面里发生的事、出镜角色、拍的是第几拍、承载哪几句台词。
  **画面里发生的事写给镜头看，不写时间轴**（"0-2秒…2-4秒…"这种不写）——
  一镜到底的机器照着这个生成，中途一切都是这个机位。
- 这一场大约 {{scene_seconds}} 秒，约 {{scene_shots}} 个镜头，平均
  {{scene_avg}} 秒一个；时长按这一镜的事来定，不要每一镜都顶到上限。

输出格式：
{"lines":[{"kind":"dialogue","speaker":"","text":"","emotion":"平静"}],
 "shots":[{"shot_type":"中景","angle":"斜侧","height":"平视","lens":"标准",
 "camera_move":"固定","subject":"","purpose":"","duration":8.0,
 "action":"","characters":[""],"beats":[1],"lines":[1,2]}]}"""


'''
text = text[:start] + SCENE + text[end:]

if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("两段剧本提示词按 MiniMax 的结构重写了")
