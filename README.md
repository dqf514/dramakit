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
左侧图标栏把工作分成八块，彼此联动：**导引 / 工作台 / 分镜台 / 角色库 / 流水线 / 资产 / 设置 / 环境**。

第一次打开（还没有项目）会落在 **「导引」**：它把「环境 → 导入 → AI 改编 → 画面 → 声音 → 合成」拆成 7 步，
每步直接读项目的真实阶段状态，做完自动打勾；按钮可以原地提交后台任务，也可以跳到对应的编辑页面。
导引页同时包含：

- **整体架构图**：文本链（1~7）→ 生成链（8~11）→ 合成链（12），以及 `project.json / 后台任务 / catalog.db / Provider`
  四个基座；点任意阶段可直接去流水线重跑。
- **外挂接入手册**：ComfyUI、大模型、TTS、BGM、ffmpeg 各自的配置键、步骤和「环境自检」结果。
  ComfyUI 一栏内置 **自动接入**：填地址 → 自动识别工作流与节点编号 → 选择后一键写回配置，
  不用再手抄 JSON 里的节点 ID；工作流缺节点/插件会直接列出。
- **无缝工作流说明**：一键跑全链、断点续跑、改一处只废下游、后台任务、配音驱动时间轴、失败不连坐。
- **新建/导入表单**：填项目名和小说路径即可创建并自动跑「导入」。

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

这一版把「看片、改片、返工」搬进了控制台，不用再翻 `project.json`。界面默认浅色主题，
右上角可一键切换深色；选择会记在浏览器里，下次打开保持不变。

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

## 六、整体架构与外挂程序接入

### 6.1 架构图

```text
                 ┌──────────────────────── 控制台 dj serve（浏览器）────────────────────────┐
                 │  导引 · 工作台 · 分镜台 · 角色库 · 流水线 · 资产 · 设置 · 环境             │
                 └───────────────────────────────┬───────────────────────────────────────────┘
                                                 │ JSON API + 后台任务/轮询
┌────────────┐   ┌───────────────────────────────▼───────────────────────────────────────────┐
│ 小说/剧本   │→ │ ingest → analyze → character → segment → script → storyboard → promptgen  │
└────────────┘   └───────────────────────────────┬───────────────────────────────────────────┘
                                                 │ 台词 / 分镜 / 提示词
                        ┌────────────────────────┼─────────────────────────┐
                        ▼                        ▼                         ▼
                  ComfyUI (T2I / I2V)        TTS 配音                  曲库 / MusicGen
                        │ 图 / 视频              │ 逐句音频                 │ BGM
                        └────────────────────────┼─────────────────────────┘
                                                 ▼
                            voice → subtitle → music → compose（ffmpeg）
                                                 │
                                                 ▼
                            9:16 成片 mp4 · 硬字幕 srt · 封面
```

四层职责：

| 层 | 负责 | 关键位置 |
|----|------|----------|
| 交互层 | 导引、编辑、预览、自然语言指令 | `dramakit/web/static/index.html` |
| 编排层 | 12 阶段顺序、状态机、断点续跑、任务队列 | `dramakit/pipeline/runner.py` |
| 能力层 | LLM / 画面 / TTS / 音乐 / ffmpeg 可替换适配器 | `dramakit/providers/` |
| 数据层 | 项目状态、素材、时间轴、资产目录 | `projects/<项目>/project.json`、`catalog.db` |

产物在磁盘上的流向：

```text
source/小说.txt
   → project.json（集 → 场 → 镜 → 台词 + 状态）
   → images/  video/  audio/  subs/  bgm/  covers/
   → episodes/ep_001.mp4（成片）
```

### 6.2 ComfyUI（画面 / 视频）

完整部署步骤见 **[`deploy/comfyui-server.md`](deploy/comfyui-server.md)**，含 Linux/Windows 安装、
PyTorch CUDA、AnimateDiff + VideoHelperSuite 自定义节点、模型下载、systemd 自启、防火墙、
Nginx 反代 + Basic Auth、SSH 隧道。一键脚本（Linux）：

