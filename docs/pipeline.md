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

编剧和导演的**专业规矩来自 skill 文件**，不是硬编码在提示词里。

技能库是 [shuohao-skills](https://github.com/eternityspring/shuohao-skills)（Apache-2.0）改编来的：

- 7 个生产阶段 skill：`novel-outline`（改编大纲）/ `novel-characters`（角色设定）/
  `novel-art`（美术设定）/ `novel-script`（写剧本）/ `novel-staging`（开场站位）/
  `novel-storyboard`（分镜）/ `character-refs`（角色参考图）
- 15 张题材卡（`genre/`）：按题材挑的那一张，上游没有

**改了什么**：上游的 skill 是给 Agent 用的工作流——跑 shell 命令、写 JSON 文件、
出 HTML 报告。这一套是 Python 流水线，直接把规矩塞进提示词里。所以**留下的���手艺**
（进提示词的规矩，和跟着手艺走的参考文档），**没留下的是工作流**
（命令、JSON 合同、报告）。

**接入方式**：
```python
# config.py
class SkillsConfig(BaseModel):
    analyze: list[str] = ["novel-outline", "novel-characters", "novel-art"]
    script: list[str] = ["novel-script"]
    storyboard: list[str] = ["novel-storyboard", "novel-staging"]
    promptgen: list[str] = ["novel-storyboard"]
    refs: dict[str, dict[str, list[str]]] = {
        # 每个阶段额外点名要读哪几篇参考文档
        "script": {"novel-script": ["script-pass.md"]},
        ...
    }
```

**运行时**：`loader.for_stage(ctx, "script")` → 读 `skills/novel-script/SKILL.md`
+ 点名的参考文档 → 注入提示词。题材卡由 `loader.genre_rules(ctx, stage)` 自动挑一张。

**加新 skill**：在 `skills/` 下建一个文件夹，放 `SKILL.md`，然后在 `config.py` 里引用。

## 上游的「段」和我们的「镜头」

上游把镜头分三层：**段**（一次生成调用，9–15 秒）→ **分镜**（段内 2–5 秒的剪切）→
**分镜图**（每切一张，钉在各自切点）。我们把前两层压成了一层：我们的一个「镜头」
就是一次 H3 生成，段内的切由 `_cut_marks` 给出（`comfyui.segment_cuts: true`）。

**这带来的差别是渲染成本**：上游一集约 10 次生成，我们一集约 30 次（按
`shot_duration_range: [5.0, 15.0]`，一集 150 秒被切成 30 个 5 秒的镜头）。
上游的段是 9–15 秒，一集约 10–16 段，**渲染次数差三倍**。

这是下一步该做的事（把镜头拉长到 9–15 秒，一集约 13 段），不是现在改的：
段内的切点数、节拍到镜头的认领、H3 的 `[Shot k]` 对账都要跟着动，
而这三样现在只在纸上，没有跑过整集。

上游库的更新方式：

```bash
git clone https://github.com/eternityspring/shuohao-skills.git rounds/vendor/shuohao-skills
# 手艺在 references/ 里，脚本在 scripts/ 里，SKILL.md 是我们改写过的
```

上游的 skill 是给 Agent 用的工作流（跑命令、写 JSON、出报告），我们的是
Python 流水线。**留下的是手艺**（进提示词的规矩，和跟着手艺走的参考文档），
**没留下的是工作流**（命令、JSON 合同、报告）。上游的 `scripts/*.mjs` 校验器
原样留着——它们校验的是上游自己的 JSON 合同，不是我们的项目文件，
但它们是那些质量门写出来的原因，值得对照着看。

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
