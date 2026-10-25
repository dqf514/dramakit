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

---

## 一、算力池架构（Plan B 核心）

### 1.1 节点角色
- [ ] `NodeConfig` 增加 `roles: list[str]`（`t2i` / `i2v`），标注节点专长
- [ ] 节点池配置支持按角色筛选：`dj nodes --role i2v`
- [ ] 同一节点可配多角色（未标注则视为通用节点）

### 1.2 Provider 改造成 pool
- [ ] `ComfyUIClient` → `ComfyUIPool`：持有多节点客户端
- [ ] 派发策略：**同角色内按队列深度选最闲的**（查各节点 `/queue`），
      不用轮询（避免把活压到已经排队的节点上）
- [ ] 出图任务只派给 `t2i` 节点，出视频只派给 `i2v` 节点
- [ ] 通用节点（无 roles）作为兜底，任何任务都能接
- [ ] 每节点并发 1（大模型占满显存），节点间并行

### 1.3 跨节点素材传递
- [ ] 出图在 A 节点、，视频在 B 节点：首帧图要传给 B
      （复用现有 `upload_image`，只需确保派发后走对节点）
- [ ] 失败转移：节点中途掉线时，该镜重派给其它节点

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

### 预期收益
| 配置 | 23 镜总耗时 |
| --- | --- |
| 现状（单机 5080 交替） | 145 分钟 |
| 5080 出图 + 3090×2 出视频 | ~45-65 分钟 |
| 再让 5080 跑完图后加入视频 | ~40 分钟 |

---

## 三、模型自动同步（已部分完成）

- [x] **工作流即清单**：扫描 `config/comfyui/*.json` 的模型加载节点，自动推出要传的模型
- [x] `dj nodes` / `dj nodes check`：连通 / 版本 / GPU / 显存 / 模型齐全度自检
- [x] `dj nodes sync <名字>`：缺什么补什么，带每文件与总体进度、速度、ETA
- [x] 两种传输方式：`shared`（已挂载直接拷）/ `scp`（走 ssh）
- [x] 前端「流水线 → 节点池」面板：节点状态 + 缺失模型 + 同步进度条
- [ ] **断点续传**：scp 传输中断后能接着传（当前是整文件重来）
- [ ] **校验完整性**：按文件大小/哈希校验，避免传了半个文件
- [ ] 同步完成后自动触发目标节点刷新模型列表
- [ ] 支持"新增节点"的向导：填地址 → 探测 → 拉模型 → 加入池

---

## 四、5080 出图换 FLUX（当前 SDXL 效果太差）

### 4.1 选型
- [ ] 图像模型：`FLUX.1-schnell`（Apache-2.0，4 步蒸馏，提示词服从度远好于 SDXL）
- [ ] 权重格式：GGUF（`city96/FLUX.1-schnell-gguf`）
  - 5080（16G）→ **Q6_K（9.16G）**：总占用 ~14.3G，留足余量不抖动
  - 3090（24G）→ **Q8_0（11.82G）**：总占用 ~17G，很宽裕
- [ ] 文本编码器：`t5xxl_fp8_e4m3fn`（4.56G）+ `clip_l`（0.23G）
- [ ] VAE：`ae.safetensors`（0.31G）—— **官方仓库是 401 门禁，hf-mirror 同样拦**，
      需找 ungated 镜像（候选：`Shakker-Labs/FLUX.1-dev`、`Kijai/flux-fp8` 的
      `flux-vae-bf16.safetensors` 需实测确认与官方 ae 等价——官方 ae 是 335MB，
      Kijai 那份 167MB 正好一半，存疑）

### 4.2 接入
- [ ] 安装 `ComfyUI-GGUF` 自定义节点（GGUF 权重加载器）
- [ ] 写 FLUX 版 t2i 工作流（API 格式）：
      `UnetLoaderGGUF` + `DualCLIPLoader(type=flux)` + `FluxGuidance` +
      `EmptySD3LatentImage` + `KSampler(euler/simple, 4步, cfg=1)` + `VAEDecode`
- [ ] 配置指向新工作流，`dj comfy-test --gen` 实测出图
- [ ] 角色一致性要重新适配：FLUX 用 `DualCLIPLoader`，
      角色参考图注入需改用 FLUX 的 image-conditioning 节点（或退回纯文本锚点）

### 4.3 提示词调整
- [ ] FLUX 提示词习惯与 SDXL 不同：**自然语言描述**，不要堆关键词、不要写
      "8k, masterpiece, best quality" 这类 SDXL 套话
- [ ] 负面词在 FLUX 常规 checkpoint 上**不起作用**（schnell 尤其），要去掉
- [ ] `t2i_nodes` 里的 `negative` 映射对 FLUX 要留空

---

## 五、其它待办

- [ ] 断点续跑：分集/分镜变化时，只重跑受影响的镜头
- [ ] 整集预览页：把多机产出的镜头按时间轴拼成一个可看的草稿
- [ ] 失败镜头重试队列：单镜失败不阻断整集，改由 precheck 汇总报告
- [ ] Pydantic 序列化警告（`stage_status` 用 str 而非 enum）：修 `Status` 类型声明
- [ ] 清理 `models/checkpoints/v1-5-pruned-emaonly.safetensors`（SD1.5，已不参与出图）

---

## 变更记录
- 2026-10-25：初版。已完成节点池/清单/同步/自检/前端进度条；
  记录实测耗时基线；定下"专机专用 + 角色派发"的改造方向。
