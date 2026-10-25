# 改造计划 TODO

> 目标：把 DramaKit 从"单机单节点"改造成"多机多节点的算力池"，让 H3 出视频
> 与 FLUX 出图各自专机专模，充分利用多张卡，并把新节点接入的模型同步自动化。

---

## 现状（2026-10-25 实测）

| 项 | 实测值 |
| --- | --- |
| 单机 23 镜总耗时 | **145 分钟**（出图 15 分钟 + 出视频 130 分钟） |
| 出图 SDXL 25 步 | 40 秒/镜（其中 16 秒模型初始化） |
| 出视频 H3 turbo 8 步 | 340 秒/镜（**其中 78 秒模型初始化**） |
| 模型初始化占比 | 每镜 94 秒 / 380 秒 ≈ **25%** |

**关键结论**：单机交替做图和视频，每镜都要把上一个模型踢出显存、换入下一个
（16GB 装不下 H3 15.2G + H3 文本编码器 14.6G + SDXL 6.5G）。**专机专用**能让
ComfyUI 的模型缓存复用，每镜 78 秒初始化开销直接归零。

### 本轮新发现（推翻旧结论）

| 项 | 旧值 | 实测新值 | 影响 |
| --- | --- | --- | --- |
| H3 生成分辨率 | 以为 1344×768 | **实际 864×480** | 成片 1280×720 是 1.48 倍放大，必糊 |
| H3 在 1344×768 | 未测 | **527 秒/镜**（含 78 秒加载） | 比 864×480 慢约 1.55 倍 |
| 出图模型 | SDXL 1.0 | **FLUX 3 Image Klein**（2026-10-15 发布） | 见第四节 |
| FLUX 1.x 权重 | 打算下 Q6_K | **作废** | 已停下载，只下了 45KB |

---

## 一、算力池架构（Plan B 核心）

### 1.1 节点角色
- [x] `NodeConfig` 增加 `roles: list[str]`（`t2i` / `i2v`），标注节点专长
- [x] 节点池配置支持按角色筛选：`dj nodes --role i2v`
- [x] 同一节点可配多角色（未标注则视为通用节点）

### 1.2 Provider 改造成 pool
- [x] `ComfyUIClient` → `ComfyUIPool`：持有多节点客户端
      （`dramakit/providers/pool.py`，有额外节点时才启用，单机路径不变）
- [x] 派发策略：**同角色内按队列深度选最闲的**（查各节点 `/queue`，
      3 秒缓存），不用轮询（避免把活压到已经排队的节点上）
- [x] 出图任务只派给 `t2i` 节点，出视频只派给 `i2v` 节点
- [x] 通用节点（无 roles）作为兜底，任何任务都能接
- [x] 每节点并发 1（大模型占满显存），节点间并行
- [x] **失败转移**：某节点渲染失败，该镜自动重派给下一个候选节点
- [ ] 跨节点首帧传递：A 机出图 → B 机做 i2v 时，首帧要传过去
      （`upload_image` 已有，但派发层还没把"用哪个节点出的图"记下来）
- [ ] 派发结果要在日志/前端里可见（现在只有失败时才打日志）

### 1.4 目标配置
```yaml
comfyui:
  models_dir: E:\\ComfyUI\\models
  nodes:
    - name: gpu3090-v0      # 3090#0，专做 i2v
      base_url: http://<3090IP>:8188
      roles: [i2v]
      transfer: scp         # 或 shared
    - name: gpu3090-v1      # 3090#1，专做 i2v
      base_url: http://<3090IP>:8189
      roles: [i2v]
      transfer: scp
```

---

## 二、双 3090 部署要点

- [ ] **一台机器开两个 ComfyUI 实例**（H3 单任务吃 15.2G+14.6G，一张卡塞不下两个任务）：
      ```bash
      CUDA_VISIBLE_DEVICES=0 python main.py --listen 0.0.0.0 --port 8188
      CUDA_VISIBLE_DEVICES=1 python main.py --listen 0.0.0.0 --port 8189
      ```
- [ ] **模型只拷一份**：两个实例共用同一 models 目录，H3 那套 ~35G 不用拷两遍
- [ ] **3090 跑 int8_convrot 高质量版**（19.5G，24G 装得下；5080 的 16G 装不下只能跑 w6a8）
- [ ] Ampere 无原生 FP8，官方文档说 30 系 **INT8 比同体积 FP8 更快**（INT8 矩阵运算约 2× FP16），
      所以 3090 用 int8_convrot 既是更高质量也更快

### 预期收益（按 1344×768 重算）
| 配置 | 23 镜总耗时 |
| --- | --- |
| 现状（单机 5080 交替，864×480） | 145 分钟 |
| 单机 5080 @ 1344×768 | ~230 分钟（527 秒/镜） |
| 5080 出图 + 3090×2 出视频 @ 1344×768 | **~1.5 小时**（并行） |
| 再让 5080 跑完图后加入视频 | ~1.2 小时 |

