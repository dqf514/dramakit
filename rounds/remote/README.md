# rounds/remote —— 3090 那台机器的工具

那边是另一台机器（192.168.31.8）：两张 3090、两个 ComfyUI 容器
（8188 和 8189）、一个 vllm 网关。碰它要 ssh，所以工具都放这里，
免得跟本机的混在一起。

## 那边的机器

| 工具 | 干什么 |
|---|---|
| `doc_3090.md` | 那台机器上装了什么、怎么连 |
| `docker-compose.h3.yml` | 两个 ComfyUI 容器的编组（每个容器一张卡） |
| `card_health.sh` / `check_both.sh` | 显卡和容器 |
| `remote_check.sh` / `remote_diag.sh` / `remote_err.sh` | 连得上吗、报什么错 |
| `remote_start.sh` / `remote_stop.sh` | 起停那边的服务 |
| `remote_log.sh` / `remote_out.sh` / `remote_hist.sh` | 看日志和输出 |
| `remote_gpu_hist.sh` / `remote_gpu_hist2.sh` | 显卡的占用历史 |
| `remote_mem_report.sh` / `fix_remote_mem.sh` | 显存不够的时候（模型常驻把卡占满了） |
| `remote_flux_check.sh` / `remote_wf.sh` | 出图和视频的工作流 |
| `remote_clip.sh` | 拿一段成片下来 |
| `remote_mode.sh` / `remote_onecard.sh` | 单卡跑 / 一台机器跑 |

## 往那边搬东西

| 工具 | 干什么 |
|---|---|
| `fetch_3090.ps1` / `fetch_h3_models.ps1` / `fetch_musetalk.ps1` / `fetch_ref2va.ps1` / `fetch_whisper_small.ps1` | 下模型和权重过去 |

## 别的

| 工具 | 干什么 |
|---|---|
| `shutdown_3090.py` | 关掉那边 |
| `validate_3090.py` | 验一下那边是不是好的 |
| `upgrade_torch_cu130.py` / `fix_torch_cu130.py` / `check_torch_cu130.py` | 换 torch（cu130）——**装完就把 1.8G 的 wheel 删了**，不再留着 |
| `strata_*.sh` / `start_strata_gpu1.sh` | 那边的上下文长度实验（256k） |
| `switch_ip.py` | 换那台机器的地址 |

那台机器上教师的工作流在 `rounds/teacher_h3/`（八个 H3 工作流，参考用的）。