```bash
bash deploy/setup_comfyui.sh
```

**接入（控制台全自动）：**

1. GPU 机器启动 ComfyUI：`python main.py --listen 0.0.0.0 --port 8188`（本机可只监听 127.0.0.1）。
2. 在 ComfyUI 里搭好「文生图」「图生视频」两条能跑通的工作流，各自 **Save (API Format)** 导出 JSON。
3. 把 JSON 放进 `config/comfyui/`（文件名随意），控制台「导引 → ComfyUI」填地址点 **自动识别**。
4. 识别会扫描工作流、从图结构推断节点编号、校验模型与插件，并推荐出图/视频/首尾帧各一套；
   确认后点 **应用并启用**，配置原位写回 `default.yaml` 并立刻自检。

节点映射不需要手填：`comfyui.auto_map: true` 会按节点类型和连线自动推断
（KSampler / CLIPTextEncode / CheckpointLoader / EmptyLatentImage / LoadImage / VideoCombine…），
`auto_workflows: true` 允许在路径为空或失效时自动扫描 `config/comfyui/*.json`。
手填仍然优先；工作流改编号后失效的手填值会被忽略并重新推断，不会卡住出图。

需要手动覆盖时，配置键与语义节点对应关系如下：

| 配置键 | 指向的节点 | 写入内容 |
|--------|------------|----------|
| `t2i_nodes.positive` | 正向 `CLIPTextEncode` | 镜头提示词 |
| `t2i_nodes.negative` | 负向 `CLIPTextEncode` | 负向词 |
| `t2i_nodes.seed` | `KSampler` | seed |
| `t2i_nodes.width` / `height` | `EmptyLatentImage` | 宽 / 高 |
| `t2i_nodes.steps` / `cfg` | `KSampler` | 采样步数 / CFG |
| `t2i_nodes.sampler` | `KSampler` | sampler_name / scheduler |
| `t2i_nodes.checkpoint` | `CheckpointLoaderSimple` | checkpoint 文件名 |
| `t2i_nodes.ref_image` | `LoadImage`（可选） | 角色 / 场景参考图主槽 |
| `i2v_nodes.image` | `LoadImage` | 首帧 |
| `i2v_nodes.last_image` | `LoadImage`（可选） | 尾帧（首尾帧模式） |
| `i2v_nodes.frames` | 帧数节点 | length / frames |
| `i2v_nodes.fps` | 视频合成节点 | frame_rate / fps |

**远程 / 局域网 / 反代：**

```yaml
comfyui:
  base_url: http://192.168.1.50:8188
  use_proxy: false              # 必须 false，否则 httpx 会读系统代理导致连不上
  auth: token                   # none | basic | token | header
  auth_token: ""                # 建议环境变量 DRAMAKIT_COMFYUI_TOKEN
  verify_tls: true              # 内网自签名证书可设 false
  use_websocket: true
  ws_fallback_to_poll: true     # 反代挡掉 WS 时自动回退轮询 /history
```

验证：`dj comfy-test --gen`（含试生成一张图），或控制台「导引 → 环境自检」。
自检会逐个校验工作流里的节点类型和映射 ID，缺插件/节点会直接列出问题。

**一致性默认全自动（不配会自动降级，不报错）：**

- **参考图出图**：默认 `characters.consistency: ref`。角色三视图和场景环境图由定妆/画面
  阶段自动生成，主槽优先放当前镜头的角色，其次放场景参考；工作流没有 `LoadImage`
  参考槽时自动忽略，退回纯文字锚点。
- **首尾帧图生视频**：准备支持双图输入的 i2v 工作流后在控制台勾选即可；`first_last_frame`
  未开时自动走单图 i2v。分镜台单镜抽屉也能按镜头覆盖。

### 6.3 大模型 LLM（文本）

所有文本阶段都走 **OpenAI 兼容**接口，云端/本地任选：

