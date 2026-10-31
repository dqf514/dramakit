# 短剧流水线

**小说进 → 成片出**

## 流程

1. **编剧**（analyze + script）：读小说，立 logline、抽出角色/场景/道具，写本子
2. **导演**（storyboard）：拆片段、写站位/景别/运镜/段内切点
3. **提示词**（promptgen）：出图提示词 + H3 提示词
4. **资产**（character）：角色定妆（人脸图 + 三视图）、场景空镜
5. **出片**（visual）：出图与出视频并行，交接帧让切点不跳
6. **后期**（compose）：调色统一、配乐垫底、混音、烧字幕、合规标注、导出成片
7. **验收**（qc + review + drift）：机器体检 + 多模态看片 + 人脸漂移检查

## Skill 系统

编剧和导演的**专业规矩来自 skill 文件**，不是硬编码在提示词里：

- 11 个短剧 skill（novel-analyze / write / storyboard / video-prompts / image-prompts / assets / produce / review / edit / develop / short-drama）
- 26 个编剧理论 skill（契诃夫构作 / 小津风格 / 继承之战 / 人物冲突 / 故事结构 / ...）

**接入方式**：
```python
# config.py
class SkillsConfig(BaseModel):
    analyze: list[str] = ["short-drama-novel-analyze"]
    script: list[str] = ["short-drama-write"]
    storyboard: list[str] = ["short-drama-storyboard"]
    promptgen: list[str] = ["short-drama-video-prompts", "short-drama-image-prompts"]
    by_genre: dict[str, list[str]] = {
        "复仇": ["screenwriting-theory/sw-character-conflict"],
        "甜宠": ["screenwriting-theory/ozu-screenplay-style"],
        ...
    }
```

**运行时**：`loader.for_stage(ctx, "script")` → 读 `skills/short-drama-write/SKILL.md` + 该题材的理论 skill → 注入提示词。

**加新 skill**：在 `skills/` 下建一个文件夹，放 `SKILL.md`，然后在 `config.py` 里引用。

## 资产库

| 层 | 内容 |
|---|---|
| 角色 | 正面全身 + 人脸满屏 + 侧面 + 四分之三 + 背面（横向排列成一张三视图） |
| 场景 | 空镜（固定材质/色调/窗位） |
| 道具 | 贯穿全剧的道具（戒指/合同/病历） |

**每张参考图 = 一张图**：H3 参考图槽位有限（9 个），三视图必须合在一张。

## 参考图顺序（编号 = 上传顺序 = 提示词 `<Picture N>`）

```
Picture 1   首帧（构图/站位/服装/光线）
Picture 2   上一镜尾帧（交接帧，切点不跳）
Picture 3+  每人两张：人脸图 + 三视图
最后一张   场景图（只取环境光线）
```

## 三道花钱前的闸门

1. 参考图不齐 → 不抽卡
2. 台词标签不够 → 不抽卡
3. 只有静帧没有视频 → precheck 拦下合成
