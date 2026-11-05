"""The console tells the truth about what the pipeline does.

Two things were wrong in it.  The five steps put the casting in front
of the writing, which is not what the run does any more - the casting
runs beside the writing, and the step says so.  And the voice step
said "TTS line by line", which stopped being true when the video model
started speaking the lines itself: what is made is one sample of each
character's voice, and that sample is the timbre the video model uses.
"""
import pathlib

PATH = pathlib.Path(r"E:\dramakit\dramakit\web\static\index.html")
text = PATH.read_text(encoding="utf-8")

old_stages = 'const STAGES=["ingest","analyze","character","segment","script","storyboard","promptgen","voice","visual","subtitle","music","precheck","compose","qc"];'
new_stages = 'const STAGES=["ingest","analyze","cover","character","segment","script","storyboard","promptgen","voice","visual","subtitle","music","precheck","compose","qc"];'
assert old_stages in text, "找不到 STAGES"
text = text.replace(old_stages, new_stages, 1)

old_zh = 'const STAGE_ZH={ingest:"导入",analyze:"分析",character:"定妆",segment:"分集",script:"剧本",storyboard:"分镜",promptgen:"提示词",voice:"配音",visual:"画面",subtitle:"字幕",music:"配乐",precheck:"预检",compose:"合成",qc:"质检"};'
new_zh = 'const STAGE_ZH={ingest:"导入",analyze:"分析",cover:"封面",character:"定妆",segment:"分集",script:"剧本",storyboard:"分镜",promptgen:"提示词",voice:"音色",visual:"画面",subtitle:"字幕",music:"配乐",precheck:"预检",compose:"合成",qc:"质检"};'
assert old_zh in text, "找不到 STAGE_ZH"
text = text.replace(old_zh, new_zh, 1)

old_steps = '''const STEPS=[
  {id:"prep",  zh:"准备", stages:["ingest","analyze","character","segment"], hint:"导入·分析·定妆·分集"},
  {id:"script",zh:"剧本", stages:["script","storyboard","promptgen"],       hint:"剧本·分镜·提示词"},
  {id:"voice", zh:"配音", stages:["voice"],                                 hint:"逐句 TTS"},
  {id:"visual",zh:"画面", stages:["visual"],                                hint:"ComfyUI 出图/视频"},
  {id:"final", zh:"成片", stages:["subtitle","music","precheck","compose","qc"], hint:"字幕·配乐·预检·合成·质检"},
];'''
new_steps = '''const STEPS=[
  {id:"prep",  zh:"准备", stages:["ingest","analyze","cover"],                     hint:"导入·分析·封面"},
  {id:"cast",  zh:"定妆", stages:["character","voice"],                          hint:"参考图·音色样本（和文字活并排跑）"},
  {id:"script",zh:"剧本", stages:["segment","script","storyboard","promptgen"],    hint:"分集·剧本·分镜·提示词"},
  {id:"visual",zh:"画面", stages:["visual"],                                      hint:"ComfyUI 出图/视频"},
  {id:"final", zh:"成片", stages:["lipsync","subtitle","music","precheck","compose","qc"], hint:"字幕·配乐·预检·合成·质检"},
];'''
assert old_steps in text, "找不到 STEPS"
text = text.replace(old_steps, new_steps, 1)

old_hint = 'const STAGE_HINT={ingest:"清洗 · 分章",analyze:"角色 · 世界观",character:"锚点 · 三视图",segment:"按钩子切集",script:"台词 · 旁白",storyboard:"场次 · 镜头",promptgen:"中英提示词",visual:"ComfyUI 出图/视频",voice:"逐句 TTS",subtitle:"跟着配音走",music:"情绪匹配 BGM",precheck:"成片前校验",compose:"ffmpeg 成片",qc:"成片质检"};'
new_hint = 'const STAGE_HINT={ingest:"清洗 · 分章",analyze:"角色 · 世界观",cover:"剧名 · 主视觉",character:"锚点 · 四视图 · 音色样本",segment:"按钩子切集",script:"台词 · 旁白",storyboard:"场次 · 镜头",promptgen:"中英提示词",visual:"ComfyUI 出图/视频",voice:"每个角色一段，给 H3 当音色参考（画面自带声音，不逐句配音）",subtitle:"跟着画面走",music:"情绪匹配 BGM",precheck:"成片前校验",compose:"ffmpeg 成片",qc:"成片质检"};'
assert old_hint in text, "找不到 STAGE_HINT"
text = text.replace(old_hint, new_hint, 1)

PATH.write_text(text, encoding="utf-8")
print("控制台改好了")