```yaml
llm:
  base_url: http://localhost:11434/v1     # Ollama；LM Studio 用 :1234
  model: qwen2.5:14b
  api_key: ollama                         # 本地随便填；云端建议环境变量 DRAMAKIT_LLM_API_KEY
```

云端示例：DeepSeek `https://api.deepseek.com/v1`、通义 `https://dashscope.aliyuncs.com/compatible-mode/v1`、
Kimi `https://api.moonshot.cn/v1`、OpenAI `https://api.openai.com/v1`。

多模型分工在 **「设置 → 模型清单」**：可加任意个端点，按任务勾选（分析/分集/剧本/分镜/提示词/
配置/动作/检索/打标），列表顺序即优先级，未勾选任务由默认模型兜底。保存会原位写回 YAML 并保留注释；
每个模型都有「测试」按钮，会拉取端点上的真实模型列表。详见 [4.5](#45-多模型分工模型清单)。

### 6.4 配音 TTS

```yaml
tts:
  provider: edge                  # edge | cosyvoice | openai | minimax
  base_url: http://localhost:9880 # cosyvoice / 其它本地服务
  voice_map:                      # 角色 → 音色
    林凡: zh-CN-YunxiNeural
    苏晚: zh-CN-XiaoxiaoNeural
```

- `edge`：免费、无需 Key，开箱即用（默认云希/云扬/晓晓）。
- `cosyvoice`：本地 HTTP 服务，可克隆音色；局域网地址填 `base_url`，`use_proxy: false`。
- `openai`：任意兼容 `/v1/audio/speech` 的服务；`minimax`：云端多情感音色。
- 配音阶段会回填每句真实音频时长，后面镜头、字幕、合成全部复用这条时间轴。

### 6.5 配乐 BGM 与合成

```yaml
music:
  provider: library               # library | musicgen | suno | none
  library_dir: assets/music
  duck_voice: true                # 有人说话时自动压低 BGM
  loop_to_fit: true               # 自动循环铺满整集
```

- `library`：把版权音乐丢进 `assets/music`，按情绪命名，或配 `mood_map` 显式映射。
- `musicgen`：本地/HTTP MusicGen 服务，填 `base_url`；`suno`：Suno 兼容 API。
- 合成只用 **ffmpeg/ffprobe**（必须在 PATH）。Windows 可用 winget/scoop/choco 安装或手动加 PATH；
  macOS `brew install ffmpeg`；Linux `sudo apt install ffmpeg`。`dj doctor` 可自检。

### 6.6 其它外挂 / 自定义协议

Provider 层是开放的：任何 OpenAI 兼容 LLM/TTS、Suno 兼容音乐 API 都能直接接。画面服务若换成
非 ComfyUI 的 REST，实现 `providers/base.py` 的 `BaseImageVideo`（生成 → 等待 → 下载）即可；
TTS / 音乐同理实现 `BaseTTS` / `BaseMusic`，在 `providers/__init__.py` 的工厂里注册。
流水线阶段只依赖抽象接口，不需要改。

### 6.7 什么算“无缝”

- **一键全链**：十二阶段按固定顺序执行，已完成节点自动跳过。
- **断点续跑**：状态写进 `project.json`，崩溃、换模型、换 ComfyUI 后直接重跑。
- **只废下游**：改台词作废该句配音/字幕/合成；改角色锚点重置相关提示词；单镜返工只重出该镜。
- **后台任务**：画面/视频可能跑几十分钟，任务在服务端线程中执行，浏览器轮询，可随时切页。
- **时间轴只认配音**：每句音频时长决定场景长度，镜头按比例铺满，字幕同一条时间轴，合成不跑偏。
- **失败不连坐**：ComfyUI 挂了只影响画面；AI 端点不可用时配置/打标/检索回退规则，其它阶段照跑。

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
    │   └── static/index.html     #   单页浅色/深色控制台 UI（含导引与架构图）
    ├── providers/                # llm / tts / comfyui / music 适配器
    ├── pipeline/                 # 12 个阶段 + runner + timeline
    ├── prompts/                  # 各阶段 LLM 提示词模板
    ├── media/                    # ffmpeg / 字幕
    └── utils/
```

---

## 八、工作原理要点

整体架构图与外挂接入见 [第六章](#六整体架构与外挂程序接入)。几个关键设计：

- **时间轴由配音驱动**：每句台词的真实音频时长决定场景长度，镜头按比例拉伸铺满，
  字幕用同一时间轴 → 画面/人声/字幕永远对齐。
- **角色/场景一致性（全自动）**：`analyze` 抽角色 → `character` 定妆阶段把外貌整理成稳定
  英文锚点、用 ComfyUI 出三视图、为每个场景出一张无人环境图、并由 AI 从可用音色里给角色
  分配声音 → `visual` 出图时把锚点前置，并按「角色主参考 + 场景参考」注入 `LoadImage`
  槽位；`characters.consistency: ref`（默认）启用参考图，工作流没有参考槽时自动退回纯文字
  锚点；`seed_mode: character` 让同一角色跨镜头用稳定种子。角色卡可锁定，锁了不会被重写。
- **首尾帧（可选）**：`comfyui.first_last_frame` + `flf_workflow` + `i2v_nodes.last_image`
  三处齐备时，每个镜头会先生成起始帧和结束帧，再交给双图 i2v 工作流；缺任何一项自动
  退回单图 i2v，不影响其他流程。分镜台上的单镜抽屉可按镜头覆盖首尾帧开关。
- **场景转场**：`compose.transition: fade` 对每个场景片段做等时长淡入淡出（不用 xfade
  叠化，避免画面轨变短导致人声/字幕错位）；`none` 即硬切。
- **可续跑**：所有状态写进 `project.json`，节点级 `status`。中途失败/换配置都能接着跑。
- **AI 优雅降级**：控制台里所有 AI 能力（配置生成/打标签/检索/动作解析）都容错——
  模型端点不可用时自动回退到规则/直通，界面不卡、手动流水线照跑，绝不因为「AI 挂了」而不可用。
- **导引驱动**：控制台「导引」页把上述设计翻译成 7 步可执行路线，并实时读取 `stage_status`；
  架构图、外挂配置和自检结果都放在同一页，第一次用不需要先读文档。

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
**首尾帧驱动**、**场景淡入淡出**、**分镜台单镜返工与台词编辑闭环**、**导引式上手与架构/外挂自检**、**浅色/深色主题**。

后续可加：
- [ ] 场景切换的闪黑/叠化样式与节拍卡点
- [ ] 角色 LoRA 自动训练/管理，进一步增强一致性
- [x] ~~Web UI（浏览器里看分镜、改台词、单镜重出图）~~ → 已交付 `dj serve` 控制台
- [x] ~~控制台里直接改台词/单镜重出图的编辑闭环~~ → 分镜台抽屉 + 单镜返工
- [ ] 数字人口播模式（对接 SadTalker / EchoMimic / MuseTalk）
- [ ] AI 视频生成 API（可灵/海螺/Vidu）作为 ComfyUI 之外的画面来源
- [ ] 音效 SFX 层（脚步/门/打斗），按分镜事件自动铺
- [ ] 红果/抖音 上传元数据（标题/简介/标签/封面）批量导出
- [ ] **多卡/多机统一调度（Plan B：ComfyUI provider 池）**
      现状 `comfyui.base_url` 为单端点。目标：支持 `endpoints: [ ... ]` 一组 ComfyUI，
      按各卡队列深度/显存把镜头派发给最闲的卡，visual 阶段并发出图/出视频（多画面并行）。
      配套 **模型自动同步**：新增 provider 节点时，自动比对并传输该节点缺失的模型文件
      （按文件名+大小/哈希校验），展示直观的传输进度（每文件百分比 + 总体进度 + 速率/ETA），
      支持断点续传与失败重试；并提供 **节点自检**（连通性 / 显存 / 已装模型清单 / 版本）
      与 **定期模型一致性同步**（检测各节点模型漂移并一键对齐）。

---

> 个人项目，MIT。模型与素材的版权/合规请自行确认，尤其是商用发布。