---

## 三、模型自动同步（已部分完成）

- [x] **工作流即清单**：扫描 `config/comfyui/*.json` 的模型加载节点，自动推出要传的模型
- [x] `dj nodes` / `dj nodes check`：连通 / 版本 / GPU / 显存 / 模型齐全度自检
- [x] `dj nodes sync <名字>`：缺什么补什么，带每文件与总体进度、速度、ETA
- [x] 两种传输方式：`shared`（已挂载直接拷）/ `scp`（走 ssh）
- [x] 前端「流水线 → 节点池」面板：节点状态 + 缺失模型 + 同步进度条
- [x] `dj comfy-test` 改为按**工作流实际引用的模型**逐个核对服务器可见性
      （原先只看 `checkpoints/`，FLUX 的 `diffusion_models/` 完全看不见）
- [ ] **断点续传**：scp 传输中断后能接着传（当前是整文件重来）
- [ ] **校验完整性**：按文件大小/哈希校验，避免传了半个文件
- [ ] 同步完成后自动触发目标节点刷新模型列表
- [ ] 支持"新增节点"的向导：填地址 → 探测 → 拉模型 → 加入池

---

## 四、5080 出图换 FLUX 3 Image Klein（本轮已完成主体）

### 4.1 选型：为什么是 FLUX 3 而不是 FLUX.1-schnell
FLUX 3 Image Klein 于 **2026-10-15** 发布（5.6B 开放权重，ComfyUI 0.42.0 已支持），
比 FLUX.1-schnell 适合我们的地方：
- **多参考图（最多 10 张）** → 角色一致性可以走原生多参考，而不是硬塞单张
- 文本编码器是 **Qwen3-VL-4B**（T5 之后的大幅升级，提示词服从度更好）
- 文字渲染更可靠（短剧里常有招牌、纸条、手机屏）
- 蒸馏版 16 步出图

### 4.2 已完成
- [x] 定位到官方权重（`black-forest-labs/flux-3-image-klein-comfy` 是 gated 的 401），
      改用镜像 `ml-resources/flux-3-image-klein-comfy`（可下载，非门禁）
- [x] 并行分块下载器 `dl_par.py`（8 段并发，**66~82 MB/s**，单流只有 8.5MB/s 且会卡死）
- [x] 落位：
      - `diffusion_models/flux3-image-klein-int8-convrot.safetensors`（5.43G，校验通过）
      - `text_encoders/qwen3vl_4b_int8_convrot.safetensors`（4.52G）
      - `vae/flux2-vae.safetensors`（336M）
      - `text_encoders/qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors`（6.26G，提示词扩写器）
- [x] FLUX 3 版 t2i 工作流 `config/comfyui/t2i_flux3_klein.json`（API 格式）
      `UNETLoader + CLIPLoader(type=flux3) + VAELoader + 2×CLIPTextEncode +
       EmptyFlux2LatentImage + ModelSamplingFlux(shift=log(16)) + KSampler + VAEDecode`
- [x] 工作流映射层支持 FLUX 架构：`checkpoint` 写 `unet_name`（SDXL 写 `ckpt_name`），
      新增 `clip` / `vae` / `sampling` 语义节点
- [x] `prompt_format: flux3` 切换提示词模板：**完整场景描述**（100~350 词，
      媒介开头 → 场景 → 光线 → 镜头 → 人物），负面词自动置空
- [x] `video_width/height` 让 H3 分辨率可配（已从 864×480 提到 **1344×768**）

### 4.3 待办
- [x] **定位并解决"出图是废图"的根因**（2026-10-26）：
      症状 = 颜色语义对（苹果红/叶绿/木黄）但空间结构完全丢失。
      逐一排除：VAE 往返无损 ✓、shift/调度/时间嵌入与官方参考实现逐项一致 ✓、
      flow_map 判定正确（`ref_time_in` 存在）✓、官方工作流原样复现同样废 ✓。
      **真凶：文本编码器 `qwen3vl_4b_int8_convrot.safetensors` 本身产出垃圾条件。**
      换成 `qwen3vl_4b_bf16.safetensors` 后一次成功（红苹果 / 木桌 / 散景，完全对题）。
      → `comfyui.clip_name` 与工作流里的 `clip_name` 都必须写 bf16 版。
      （同仓库的 `qwen3.5_9b_flux3_prompt_upsampler_w4a8` 是好的，坏的只有 int8_convrot 那个）
- [x] **实测出图**：1344×768 / 16 步 / **15.8 秒一张**，提示词逐句还原
      （走廊/拖鞋/自行车/尘埃光束全部出现）
