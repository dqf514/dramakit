# DramaKit · 短剧工厂

**从一部小说，到一部多集竖屏短剧。** 导入小说/剧本，自动分集，逐集生成
剧本 → 分镜 → 出图提示词 → 画面（ComfyUI）→ 配音 → 字幕 → 配乐 → 合成成片。

面向 **红果短剧 / 抖音短剧** 的竖屏 9:16、每集 60~120 秒形态。个人自用、可持续迭代。

每一个 AI 能力都是**可插拔**的：云端 API 与本地部署随时切换。

**AI 原生**：一句 `dj serve` 打开本地控制台——参数一键生成、项目/素材自动打标签分类、
自然语言驱动检索与动作。你只管在输入框里提要求，剩下的交给 AI（见 [第四节](#四ai-原生控制台推荐入口)）。

```
小说.txt
   │
   ▼  ingest      清洗 + 章节识别
   ▼  analyze     LLM 抽角色/世界观/画风        ← LLM
   ▼  character   角色定妆(锚点 + 三视图参考图)  ← ComfyUI
   ▼  segment     分集 + 每集标题/钩子/前情      ← LLM
   ▼  script      改编成场景 + 台词(对白/旁白)   ← LLM
   ▼  storyboard  每场戏的分镜表(景别/运镜/时长) ← LLM
   ▼  promptgen   每个镜头的出图/出视频提示词     ← LLM
   ▼  visual      调 ComfyUI 出图 + 图生视频      ← 你的视频服务器
   │              (角色参考图注入 / 首尾帧驱动)
   ▼  voice       逐句配音(多角色音色)           ← TTS
   ▼  subtitle    时间轴对齐的 SRT + ASS 字幕
   ▼  music       按情绪生成/匹配 BGM            ← 配乐
   ▼  compose     ffmpeg 合成竖屏成片(硬字幕)     ← 本地 ffmpeg
   │
   ▼  episodes/ep_001.mp4, ep_002.mp4 ...
```

---

## 一、能力矩阵（云端 / 本地任选）

| 环节 | 云端 API | 本地部署 | 免费默认 |
|------|----------|----------|----------|
| LLM 剧本/分镜 | DeepSeek / 通义千问 / Kimi / OpenAI | Ollama / LM Studio / vLLM | Ollama |
| 配音 TTS | MiniMax / OpenAI-TTS | CosyVoice（可克隆音色） | **Edge-TTS** |
| 画面/视频 | 任意 REST 出图服务 | **ComfyUI**（SDXL + AnimateDiff） | ComfyUI |
| 配乐 BGM | Suno API | MusicGen | 本地曲库 |
| 合成 | — | ffmpeg | ffmpeg |

全部通过 `config/default.yaml` 切换，代码零改动。

---

## 二、安装

```bash
cd dramakit
python -m venv venv
venv\Scripts\activate        # Windows；Linux: source venv/bin/activate
pip install -e .             # 或 pip install -r requirements.txt
```

依赖：**Python 3.10+**、**ffmpeg/ffprobe**（必须在 PATH）。
可选：`pip install -e ".[docx]"`（读 .docx）、`".[musicgen]"`（本地生成配乐）。

自检环境（会测 ffmpeg / LLM / TTS / ComfyUI）：
```bash
dj doctor
```

---

## 三、快速开始

```bash
# 1) 建项目并导入小说
dj new 我的短剧 --source D:\novels\战神归来.txt

# 2) 跑完整流水线（默认连本地 Ollama + Edge-TTS + 本地 ComfyUI）
dj run projects/我的短剧

# 3) 看进度
dj status projects/我的短剧
```

成片在 `projects/我的短剧/episodes/ep_001.mp4` …

**只跑一部分 / 重跑某几步**（改完配置或换了模型很有用）：
```bash
# 只到分镜就停（先看剧本质量，再决定要不要出图）
dj run projects/我的短剧 --stop-after storyboard

# 只重跑配音+字幕+合成
dj run projects/我的短剧 --stages voice,subtitle,compose

# 只处理第 1~3 集
dj run projects/我的短剧 --episodes 1-3
```

流水线**可断点续跑**：已完成的镜头/台词/集数会跳过，崩了直接重跑即可。

---

## 四、AI 原生控制台（推荐入口）

不想碰配置文件、不想记命令？**一句话：`dj serve`，然后在浏览器里用自然语言指挥。**

```bash
dj serve                      # 打开 http://127.0.0.1:8756
dj serve --port 9000          # 换端口
dj serve --no-browser         # 不自动开浏览器（远程/无头）
```

控制台是**零依赖**的（Python 标准库 `http.server` + 单页 HTML，无需前端构建）。
左侧图标栏把工作分成七块，彼此联动：**工作台 / 分镜台 / 角色库 / 流水线 / 资产 / 设置 / 环境**。

### 4.1 一键配置（AI 帮你把参数全填好）

点「一键配置」→ AI 自动：
1. **探测环境**：本地/局域网的 LLM 端点（Ollama:11434、LM Studio:1234）与已加载模型、
   ComfyUI（GPU/显存、可用 checkpoint、工作流校验）、ffmpeg、Edge 音色、本地曲库。
2. **按你的意图生成完整配置**：选题材预设 + 勾选项 + 一句大白话要求，AI 据此写出
   `llm/comfyui/tts/music/segment/storyboard/compose` 全套参数——**模型名和 checkpoint
   只从真实探测到的列表里选**，连不上的 Provider 自动禁用。
3. **回写** `config/default.yaml`（可先 `--dry-run` 预览不落盘）。

人工参与被压到最少，且**额外要求有模板**：
- **题材预设**（6 个）：都市甜宠 / 战神归来 / 古装宅斗 / 玄幻修仙 / 悬疑推理 / 重生复仇。
- **勾选项 chips**：画风、节奏、受众、单集时长、画面比例、字幕、配音、配乐……点一下就改。
- **意图示例**：给 4 条现成话术，照着改成你的需求即可。

命令行等价：
```bash
dj setup "都市甜宠，节奏快，每集90秒，本地Ollama出剧本，ComfyUI在192.168.1.50" \
   --preset urban_sweet --chips fast_pace,vsub_9x16 --dry-run
dj setup --list-templates        # 看所有预设/勾选项/示例
```

### 4.2 项目管理（所有内容自动分类打标签）

导入小说、跑完各阶段后，**项目里的每一个节点/素材**（集、场景、镜头、台词、图片、
视频、音频、字幕、BGM、封面）都会进 SQLite 资产目录 `catalog.db`，并由 AI 自动打上
**标签 + 分类 + 摘要**。侧栏按项目/标签浏览，项目详情里以「集 → 场 → 镜」树展开，
图片/视频/音频直接内嵌预览。

AI 打标签（模型清单里勾了「标签/摘要」的模型干这活，省钱省时）：
```bash
dj tag projects/我的短剧            # 全项目补标签
dj tag projects/我的短剧 --no-ai    # 只用规则，不调模型
```

### 4.3 AI 检索（自然语言找素材）

输入「找夜景里女主哭的镜头」「战神归来第2集的BGM」，AI 把大白话展开成
`{关键词, 标签, 分类, 素材类型}` 再查目录，返回卡片式结果，可直接定位/预览。
```bash
dj search "夜景 女主 哭" --project projects/我的短剧 --limit 20
```

### 4.4 自然语言驱动动作（AI 解析 → 你确认 → 执行）

顶部常驻命令框，说人话即可，例如：
- 「跑完整个项目」「只重出第3集第5个镜头的图」「画风改成水墨国风」
- 「导出第1集」「重建索引」

AI 把指令解析成**白名单动作**（`run_pipeline / regenerate_shot / set_art_style /
search / reindex / export`），**危险或写操作先弹确认卡**再执行，绝不自作主张。
```bash
dj ai "把画风改成赛博朋克，然后重出第1集" --project projects/我的短剧 --yes
```

### 4.5 多模型分工（模型清单）

不再固定「主脑 / 小脑」。控制台里维护一份**模型清单**，谁干什么由你勾选：

- **想加几个加几个**：Ollama / LM Studio 本地模型，或 DeepSeek、通义、Kimi、OpenAI、
  智谱、任意 OpenAI 兼容端点；每个模型独立配置地址、Key、模型名、温度、max_tokens、
  超时、是否走代理。
- **优先级 = 列表顺序**：用 ↑ ↓ 调换；同一个任务被多个模型勾选时，用最上面的那个。
- **任务分工**：小说分析 / 智能分集 / 剧本 / 分镜 / 画面提示词 / 一键配置 / 智能动作 /
  语义检索 / 标签摘要——给每个模型勾选它负责的任务，随时互换、随时改派。
- **默认模型**：所有没被勾选的任务由它兜底；同时自动同步到 `llm.*`，旧配置与 CLI 无缝兼容。
- 交互式调用**快速失败**（`ai.main_timeout`，默认 90s，不重试），端点挂了也秒回退，
  不会卡住界面。所有 AI 能力**失败即优雅降级**，不影响你手动跑流水线。

相关配置见 `config/default.yaml` 的 `models:` 段。清单为空时自动回退到旧的
`llm` / `ai.light_*` 单模型逻辑。

### 4.6 设置页（模型清单可视化配置）

「一键配置」是 AI 帮你填；想自己直接改，切到控制台的 **「设置」** 标签页：

- **模型清单**：点 Provider 预设（DeepSeek / 通义 / Kimi / OpenAI / 智谱 / Ollama /
  LM Studio / 自定义）添加模型，填 `base_url / api_key / model / temperature /
  max_tokens / 超时 / use_proxy`。API Key 是密码框（页面只回显掩码），留空＝不修改，
  也可勾选清除。
- **优先级与默认**：每张卡片有 ↑ ↓ 调优先级（数字越小越优先）和「默认兜底」单选。
- **任务勾选**：每张卡片下半部是该模型负责的任务 chips，点亮即负责；都不勾＝只做兜底。
- **测试连接**：逐个模型验证，成功会**列出端点上的全部模型供点选**，失败给出原因
  （Key 不对 / 模型不存在 / 超时 / 连不上）。
- **AI 行为开关**：AI 层总开关、自动打标签、输出语言、交互超时。

保存采用**原位定点写回** `config/default.yaml`：模型块整体更新，其余内容与中文注释原样
保留（「一键配置」因是整份生成，会在写入前自动留 `.bak` 备份）。

### 4.7 制作工作区（分镜台 / 角色库 / 单镜返工）

这一版把「看片、改片、返工」搬进了控制台，不用再翻 `project.json`：

- **工作台**：封面、集数/镜头/台词统计、十二阶段进度条，以及每个阶段的一键跳转和
  按集重跑；点任意阶段直接进入流水线对应位置。
- **分镜台**：按「集 → 场 → 镜」浏览，镜头卡直接预览图片/视频（悬停播放），
  台词行显示说话人、时长与配音状态，可**就地改台词**（改完自动作废配音/字幕/合成）。
  右侧抽屉编辑单个镜头：景别、运镜、时长、动作、出场角色、中英文提示词、负向词、
  种子、首尾帧开关；并支持**只重出图 / 只重出视频 / 整个镜头返工**。
- **角色库**：每个角色一张卡片，展示锚点外貌、三视图参考图与锁定状态；可改外貌/
  服装/发型/负向词，一键「生成三视图」或「重置提示词」，重置后相关镜头会回到待生成。
- **流水线**：选集、看各阶段状态、按阶段重跑；制作参数（生成模式、分辨率、帧数、
  steps/cfg、并发、种子策略、一致性模式、转场、BGM 音量、TTS 并发、工作流路径、
  首尾帧开关）也能在「设置」页改并写回配置。
- **资产 / 环境**：全部产出按类型筛选预览；环境页汇总 ffmpeg、LLM、TTS、ComfyUI、
  曲库的连通性。

模型清单示例：

```yaml
models:
  default: m1                     # 兜底模型（未勾选的任务都给它）
  entries:                        # 顺序 = 优先级
  - id: m1
    label: 本地主力
    base_url: http://localhost:11434/v1
    model: qwen2.5:14b
    api_key: ollama
    roles: [analyze, segment, script, storyboard, promptgen, config, actions, search]
  - id: m2
    label: 打标小模型
    base_url: http://localhost:11434/v1
    model: qwen2.5:3b
    api_key: ollama
    roles: [tag]
```

---

## 五、配置（`config/default.yaml`）

这是整套工具的"控制台"，每个参数都有中文注释。最常改的几处：

```yaml
models:                                   # 模型清单（控制台「设置」页可视化编辑）
  default: m1                             # 兜底模型
  entries:                                # 顺序 = 优先级
  - id: m1
    label: 本地主力
    base_url: http://localhost:11434/v1
    model: qwen2.5:14b
    api_key: ollama
    roles: [analyze, segment, script, storyboard, promptgen, config, actions, search]
  - id: m2
    label: 打标小模型
    base_url: http://localhost:11434/v1
    model: qwen2.5:3b
    roles: [tag]

llm:                                      # 旧版单模型入口；默认模型会自动同步到这里
  base_url: https://api.deepseek.com/v1   # 换成你的 LLM
  model: deepseek-chat
  api_key: 用环境变量 DRAMAKIT_LLM_API_KEY

tts:
  provider: edge                          # 免费开箱即用
  voice_map:                              # 角色→音色
    林凡: zh-CN-YunjianNeural
    苏晚: zh-CN-XiaoyiNeural

comfyui:
  base_url: http://192.168.1.50:8188      # 你的视频服务器
  mode: image_then_video                  # 出图再图生视频

segment:
  episode_duration: 90                    # 每集约 90 秒

compose:
  width: 1080
  height: 1920                            # 竖屏
  burn_subtitles: true

ai:                                       # AI 原生层（一键配置/标签/检索）
  enabled: true
  language: zh
  main_timeout: 90.0                      # 交互调用快速失败上限，端点挂了不卡界面
  light_model: ""                         # 旧版小模型；models.entries 非空时不生效

web:                                      # dj serve 控制台
  host: 127.0.0.1
  port: 8756
  open_browser: true
```

> **远程/局域网连接必看**：每个 Provider（`llm/tts/comfyui/music`）都有 `use_proxy` 开关，
> **默认 `false`（直连）**。httpx 默认会读系统代理，连内网 ComfyUI/本地模型时会卡死——
> 保持 `false` 即可；只有确实要走代理访问云端时才设 `true`。

- 生成一份带注释的默认配置：`dj config --init`
- 查看当前生效配置：`dj config`
- 音色速查表：`config/voices.yaml`，或 `dj voices` 实时列出。
- **懒得手改？用 [`dj setup`](#41-一键配置ai-帮你把参数全填好) 让 AI 一键生成整份配置。**

**密钥走环境变量**，别写进文件：
```bash
# Windows
setx DRAMAKIT_LLM_API_KEY "sk-xxxx"
# Linux/Mac
export DRAMAKIT_LLM_API_KEY=sk-xxxx
```

---

## 六、视频服务器（ComfyUI）部署

完整步骤见 **[`deploy/comfyui-server.md`](deploy/comfyui-server.md)**，含：
- Linux/Windows 安装、PyTorch CUDA、AnimateDiff + VideoHelperSuite 自定义节点
- 模型下载（SDXL / SD1.5 / AnimateDiff 运动模型）
- systemd 开机自启、防火墙、Nginx 反代 + Basic Auth、SSH 隧道
- **如何导出你自己的工作流并对上节点ID**（关键）

一键脚本（Linux）：
```bash
bash deploy/setup_comfyui.sh
```

对接要点：在 ComfyUI 里搭好能跑通的工作流 → **Save (API Format)** 导出 JSON →
覆盖 `config/comfyui/t2i_sdxl.json` / `i2v_animatediff.json` → 把节点ID填进
`config/default.yaml` 的 `comfyui.t2i_nodes` / `i2v_nodes` → `dj doctor` 验证。

想要更强的一致性/可控性，再加两份**可选**工作流：
- **参考图出图**：t2i 工作流里加一个 `LoadImage`，把节点 ID 填到
  `comfyui.t2i_nodes.ref_image`，并把 `characters.consistency` 设为 `ref`。
- **首尾帧图生视频**：准备支持双图输入的 i2v 工作流，填 `comfyui.flf_workflow` 与
  `comfyui.i2v_nodes.last_image`，再打开 `comfyui.first_last_frame: true`。
两份都不配时，系统按原来的单图/单帧流程跑，不会报错。

---

## 七、目录结构

```
dramakit/
├── config/
│   ├── default.yaml              # 全套参数（主配置）
│   ├── voices.yaml               # 音色速查表
│   └── comfyui/                  # ComfyUI 工作流模板（换成你自己的）
│       ├── t2i_sdxl.json
│       └── i2v_animatediff.json
├── deploy/
│   ├── comfyui-server.md         # 视频服务器部署完整指南
│   └── setup_comfyui.sh          # 一键部署脚本
├── assets/music/                 # 本地 BGM 曲库（放版权音乐，按情绪命名）
├── projects/                     # 每个项目一个目录（输出）
│   ├── catalog.db                # AI 资产目录（SQLite，全项目素材的标签/分类索引）
│   └── <项目>/
│       ├── project.json          # manifest（断点续跑的状态）
│       ├── source/  audio/  images/  video/
│       ├── subs/  bgm/  covers/
│       └── episodes/ep_001.mp4   # 成片
└── dramakit/                     # 源码包
    ├── config.py  models.py  project.py  cli.py
    ├── catalog.py                # SQLite 资产目录：索引/打标签/检索
    ├── ai/                       # AI 原生层
    │   ├── brain.py              #   按任务角色解析模型（优先级/默认/优雅降级）
    │   ├── autoconfig.py         #   环境探测 → 生成 → 回写整套配置
    │   ├── actions.py            #   自然语言 → 白名单动作（需确认）
    │   └── templates.py          #   题材预设 / 勾选项 / 意图模板
    ├── web/                      # dj serve 控制台（零依赖）
    │   ├── server.py             #   stdlib HTTP + JSON API + 后台任务
    │   └── static/index.html     #   单页深色控制台 UI
    ├── providers/                # llm / tts / comfyui / music 适配器
    ├── pipeline/                 # 12 个阶段 + runner + timeline
    ├── prompts/                  # 各阶段 LLM 提示词模板
    ├── media/                    # ffmpeg / 字幕
    └── utils/
```

---

## 八、工作原理要点

- **时间轴由配音驱动**：每句台词的真实音频时长决定场景长度，镜头按比例拉伸铺满，
  字幕用同一时间轴 → 画面/人声/字幕永远对齐。
- **角色一致性（三层）**：`analyze` 抽角色 → `character` 定妆阶段把外貌整理成稳定英文
  锚点，并用 ComfyUI 出三视图参考图 → `visual` 出图时注入锚点；`characters.consistency:
  ref` 会把参考图喂给工作流的 `LoadImage` 节点（需配 `comfyui.t2i_nodes.ref_image`），
  `seed_mode: character` 让同一角色跨镜头用稳定种子。角色卡可锁定，锁了不会被重写。
- **首尾帧（可选）**：`comfyui.first_last_frame` + `flf_workflow` + `i2v_nodes.last_image`
  三处齐备时，每个镜头会先生成起始帧和结束帧，再交给双图 i2v 工作流；缺任何一项自动
  退回单图 i2v，不影响其他流程。分镜台上的单镜抽屉可按镜头覆盖首尾帧开关。
- **场景转场**：`compose.transition: fade` 对每个场景片段做等时长淡入淡出（不用 xfade
  叠化，避免画面轨变短导致人声/字幕错位）；`none` 即硬切。
- **可续跑**：所有状态写进 `project.json`，节点级 `status`。中途失败/换配置都能接着跑。
- **AI 优雅降级**：控制台里所有 AI 能力（配置生成/打标签/检索/动作解析）都容错——
  模型端点不可用时自动回退到规则/直通，界面不卡、手动流水线照跑，绝不因为「AI 挂了」而不可用。

---

## 九、命令速查

| 命令 | 作用 |
|------|------|
| `dj serve [--port --no-browser]` | **打开 AI 原生 Web 控制台（推荐入口）** |
| `dj setup "<意图>" [--preset --chips --extra --dry-run]` | AI 一键生成整套配置 |
| `dj setup --list-templates` | 列出所有题材预设/勾选项/意图模板 |
| `dj ai "<指令>" [--project --yes]` | 自然语言 → 白名单动作（解析后确认执行） |
| `dj search "<大白话>" [--project --limit]` | AI 检索素材（自然语言→结构化查询） |
| `dj tag <项目> [--no-ai]` | 给项目素材补 AI 标签/分类 |
| `dj doctor` | 自检 ffmpeg/LLM/TTS/ComfyUI |
| `dj comfy-test [--gen]` | 远程 ComfyUI 对接自检（含试生成一张图） |
| `dj new <名> --source <文件>` | 建项目 |
| `dj run <项目> [--stages --stop-after --episodes]` | 跑流水线 |
| `dj status <项目>` | 看进度表 |
| `dj voices` | 列出可用音色 |
| `dj config [--init/--dump]` | 查看/导出配置 |
| `dj clean <项目> --what tmp\|intermediates` | 清理中间产物 |

---

## 十、迭代路线（Roadmap）

已具备：全流程打通、可插拔 Provider、断点续跑、竖屏合成、硬字幕、Ken Burns 运动、
侧链 BGM、封面、**远程 ComfyUI 对接**、**AI 原生 Web 控制台**（一键配置 / 多模型分工 /
资产自动打标签分类 / 自然语言检索 / 自然语言驱动动作 + 确认）、**角色定妆与参考图注入**、
**首尾帧驱动**、**场景淡入淡出**、**分镜台单镜返工与台词编辑闭环**。

后续可加：
- [ ] 场景切换的闪黑/叠化样式与节拍卡点
- [ ] 角色 LoRA 自动训练/管理，进一步增强一致性
- [x] ~~Web UI（浏览器里看分镜、改台词、单镜重出图）~~ → 已交付 `dj serve` 控制台
- [x] ~~控制台里直接改台词/单镜重出图的编辑闭环~~ → 分镜台抽屉 + 单镜返工
- [ ] 数字人口播模式（对接 SadTalker / EchoMimic / MuseTalk）
- [ ] AI 视频生成 API（可灵/海螺/Vidu）作为 ComfyUI 之外的画面来源
- [ ] 音效 SFX 层（脚步/门/打斗），按分镜事件自动铺
- [ ] 红果/抖音 上传元数据（标题/简介/标签/封面）批量导出

---

> 个人项目，MIT。模型与素材的版权/合规请自行确认，尤其是商用发布。
