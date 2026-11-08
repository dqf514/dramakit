"""The H3 prompt, in the shape H3 reads.

The official shape: the three fields, a timeline with single time points,
`[Shot N]` with its own framing, the speaker ids outside the `<d>` tag,
the reference pictures' jobs spelled out, and no negative content at all
(the sampler runs at cfg 1 - a list of forbidden things only puts the
forbidden things into the picture).

The old template was a wall of Chinese prohibitions and told the model
two different things about whether a segment may be cut.
"""
import pathlib

P = pathlib.Path(r"E:\dramakit\dramakit\prompts\templates.py")
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
text = raw.replace("\r\n", "\n")

start = text.index("H3_VIDEO_USER = ")
end = text.index("H3_SCORE_SYSTEM = ")

NEW = '''H3_VIDEO_USER = """为下面这一段生成 MiniMax H3 提示词（I2VA 模式：图片是第一帧）。

## 这一段的固定条件

- **第一帧就是给定的图片**：第一帧里有什么人、什么光，第一帧里就得有什么
- 画面：{{action}}
- 机位：{{shot_type}} / {{angle}}·{{height}}·{{lens}} / 运镜 {{camera_move}}
- 焦点：{{subject}}（焦点之外的一切都虚化，大光圈 f/1.4~f/2.8）
- 出镜角色（外貌、发型、服装与给定描述完全一致）：
{{character_anchors}}
- 场景：{{location}} / {{time_of_day}}
  场景参考图是唯一标准：桌子的材质和颜色、窗户位置、座位关系都不变
  {{location_visual}}
- 画风：{{style}}；画幅：{{aspect_ratio}}（{{frame_size}}）；年代：{{era}}；
  色调：{{color_palette}}
- 情绪：{{mood}}
- 参考图的分工（每张图各管各的，不要互相污染）：
{{references}}
- 本段台词（speaker 已换成编号）：
{{dialogue}}
{{dialogue_note}}

## 这一段的时间轴（切点是定好的）

{{timeline}}
{{segment_shots}}

## 写法

- **integrated_multimodal_description** 以 `[Shot 1] ` 开头；后面的镜头用
  `At 00:0X.XXX, the camera cuts to [Shot N]` 开头（硬切，不是叠化）
- 每个 `[Shot N]` 有**自己的景别、角度和焦点**——景别在近景↔特写↔过肩↔中景
  之间换，角度也换；焦点跟着这一镜的事走（说话人的眼睛、动的那只手、
  那个物件）
- 人物看着画外的对话对象或道具，视线不落在镜头上
  （no one looks into the lens）
- **台词原样用 `<d>[zh-CN]...</d>` 包住**，说话人编号写在标签外
- 画外音（心里的声音、画外的人在说话）写明是画外音，并写明这个人嘴唇闭合
- 描述全部用英文写
- 描述末尾原样带上 constraints（不改写）：
  {{constraints}}

输出JSON：
{"integrated_multimodal_description":"","overall_soundscape":"","non_diegetic_music":""}"""


'''

text = text[:start] + NEW + text[end:]
if crlf:
    text = text.replace("\n", "\r\n")
P.write_bytes(text.encode("utf-8"))
print("H3 提示词按官方结构重写了")