- [x] **角色/场景参考图改成 FLUX 3 版提示词**：旧的是 SDXL 关键词堆叠，
      FLUX 3 把 "character reference sheet" 当真的，画出来是**机甲技术线稿**。
      改成"完整场景描述"后出的是正经棚拍人像（锚点全中）。
- [x] **多参考图链路**：`t2i_flux3_klein_ref.json`（`ReferenceMultiLatent` +
      两个参考槽位）；竖版角色参考图用 `fit_reference()` 模糊填充到 16:9，
      否则输出尺寸会跟着参考图变成竖版
- [ ] **重新生成全部角色参考图 / 场景参考图**（现有的是老 SDXL 出的机甲线稿）
- [ ] 提示词扩写器（`qwen3.5_9b_flux3_prompt_upsampler_w4a8`）：BFL 明确说
      "不要在没有提示词扩写器的情况下使用该模型"。已验证扩写器本身工作正常
      （能产出 200+ 词完整场景描述 + 元素表）。两个选择：
      - [ ] 走官方扩写器（多占 6.26G 显存/时间，每镜 +30~60 秒）
      - [x] 用流水线现有的 LLM + BFL 官方 system prompt（在 promptgen 里做，省 6.26G）
            → 已把官方 system prompt 的规则译进 `FLUX3_IMAGE_SYSTEM`
- [ ] FLUX 3 的 `Flux3LayoutPrompt` 边界框布局（可选进阶）
- [x] 对比 SDXL 的 40 秒/张：FLUX 3 更快（15.8 秒）且质量高一个档

---

## 五、专业后期（剪映 vs Resolve 的取舍）

**结论：不做二选一，做双轨。**

| 轨道 | 工具 | 用途 |
| --- | --- | --- |
| ① 自动出片 | ffmpeg（现有 compose） | 确定性、无 GUI、可批量、可复现 |
| ② 专业精修 | **FCPXML 导出** → Resolve / Premiere / FCP | 人工精修、换包装、改调色 |

**剪映（CapCut）接不进来**：没有任何可编程的渲染接口（无 CLI / 无脚本 API / 无 headless 导出），
是纯 GUI 应用；而且它的强项是竖屏模板包装（花字、卡点），不是叙事连贯 + 声音规范。
**DaVinci Resolve 可以**（免费版就带完整 Python/Lua 脚本 API，能 headless 渲染），
但要装 3GB、必须跑桌面进程、版本坑多，适合当可选后端而不是默认渲染器。

- [x] **统一调色** `compose.grade_shots`：逐镜 `signalstats` 测量后拉到本集中位数
      （实测镜头亮度 70~98、饱和 0.6~11.5，差异确实大）
- [x] **垫底响度归一** `compose.normalize_bed_loudness`：H3 每镜原生音频 loudnorm 到
      `-24 LUFS` 再垫底，BGM 不再忽大忽小
- [x] **音乐轨重构**：bed / 曲库 BGM 各自增益合成一条 music stem，再与对白混，
      取代原来 `bgm_volume` 套两遍的混乱增益
- [x] **FCPXML 导出** `compose.nle_export`：每集一份 `.fcpxml`（画面 spine + 对白轨 + 音乐轨）
- [x] **成片 QC** `qc` 阶段：分辨率/帧率/时长/音画同步、EBU R128 响度与真峰、
      黑帧、字幕文件，写 `qc/ep_XXX.json`
- [ ] Resolve 直出后端（可选）：`resolve` 脚本建时间线 → headless 渲染
- [ ] 成片 QC 接到前端（资产页显示每集的 QC 结论）
- [ ] LUT 支持：给全片套统一色调（`compose.lut` 已留字段，还没配 .cube 文件）

---

## 六、其它待办

- [ ] 断点续跑：分集/分镜变化时，只重跑受影响的镜头
- [ ] 整集预览页：把多机产出的镜头按时间轴拼成一个可看的草稿
- [ ] 失败镜头重试队列：单镜失败不阻断整集，改由 precheck 汇总报告
- [ ] Pydantic 序列化警告（`stage_status` 用 str 而非 enum）：修 `Status` 类型声明
- [ ] 清理 `models/checkpoints/v1-5-pruned-emaonly.safetensors`（SD1.5，已不参与出图）
- [ ] `dj nodes sync` 支持断点续传 + 哈希校验

---

## 变更记录
- 2026-10-25（初版）：节点池/清单/同步/自检/前端进度条；实测耗时基线；
  定下"专机专用 + 角色派发"的改造方向。
- 2026-10-25（第二轮）：发现 H3 实际只有 864×480（成片是 1.48 倍放大）；
  改用 FLUX 3 Image Klein（官方 FLUX.1 仓库已 401，改走镜像 + 并行分块下载）；
  实现专业后期层（统一调色 / 垫底归一 / FCPXML 导出 / 成片 QC）。

