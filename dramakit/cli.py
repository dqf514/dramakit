"""DramaKit CLI.

Typical flow:
  dj doctor                                  # check ffmpeg / ComfyUI / LLM / TTS
  dj new 我的短剧 --source novel.txt          # create a project
  dj run 我的短剧                             # run the whole pipeline
  dj run 我的短剧 --stages voice,subtitle,compose   # re-run part of it
  dj status 我的短剧                          # see progress
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import Config
from .models import Status
from .pipeline import ORDER, Context, make_context, run_pipeline
from .project import ProjectStore
from .providers import Providers
from .utils.logging import setup_logging

app = typer.Typer(add_completion=False, help="DramaKit — 小说转多集竖屏短剧工厂")
console = Console()

DEFAULT_CONFIG = "config/default.yaml"


def _find_config(path: Optional[str]) -> Optional[Path]:
    cands = []
    if path:
        cands.append(Path(path))
    cands += [Path(DEFAULT_CONFIG), Path("default.yaml"),
              Path(__file__).parent.parent / DEFAULT_CONFIG]
    for c in cands:
        if c.exists():
            return c
    return None


def _open_store(project: str) -> ProjectStore:
    p = Path(project)
    if not p.exists():
        # try under a projects/ dir
        alt = Path("projects") / project
        if alt.exists():
            p = alt
    if not p.exists():
        console.print(f"[red]找不到项目:[/red] {project}")
        raise typer.Exit(1)
    return ProjectStore.open(p)


def _parse_stages(s: Optional[str]) -> Optional[list[str]]:
    if not s:
        return None
    return [x.strip() for x in s.split(",") if x.strip()]


def _parse_eps(s: Optional[str]) -> list[int]:
    if not s:
        return []
    out = []
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


# --------------------------------------------------------------------------- #
@app.command()
def doctor(config: Optional[str] = typer.Option(None, "--config", "-c", help="配置文件路径"),
           ping_comfy: bool = typer.Option(True, help="是否测试 ComfyUI 连接")):
    """检查运行环境：ffmpeg / LLM / TTS / ComfyUI / 音乐。"""
    cfg = Config.load(_find_config(config))
    from .media import ffmpeg as ff
    console.print("[bold]DramaKit 环境自检[/bold]")
    console.print(f"  ffmpeg/ffprobe : {'[green]OK[/green]' if ff.check_available() else '[red]缺失[/red]'}")
    # LLM
    try:
        prov = Providers(cfg)
        r = prov.llm.complete("You are a test.", "Reply with the single word: OK",
                              max_tokens=10)
        console.print(f"  LLM ({cfg.llm.model}) : [green]OK[/green] → {r.text.strip()[:20]!r}")
    except Exception as e:  # noqa: BLE001
        console.print(f"  LLM ({cfg.llm.model}) : [red]失败[/red] {str(e)[:80]}")
    # TTS
    try:
        import tempfile
        prov = Providers(cfg)
        with tempfile.TemporaryDirectory() as d:
            out = str(Path(d) / "t.mp3")
            dur = prov.tts.synthesize("测试配音", "zh-CN-YunxiNeural", out)
            console.print(f"  TTS ({cfg.tts.provider}) : [green]OK[/green] {dur:.2f}s")
    except Exception as e:  # noqa: BLE001
        console.print(f"  TTS ({cfg.tts.provider}) : [red]失败[/red] {str(e)[:80]}")
    # ComfyUI
    if cfg.comfyui.enabled and ping_comfy:
        from .providers.comfyui import ComfyUIClient
        c = ComfyUIClient(cfg.comfyui, Path("."))
        ok = c.ping()
        console.print(f"  ComfyUI ({cfg.comfyui.base_url}) : "
                      f"{'[green]OK[/green]' if ok else '[yellow]不可达[/yellow]'}")
    # music
    console.print(f"  音乐 ({cfg.music.provider}) : 已配置")


@app.command()
def new(name: str = typer.Argument(..., help="项目名"),
        source: Optional[str] = typer.Option(None, "--source", "-s", help="小说/剧本文件"),
        config: Optional[str] = typer.Option(None, "--config", "-c"),
        output_dir: Optional[str] = typer.Option(None, "--out", "-o")):
    """创建新项目（可选同时导入源文件）。"""
    cfg = Config.load(_find_config(config))
    outdir = output_dir or cfg.pipeline.output_dir
    store = ProjectStore.create(outdir, name, source)
    store.save(store.load())
    console.print(f"[green]已创建项目:[/green] {store.root}")
    if source:
        console.print(f"  源文件: {source}")
    console.print(f"  下一步: [cyan]dj run {store.root}[/cyan]")


@app.command()
def run(project: str = typer.Argument(..., help="项目目录或名称"),
        source: Optional[str] = typer.Option(None, "--source", "-s", help="小说/剧本文件"),
        config: Optional[str] = typer.Option(None, "--config", "-c"),
        stages: Optional[str] = typer.Option(None, "--stages", help="逗号分隔，如 voice,compose"),
        stop_after: Optional[str] = typer.Option(None, "--stop-after"),
        episodes: Optional[str] = typer.Option(None, "--episodes", "-e", help="如 1,3,5-8"),
        no_resume: bool = typer.Option(False, "--no-resume"),
        fail_fast: bool = typer.Option(False, "--fail-fast")):
    """运行整条流水线（或指定阶段）。"""
    store = _open_store(project)
    cfg = Config.load(_find_config(config))
    setup_logging(cfg.pipeline.verbose, store.log_path("pipeline"))
    if stop_after:
        cfg.pipeline.stop_after = stop_after
    if no_resume:
        cfg.pipeline.resume = False
    if fail_fast:
        cfg.pipeline.fail_fast = True
    eps = _parse_eps(episodes)
    if eps:
        cfg.pipeline.only_episodes = eps

    ctx = make_context(cfg, store)
    stage_list = _parse_stages(stages) or cfg.pipeline.stages_enabled
    console.print(f"[bold]▶ 运行项目[/bold] {store.root.name} | 阶段: {','.join(stage_list)}")
    results = run_pipeline(ctx, source_file=source, stages=stage_list)

    tbl = Table(title="运行结果")
    tbl.add_column("阶段"); tbl.add_column("结果")
    for k, v in results.items():
        tbl.add_row(k, str(v))
    console.print(tbl)
    _print_status(ctx)


@app.command()
def status(project: str = typer.Argument(...),
           config: Optional[str] = typer.Option(None, "--config", "-c")):
    """查看项目进度。"""
    store = _open_store(project)
    cfg = Config.load(_find_config(config))
    ctx = make_context(cfg, store)
    _print_status(ctx)


def _print_status(ctx: Context):
    proj = ctx.project
    console.print(f"\n[bold]《{proj.meta.title or proj.meta.name}》[/bold] "
                  f"[dim]{proj.art_direction.genre}[/dim]")
    console.print(f"  角色 {len(proj.characters)} | 集数 {len(proj.episodes)} | 镜头 {proj.total_shots}")
    if proj.episodes:
        tbl = Table(title="分集进度")
        for col in ["集", "标题", "场", "镜", "画面", "配音", "字幕", "配乐", "成片"]:
            tbl.add_column(col)
        for ep in proj.episodes[:60]:
            shots = ep.total_shots
            with_vis = sum(1 for s in ep.scenes for sh in s.shots if sh.has_visual)
            voiced = sum(1 for s in ep.scenes for l in s.lines
                         if l.status == Status.DONE)
            lines = sum(len(s.lines) for s in ep.scenes)
            tbl.add_row(
                str(ep.index), ep.title[:12],
                str(len(ep.scenes)), str(shots),
                f"{with_vis}/{shots}", f"{voiced}/{lines}",
                "✓" if ep.subtitle_path else "·",
                "✓" if ep.bgm_path else "·",
                "[green]✓[/green]" if ep.video_path else "·",
            )
        console.print(tbl)
    # stage status
    if proj.stage_status:
        console.print("  阶段: " + "  ".join(
            f"{k}={v}" for k, v in proj.stage_status.items()))


@app.command()
def voices(config: Optional[str] = typer.Option(None, "--config", "-c"),
           filter_zh: bool = typer.Option(True, "--zh-only")):
    """列出可用 TTS 音色（edge）。"""
    cfg = Config.load(_find_config(config))
    from .providers.tts import build_tts
    tts = build_tts(cfg.tts)
    vs = tts.list_voices()
    if not vs:
        console.print("[yellow]当前 provider 不支持列出音色。[/yellow]")
        return
    for v in vs:
        console.print(v)


@app.command(name="config")
def show_config(config: Optional[str] = typer.Option(None, "--config", "-c"),
                dump: Optional[str] = typer.Option(None, "--dump", help="导出到该 YAML 路径"),
                init: bool = typer.Option(False, "--init", help="生成默认 config/default.yaml")):
    """查看/导出/初始化配置。"""
    cfg = Config.load(_find_config(config))
    if init or dump:
        target = Path(dump or DEFAULT_CONFIG)
        cfg.dump_yaml(target)
        console.print(f"[green]已写出配置:[/green] {target}")
        return
    import yaml
    console.print(yaml.safe_dump(cfg.model_dump(), allow_unicode=True, sort_keys=False))


@app.command()
def clean(project: str = typer.Argument(...),
          what: str = typer.Option("tmp", help="tmp | intermediates | all-assets")):
    """清理中间产物。"""
    import shutil
    store = _open_store(project)
    root = store.root
    if what in ("tmp", "all"):
        shutil.rmtree(root / "tmp", ignore_errors=True)
        console.print("[green]已清理 tmp/[/green]")
    if what in ("intermediates", "all"):
        for d in ("images", "video"):
            shutil.rmtree(root / d, ignore_errors=True)
            (root / d).mkdir(exist_ok=True)
        console.print("[green]已清理 images/ video/[/green]")


@app.command(name="comfy-test")
def comfy_test(config: Optional[str] = typer.Option(None, "--config", "-c"),
               url: Optional[str] = typer.Option(None, "--url", help="临时覆盖 ComfyUI 地址"),
               gen: bool = typer.Option(False, "--gen", help="真实试生成一张图并计时"),
               out: str = typer.Option("projects/_comfy_test/sample.png", "--out")):
    """远程 ComfyUI 对接自检：连通性 / GPU / 工作流校验 / 可选试生成。"""
    cfg = Config.load(_find_config(config))
    if url:
        cfg.comfyui.base_url = url
    cfg.comfyui.enabled = True
    from .providers.comfyui import ComfyUIClient
    c = ComfyUIClient(cfg.comfyui, Path("."))

    console.print(f"[bold]ComfyUI 对接自检[/bold] → {cfg.comfyui.base_url} "
                  f"(auth={cfg.comfyui.auth})")

    # 1) connectivity
    if not c.ping():
        console.print("[red]✗ 连不上服务器。[/red] 请检查：")
        console.print("  · ComfyUI 是否以 [cyan]--listen 0.0.0.0[/cyan] 启动")
        console.print("  · 防火墙/安全组是否放行该端口")
        console.print("  · base_url 的 IP/端口是否正确；浏览器能否直接打开该地址")
        console.print("  · 若走 Nginx 反代，auth 是否配对（见 deploy/comfyui-server.md）")
        raise typer.Exit(1)
    console.print("[green]✓ 连通正常[/green]")

    # 2) system stats
    try:
        st = c.system_stats()
        sysinfo = st.get("system", {})
        devices = sysinfo.get("devices", [])
        cver = sysinfo.get("comfyui_version", "?")
        tver = sysinfo.get("torch_version", "?")
        console.print(f"  ComfyUI 版本 : {cver}")
        console.print(f"  PyTorch      : {tver}")
        for d in devices:
            vram = d.get("vram_total", 0) / (1024**3)
            free = d.get("vram_free", 0) / (1024**3)
            gname = d.get("name", "?")
            console.print(f"  GPU          : {gname} | VRAM {vram:.1f}GB (空闲 {free:.1f}GB)")
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]  读取 system_stats 失败: {e}[/yellow]")

    # 3) queue
    try:
        q = c.queue_info()
        console.print(f"  队列         : 运行中 {q['running']} | 等待 {q['pending']}")
    except Exception:  # noqa: BLE001
        pass

    # 4) checkpoints
    try:
        cks = c.list_checkpoints()
        if cks:
            cur = cfg.comfyui.checkpoint
            mark = "[green]✓[/green]" if cur in cks else "[red]✗ 配置的这个不在服务器上[/red]"
            console.print(f"  当前 checkpoint: {cur} {mark}")
            if cur not in cks:
                avail = ", ".join(cks[:12])
                console.print(f"    服务器可用: {avail}")
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]  读取 checkpoint 列表失败: {e}[/yellow]")

    # 5) workflow validation
    for label, rel, nmap, kind in (
            ("出图 t2i", cfg.comfyui.t2i_workflow, cfg.comfyui.t2i_nodes, "t2i"),
            ("图生视频 i2v", cfg.comfyui.i2v_workflow, cfg.comfyui.i2v_nodes, "i2v")):
        rep = c.validate_workflow(rel, nmap, kind)
        nnodes = rep.get("nodes", 0)
        head = f"  [{label}] {Path(rel).name} ({nnodes} 节点)"
        if rep["ok"]:
            console.print(f"{head} [green]✓ 校验通过[/green]")
        else:
            console.print(f"{head} [red]✗ 有问题[/red]")
            for p in rep["problems"]:
                console.print(f"      - {p}")
        for w in rep.get("warnings", []):
            console.print(f"      [yellow]! {w}[/yellow]")
        inferred = rep.get("inferred") or {}
        if inferred:
            console.print("      自动识别: " + " · ".join(
                f"{k}={v}" for k, v in inferred.items()))

    # 6) optional real generation
    if gen:
        import time as _t
        console.print("\n[yellow]试生成一张 768x1344 图…[/yellow]")
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        t0 = _t.time()
        neg = ("lowres, bad anatomy, extra fingers, text, watermark, logo, blurry, "
               "distorted face, deformed hands")
        try:
            c.generate_image(
                prompt="vertical composition 9:16, a cinematic portrait of a young man, "
                       "city night background, dramatic lighting, highly detailed",
                negative=neg,
                width=768, height=1344, seed=-1,
                steps=min(cfg.comfyui.steps, 20), cfg=cfg.comfyui.cfg, out_path=out)
            dt = _t.time() - t0
            sz = Path(out).stat().st_size / 1024
            console.print(f"[green]✓ 生成成功[/green] {dt:.1f}s → {out} ({sz:.0f} KB)")
            console.print("  全流程画面环节已打通，可以 `dj run <项目>` 了。")
        except Exception as e:  # noqa: BLE001
            console.print(f"[red]✗ 试生成失败:[/red] {str(e)[:300]}")
            console.print("  多半是 checkpoint 名或节点ID对不上，见上方校验与 deploy 文档。")
            raise typer.Exit(1)


@app.command(name="nodes")
def nodes_cmd(
    action: str = typer.Argument("list", help="list | check | sync"),
    name: str = typer.Argument("", help="节点名（sync 时指定；留空=全部）"),
    config: Optional[str] = typer.Option(None, "--config", "-c"),
    models_dir: str = typer.Option("", "--models-dir", help="本地 ComfyUI models 目录（同步源）"),
):
    """节点池：查看/自检 ComfyUI 节点，并同步缺失的模型文件。

    工作流即清单：扫描 config/comfyui/*.json 里的模型加载节点，
    自动得出每个节点需要哪些模型文件，缺什么就补什么。
    """
    from .providers.nodes import (check_node, manifest, nodes_from_config,
                                  sync_models, SyncReport)
    cfg = Config.load(_find_config(config))
    if models_dir:
        cfg.comfyui.models_dir = models_dir
    root = Path(".")
    refs = manifest(cfg, root)
    fleet = nodes_from_config(cfg)

    def _one(spec):
        h = check_node(spec, refs)
        if not h.online:
            console.print(f"[red]✗[/red] {spec.name:14s} {spec.base_url}  "
                          f"离线（{h.error}）")
        else:
            miss = (f"  缺 {len(h.missing)} 个模型" if h.missing else "  模型齐全")
            color = "yellow" if h.missing else "green"
            console.print(f"[{color}]●[/{color}] {spec.name:14s} {spec.base_url}  "
                          f"v{h.version}  {h.device}  "
                          f"显存 {h.vram_free/1024**3:.1f}/{h.vram_total/1024**3:.1f}G"
                          f"{miss}")
            for m in h.missing[:12]:
                console.print(f"    [yellow]缺[/yellow] {m}")
        return h

    if action in ("list", "check"):
        console.print(f"[bold]ComfyUI 节点池[/bold]（清单来自工作流，共 "
                      f"{len(refs)} 个模型文件）")
        for spec in fleet:
            if not spec.enabled:
                continue
            _one(spec)
        if action == "list":
            console.print("\n同步模型：dj nodes sync <名字>   "
                          "（节点需在 config/default.yaml 的 comfyui.nodes 里配置）")
        return

    if action == "sync":
        targets = [s for s in fleet if s.enabled and (not name or s.name == name)]
        if not targets:
            console.print(f"[red]没有匹配的节点:[/red] {name or '(全部)'}")
            raise typer.Exit(1)
        for spec in targets:
            if spec.transfer == "none":
                console.print(f"[yellow]跳过 {spec.name}:[/yellow] 未配置传输方式"
                              f"（comfyui.nodes[].transfer: shared / scp）")
                continue
            h = check_node(spec, refs)
            if not h.online:
                console.print(f"[red]✗ {spec.name} 离线，跳过[/red]")
                continue
            todo = [r for r in refs if r.rel in set(h.missing)]
            if not todo:
                console.print(f"[green]✓[/green] {spec.name} 模型已齐全")
                continue
            report = SyncReport(node=spec.name)
            total = sum(r.size for r in todo)
            console.print(f"[bold]同步 {spec.name}[/bold]  {len(todo)} 个文件 / "
                          f"{total/1024**3:.2f} GB")

            def _upd():
                d = report.to_dict()
                bar_len = 24
                filled = int(bar_len * d["percent"] / 100)
                bar = "█" * filled + "░" * (bar_len - filled)
                console.print(f"  {bar} {d['percent']:5.1f}%  "
                              f"{d['bytes_done']/1024**3:.2f}/{d['bytes_total']/1024**3:.2f}G  "
                              f"{d['speed_mb']:.1f}MB/s  ETA {d['eta']:.0f}s  "
                              f"{d['file']}", end="\r")

            sync_models(spec, todo, report, _upd)
            console.print()
            if report.failed:
                for f in report.failed:
                    console.print(f"  [red]✗[/red] {f}")
            console.print(f"[green]✓[/green] {spec.name} 同步完成："
                          f"{report.files_done}/{report.files_total} 个文件")
        return

    console.print(f"[red]未知操作:[/red] {action}（list | check | sync）")
    raise typer.Exit(1)


# --------------------------------------------------------------------------- #
# AI-native layer: serve / setup / ai / tag / search
# --------------------------------------------------------------------------- #
@app.command()
def serve(config: Optional[str] = typer.Option(None, "--config", "-c"),
          host: Optional[str] = typer.Option(None, "--host", help="默认 127.0.0.1；局域网访问填 0.0.0.0"),
          port: Optional[int] = typer.Option(None, "--port", "-p"),
          no_browser: bool = typer.Option(False, "--no-browser", help="不自动打开浏览器")):
    """启动本地 Web 控制台（项目管理 / 一键配置 / AI 检索 / AI 动作）。"""
    cfg = Config.load(_find_config(config))
    from .web import serve as _serve
    _serve(cfg, config_path=_find_config(config), host=host, port=port,
           open_browser=(False if no_browser else None))


@app.command()
def setup(intent: str = typer.Argument("", help="一句话描述你想要的短剧"),
          config: Optional[str] = typer.Option(None, "--config", "-c"),
          preset: str = typer.Option("", "--preset", help="题材预设 id，见 --list-templates"),
          chips: str = typer.Option("", "--chips", help="逗号分隔的需求 chip id"),
          extra: str = typer.Option("", "--extra", help="额外自由要求"),
          out: str = typer.Option("config/default.yaml", "--out", help="写出的 YAML 路径"),
          dry: bool = typer.Option(False, "--dry-run", help="只显示，不写文件"),
          list_templates: bool = typer.Option(False, "--list-templates", help="列出所有模板/chip")):
    """AI 一键配置：探测环境 + 依据意图与模板生成完整配置。"""
    from .ai import autoconfig
    from .ai.templates import all_templates
    if list_templates:
        t = all_templates()
        console.print("[bold]题材预设:[/bold]")
        for p in t["genre_presets"]:
            console.print(f"  [cyan]{p['id']}[/cyan]  {p['label']}  [dim]{p['genre']}·{p.get('pacing','')}·{p.get('audience','')}[/dim]")
        console.print("\n[bold]需求 chip:[/bold]")
        for group, items in t["requirement_chips"].items():
            ids = ", ".join(f"[cyan]{c['id']}[/cyan]({c['label']})" for c in items)
            console.print(f"  {group}: {ids}")
        console.print("\n[bold]意图示例:[/bold]")
        for e in t["intent_examples"]:
            console.print(f"  · {e}")
        return

    cfg = Config.load(_find_config(config))
    chip_list = [c.strip() for c in chips.split(",") if c.strip()]
    console.print("[bold]AI 一键配置[/bold]")
    with console.status("探测环境（ffmpeg / 本地大模型 / ComfyUI / 音色 / 乐库）…"):
        report = autoconfig.probe(cfg)
    _print_probe(report)
    if dry:
        ov = autoconfig.generate(cfg, intent, genre_preset=preset, chips=chip_list,
                                 extra=extra, probe_report=report)
        import yaml
        console.print("\n[bold]将写入的覆盖参数（--dry-run，未落盘）:[/bold]")
        console.print(yaml.safe_dump(ov, allow_unicode=True, sort_keys=False))
        return
    with console.status("AI 正在生成完整配置…"):
        res = autoconfig.setup(cfg, intent, genre_preset=preset, chips=chip_list,
                               extra=extra, out_path=out, probe_report=report)
    tag = "[green]AI 生成[/green]" if res["used_llm"] else "[yellow]模板规则生成（未连到大模型）[/yellow]"
    console.print(f"\n[green]✓ 配置已写出:[/green] {res['written']}  ({tag})")
    if res.get("art_defaults"):
        console.print(f"  新建项目将套用画风: {res['art_defaults']}")
    console.print("  下一步: [cyan]dj new 我的短剧 --source novel.txt[/cyan] 然后 [cyan]dj serve[/cyan]")


def _print_probe(rep: dict):
    ok = lambda b: "[green]OK[/green]" if b else "[red]×[/red]"  # noqa: E731
    console.print(f"  ffmpeg      : {ok(rep.get('ffmpeg'))}")
    eps = rep.get("llm_endpoints") or []
    if eps:
        for e in eps:
            ms = ", ".join(e.get("models", [])[:5]) or "?"
            console.print(f"  本地大模型  : [green]{e['name']}[/green] @ {e['base_url']} → {ms}")
    else:
        console.print("  本地大模型  : [yellow]未发现 Ollama/LMStudio[/yellow]")
    main = rep.get("llm_main") or {}
    console.print(f"  配置的主脑  : {main.get('model','?')} "
                  f"{'[green]在线[/green]' if main.get('ok') else '[red]离线[/red]'}")
    c = rep.get("comfyui") or {}
    if c.get("reachable"):
        gpus = ", ".join(f"{g.get('name')} {g.get('vram_gb')}G" for g in c.get("gpus", [])) or "?"
        console.print(f"  ComfyUI     : [green]已连接[/green] {c.get('base_url')} | {gpus}")
        cks = c.get("checkpoints") or []
        if cks:
            console.print(f"    checkpoints: {', '.join(cks[:6])}")
        console.print(f"    工作流校验 : t2i {ok(c.get('t2i_ok'))} | i2v {ok(c.get('i2v_ok'))}")
    else:
        console.print(f"  ComfyUI     : [yellow]不可达[/yellow] {c.get('base_url','')}")
    t = rep.get("tts") or {}
    console.print(f"  TTS         : {t.get('provider','?')} | {t.get('voice_count',0)} 个中文音色")
    m = rep.get("music") or {}
    console.print(f"  配乐        : {m.get('provider','?')} | 乐库 {m.get('track_count',0)} 首")


@app.command(name="tag")
def tag_cmd(project: str = typer.Argument(..., help="项目目录或名称"),
            config: Optional[str] = typer.Option(None, "--config", "-c"),
            no_ai: bool = typer.Option(False, "--no-ai", help="只重建索引，不调用大模型打标签")):
    """把项目所有资产写入目录（SQLite），并用 AI 打标签/分类。"""
    from .catalog import open_catalog
    from .ai.brain import Brain
    store = _open_store(project)
    cfg = Config.load(_find_config(config))
    cat = open_catalog(cfg, Path(cfg.pipeline.output_dir))
    brain = Brain(cfg)
    with_ai = (not no_ai) and cfg.ai.enabled and brain.probe()["main"]["ok"]
    if not with_ai and not no_ai:
        console.print("[yellow]主脑离线，改为仅重建索引（不打 AI 标签）。[/yellow]")
    with console.status("索引 + 打标签中…"):
        res = cat.reindex_project(store, with_ai=with_ai, brain=brain if with_ai else None)
    console.print(f"[green]✓ 已索引[/green] {res['project']}: {res['total']} 条  {res['counts']}")
    tags = cat.all_tags(res["project"])
    if tags:
        top = ", ".join(f"{k}({v})" for k, v in list(tags.items())[:16])
        console.print(f"  热门标签: {top}")


@app.command(name="search")
def search_cmd(query: str = typer.Argument(..., help="自然语言检索，如：夜戏里男主的特写"),
               project: Optional[str] = typer.Option(None, "--project", "-p"),
               config: Optional[str] = typer.Option(None, "--config", "-c"),
               limit: int = typer.Option(30, "--limit", "-n")):
    """AI 语义检索目录里的资产（自然语言 → 标签/类型/关键词）。"""
    from .catalog import open_catalog
    from .ai.brain import Brain
    cfg = Config.load(_find_config(config))
    cat = open_catalog(cfg, Path(cfg.pipeline.output_dir))
    brain = Brain(cfg)
    filt = brain.expand_query(query)
    kws = ", ".join(filt.get("keywords", [])) or "—"
    tgs = ", ".join(filt.get("tags", [])) or "—"
    kds = ", ".join(filt.get("kinds", [])) or "—"
    console.print(f"[dim]AI 解析 → 关键词[{kws}] 标签[{tgs}] 类型[{kds}][/dim]")
    rows = cat.search(project=project, keywords=filt.get("keywords"),
                      tags=filt.get("tags"), category=filt.get("category", ""),
                      kinds=filt.get("kinds") or None, limit=limit)
    if not rows:
        console.print("[yellow]没有匹配的资产。先 `dj tag <项目>` 建索引。[/yellow]")
        return
    tbl = Table(title=f"命中 {len(rows)} 条")
    for col in ["类型", "集", "标题", "分类", "标签", "状态"]:
        tbl.add_column(col)
    for r in rows:
        tbl.add_row(r["kind"], str(r.get("ep_index") or ""),
                    (r.get("title") or "")[:22], r.get("category", ""),
                    ", ".join((r.get("tags") or [])[:5]), r.get("status", ""))
    console.print(tbl)


@app.command(name="ai")
def ai_cmd(instruction: str = typer.Argument(..., help="自然语言指令"),
           project: Optional[str] = typer.Option(None, "--project", "-p"),
           config: Optional[str] = typer.Option(None, "--config", "-c"),
           yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认直接执行")):
    """用一句话驱动全流程：AI 解析成白名单动作，确认后执行。"""
    from .catalog import open_catalog
    from .ai.brain import Brain
    from .ai import actions
    cfg = Config.load(_find_config(config))
    cat = open_catalog(cfg, Path(cfg.pipeline.output_dir))
    brain = Brain(cfg)
    outdir = Path(cfg.pipeline.output_dir)
    slugs = [p.name for p in outdir.iterdir() if (p / "project.json").exists()] \
        if outdir.exists() else []
    act = actions.parse(brain, instruction, projects=slugs, current_project=project or "")
    console.print(f"[bold]🎯 {act.title}[/bold]" + (f"  [dim]· {act.note}[/dim]" if act.note else ""))
    console.print(f"  {act.confirm_msg}")
    if act.params:
        console.print(f"  [dim]参数: {act.params}[/dim]")
    if act.kind in ("search", "reindex", "export"):
        res = actions.execute(act, cfg, projects_root=outdir, catalog=cat)
        _print_action_result(act, res)
        return
    if act.needs_confirm and not yes:
        if not typer.confirm("  确认执行？"):
            console.print("[yellow]已取消。[/yellow]")
            return
    res = actions.execute(act, cfg, projects_root=outdir, catalog=cat)
    _print_action_result(act, res)
    slug = act.params.get("project")
    if slug and cfg.ai.auto_tag and act.kind in ("run_pipeline", "regenerate_shot", "set_art_style"):
        store = _open_store(slug)
        with_ai = cfg.ai.enabled and brain.probe()["main"]["ok"]
        cat.reindex_project(store, with_ai=with_ai, brain=brain if with_ai else None)
        console.print("[dim]  已刷新资产目录索引。[/dim]")


def _print_action_result(act, res: dict):
    if not res.get("ok", True):
        console.print(f"[red]✗ {res.get('error','失败')}[/red]")
        return
    if act.kind == "search":
        rows = res.get("results", [])
        console.print(f"[green]✓ 命中 {res.get('count', len(rows))} 条[/green]")
        tbl = Table()
        for col in ["类型", "集", "标题", "分类", "标签"]:
            tbl.add_column(col)
        for r in rows[:40]:
            tbl.add_row(r["kind"], str(r.get("ep_index") or ""),
                        (r.get("title") or "")[:22], r.get("category", ""),
                        ", ".join((r.get("tags") or [])[:5]))
        console.print(tbl)
    elif act.kind == "export":
        for e in res.get("episodes", []):
            v = "[green]✓[/green]" if e.get("video") else "·"
            console.print(f"  第{e['index']}集 {e.get('title','')} 成片{v} {e.get('video','')}")
    else:
        console.print(f"[green]✓ 完成[/green] {act.title}")
        for k, v in (res.get("results") or {}).items():
            console.print(f"  [dim]{k}: {str(v)[:100]}[/dim]")


if __name__ == "__main__":
    app()