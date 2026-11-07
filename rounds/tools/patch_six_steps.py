"""The steps the way a person thinks about them, and the skills that follow.

Six steps, not five: the import and the reading of the book are two
different things to wait for, and the shots are no longer a step of
their own - they are written with the script, in the same call, so the
coverage is designed for the words.

And the director's craft follows the script now: the rules about the
coverage, the axis and the frame go in with the writer, because the
shots are written there.
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
# 1. the six steps
# --------------------------------------------------------------------------- #
edit("dramakit/web/static/index.html",
     """const STEPS=[
  {id:"prep",  zh:"准备", stages:["ingest","analyze","cover"],                     hint:"导入·分析·封面"},
  {id:"cast",  zh:"定妆", stages:["character","voice"],                          hint:"参考图·音色样本（和文字活并排跑）"},
  {id:"script",zh:"剧本", stages:["segment","script","storyboard","promptgen"],    hint:"分集·剧本·分镜·提示词"},
  {id:"visual",zh:"画面", stages:["visual"],                                      hint:"ComfyUI 出图/视频"},
  {id:"final", zh:"成片", stages:["lipsync","subtitle","music","precheck","compose","qc"], hint:"字幕·配乐·预检·合成·质检"},
];""",
     """const STEPS=[
  {id:"import",zh:"小说导入", stages:["ingest"],                                    hint:"清洗·分章"},
  {id:"read",  zh:"全文分析", stages:["analyze"],                                   hint:"角色·世界观·类型"},
  {id:"adapt", zh:"改成剧集", stages:["segment","script","storyboard"],            hint:"切集·剧本和分镜一起写"},
  {id:"cast",  zh:"角色出图", stages:["character","voice","cover"],                hint:"参考图·音色样本·封面"},
  {id:"make",  zh:"分镜制作", stages:["promptgen","visual"],                       hint:"提示词·出图出视频"},
  {id:"post",  zh:"后期",     stages:["subtitle","music","precheck","compose","qc"], hint:"字幕·配乐·预检·合成·质检"},
];""",
     "the six steps")

edit("dramakit/web/static/index.html",
     """const STAGE_HINT={ingest:"清洗 · 分章",analyze:"角色 · 世界观",cover:"剧名 · 主视觉",character:"锚点 · 四视图 · 音色样本",segment:"按钩子切集",script:"台词 · 旁白",storyboard:"场次 · 镜头",promptgen:"中英提示词",visual:"ComfyUI 出图/视频",voice:"每个角色一段，给 H3 当音色参考（画面自带声音，不逐句配音）",subtitle:"跟着画面走",music:"情绪匹配 BGM",precheck:"成片前校验",compose:"ffmpeg 成片",qc:"成片质检"};""",
     """const STAGE_HINT={ingest:"清洗 · 分章",analyze:"角色 · 世界观",cover:"剧名 · 主视觉",character:"锚点 · 四视图 · 音色样本",segment:"按钩子切集",script:"台词和镜头一起写",storyboard:"补上没写到的镜头",promptgen:"中英提示词",visual:"ComfyUI 出图/视频",voice:"每个角色一段，给 H3 当音色参考（画面自带声音，不逐句配音）",subtitle:"跟着画面走",music:"情绪匹配 BGM",precheck:"成片前校验",compose:"ffmpeg 成片",qc:"成片质检"};""",
     "the stage hints")

# --------------------------------------------------------------------------- #
# 2. the director's craft follows the script
# --------------------------------------------------------------------------- #
edit("config/default.yaml",
     """  script:
    - short-drama-write
    - short-drama-ai-film
  storyboard:
    - short-drama-storyboard
    - short-drama-ai-film""",
     """  script:
    - short-drama-write
    - short-drama-storyboard
    - short-drama-ai-film
  storyboard:
    - short-drama-storyboard
    - short-drama-ai-film""",
     "the script stage's skills")

edit("config/default.yaml",
     """    script:
      short-drama-develop:
        - adaptation-craft.md
      short-drama-ai-film:
        - beats.md""",
     """    script:
      short-drama-develop:
        - adaptation-craft.md
      short-drama-ai-film:
        - beats.md
        - segments.md
      short-drama-storyboard:
        - production-shot-grammar.md
        - blocking-playbooks.md""",
     "the script stage's references")

# the code's defaults say the same thing
edit("dramakit/config.py",
     """    script: list[str] = ["short-drama-write", "short-drama-ai-film"]""",
     """    script: list[str] = ["short-drama-write", "short-drama-storyboard",
                          "short-drama-ai-film"]""",
     "the code's script skills")

edit("dramakit/config.py",
     """        "script": {
            "short-drama-develop": ["adaptation-craft.md"],
            "short-drama-ai-film": ["beats.md"],
        },""",
     """        "script": {
            "short-drama-develop": ["adaptation-craft.md"],
            "short-drama-ai-film": ["beats.md", "segments.md"],
            "short-drama-storyboard": ["production-shot-grammar.md",
                                       "blocking-playbooks.md"],
        },""",
     "the code's script references")

print("六步和技能都改好了")
