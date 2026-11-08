# rounds/tools —— 平时用的工具

这里放的是**平时真会用到**的工具：起控制台、跑一个阶段、清一个项目、
看一眼产出、推代码。

一次性的东西不要留在这里——探一个问题的 `probe_*.py`、改一次代码的
`patch_*.py`、测一个 bug 的 `test_*.py`：它们做完就没用了，git 里
还留着（旧版本随时能翻出来），留在目录里只会让要找的东西找不到。

跟 3090 那台机器有关的工具在 `rounds/remote/`。

## 控制台

| 工具 | 干什么 |
|---|---|
| `restart_console.py` | 重启控制台（本机权限；旧的控制台是管理员起的，要用下面那个） |
| `restart_console_admin.ps1` | **管理员**重启控制台：结束占着 8080 的旧进程，起新的，并检查新代码在不在 |
| `run_pipeline_here.py` | 在这里跑某几个阶段（`python run_pipeline_here.py <项目> <阶段,阶段> [集号]`） |
| `stop_runs.py` | 叫停正在跑的活 |
| `set_look.py` | 设画幅和画风（`python set_look.py <项目> <画风id> <画幅> <尺寸>`） |

## 项目

| 工具 | 干什么 |
|---|---|
| `clean_project.py` | 把项目清回「只导入小说」的状态 |
| `clean_nodes.py` | 清节点池里没用的机器 |
| `reset_script_stage.py` / `reset_episodes.py` | 重跑某一集或某个阶段 |
| `delete_all_projects.py` | 删掉所有项目（测试用） |
| `repair_status.py` / `repair_from_disk.py` | 修了跑挂之后的阶段状态 |
| `redo_stills.py` / `regen_refs.py` / `regen_list.py` | 重出图 / 重做参考图 / 列出可重做的 |
| `clear_shots.py` / `clear_stills.py` / `clear_video_prompts.py` | 清掉某一层产物 |

## 看产出

| 工具 | 干什么 |
|---|---|
| `read_full_screenplay.py` | 整本剧本导出成 `剧本.md` |
| `read_screenplay.py` / `read_episode_plan.py` | 某一集的剧本 / 分集计划 |
| `read_book_shape.py` | 一本书有几个章、多长 |
| `peek_project.py` / `peek_episodes.py` / `peek_new_novel.py` | 项目 / 分集 / 新导入的小说的概况 |
| `measure_framing.py` | 这一集的镜头表有多少变化（景别、角度、主体、机位） |

## 检查

| 工具 | 干什么 |
|---|---|
| `check_js.mjs.py` | 页面上的 javascript 还能不能解析（node 当解析器） |
| `browser_rounds.py` | 用浏览器把控制台点十轮（画幅、技能、节点池） |
| `health_check.py` / `final_check.py` | 机器与产出的体检 |
| `llm_ping.py` | 模型通不通 |

## 看状态

| 工具 | 干什么 |
|---|---|
| `probe_machines.py` | 三台出片的机器（本地 5080、两张 3090）忙不忙、显存多少 |
| `probe_console.py` / `probe_jobs.py` / `probe_slugs.py` | 控制台的状态 / 正在跑什么 / 项目的真名 |
| `probe_comfy_error.py` | ComfyUI 那一镜为什么失败 |

## 推代码

| 工具 | 干什么 |
|---|---|
| `push_with_retry.py` | 一直推到成功（网络时通时断） |
| `push_via_working_ip.py` | 指定 GitHub 的地址推 |

## 开机器

| 工具 | 干什么 |
|---|---|
| `autostart.ps1` | 把这套东西拉起来（ComfyUI + 控制台）；`-Restart` 是重启，`-Status` 是看状态 |
| `install_autostart.ps1` | 装开机自启的计划任务（要管理员） |
| `e2e_autostart.ps1` | 自启的端到端检查 |
| `check_system_path.ps1` / `card_health.sh` / `start_local_stack.ps1` | PATH、显卡、起本地这一套 |
| `make_music_library.py` | 配乐库（配置里指着它） |
| `widget_fields.json` | 页面部件的字段表 |
