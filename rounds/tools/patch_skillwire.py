"""Wire the two skills into the three stages that need them."""
from pathlib import Path

T = Path(r"E:\\dramakit\\dramakit\\prompts\\templates.py")
s = T.read_text(encoding="utf-8")

# 1) the analysis is the screenwriter's reading of the novel
old = """ANALYZE_SYSTEM = \"\"\"你是资深短剧编剧与美术指导。阅读小说/剧本，抽取用于AI短剧制作的设定。
只输出JSON，不要解释。\"\"\""""
new = """ANALYZE_SYSTEM = \"\"\"你是有商业短剧经验的编剧，同时负责美术设定。
阅读小说，先站到编剧的位置上：这一集讲什么、谁想要什么、谁挡着、
每一场戏在哪里发生、观众最后带着什么问题走。然后把这份读法落成
可以交给导演和美术的设定。

只输出JSON，不要解释。\"\"\""""
assert old in s, "ANALYZE_SYSTEM 锚点没找到"
s = s.replace(old, new, 1)

old = """- art_direction: style 画风, era 年代, color_palette 色调

文本："""
new = """- art_direction: style 画风, era 年代, color_palette 色调
- props: 贯穿全场的关键道具（最多{{max_props}}个，没有就空数组）
  - name 名称; description 它在剧情里是什么; visual_prompt 英文外观描述
  - **同样必须唯一**：一种材质、一个颜色、一个形制。戒指、合同、病历、
    酒杯这种会反复出现的东西，都要单独建一份资产

**读小说的规矩（编剧的职业习惯）**：
- 先想清楚"这一集的信息增量"是什么：观众看完这一集，比看之前多知道了什么
- 人物要写清楚"想要什么"和"缺什么"：台词的劲道是从这里来的
- 场景要写清楚"这是哪儿、谁在这儿、这里有什么固定的东西"
- 贯穿全场的道具要单独列出来——它们是连续性的锚点
- 美术设定是为了一致性服务的：一种材质、一个色调，写死位置

文本："""
assert old in s, "ANALYZE_USER 锚点没找到"
s = s.replace(old, new, 1)

old = """  "locations": [{"name":"","description":"","visual_prompt":""}],
  "art_direction": {"style":"","era":"","color_palette":""}
}\"\"\""""
new = """  "locations": [{"name":"","description":"","visual_prompt":""}],
  "props": [{"name":"","description":"","visual_prompt":""}],
  "art_direction": {"style":"","era":"","color_palette":""}
}\"\"\""""
assert old in s, "ANALYZE JSON 锚点没找到"
s = s.replace(old, new, 1)

# 2) the script is the screenwriter's screenplay
old = """SCRIPT_SYSTEM = \"\"\"你是短剧编剧，把小说改编成可拍摄的短剧剧本。
只输出JSON。\"\"\""""
new = """SCRIPT_SYSTEM = \"\"\"你是有商业短剧经验的编剧，把小说改编成可拍摄的短剧剧本。
你交付的不是小说梗概，是一份可以交给导演的剧本：每一场都有地点、时间、
这一场的戏、这一场里谁跟谁说什么、以及这场结束时事情变成了什么样。
只输出JSON。\"\"\""""
assert old in s, "SCRIPT_SYSTEM 锚点没找到"
s = s.replace(old, new, 1)

T.write_text(s, encoding="utf-8")
print("templates.py: 编剧身份接上了")
