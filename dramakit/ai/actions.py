"""Natural language -> structured, whitelisted actions.

The Brain (main tier) reads a free-text instruction like "把第3集重做成卡通风"
or "只生成配音和字幕" and returns a strict JSON action. Nothing here executes
on its own: `parse()` only produces a plan the UI/CLI shows to the user, and
`execute()` runs an already-approved plan. Destructive or expensive actions are
flagged `needs_confirm` so the front-end can gate them behind an explicit OK.

Whitelist philosophy: the model may only choose a `kind` from ACTION_SPEC and
may only fill the parameters that kind declares. Anything else is rejected and
falls back to a `search` (the safest useful default) or an `unknown` reply.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..config import Config
from ..models import Status
from ..pipeline import make_context, run_pipeline
from ..pipeline.runner import ORDER
from ..project import ProjectStore

log = logging.getLogger("dramakit.ai.actions")

# kind -> spec: title, params, whether it costs money/time or destroys data.
ACTION_SPEC: dict[str, dict] = {
    "run_pipeline": {
        "title": "运行流水线",
        "params": ["project", "episodes", "stages", "overrides"],
        "needs_confirm": True,       # spends GPU/API time
        "destructive": False,
    },
    "regenerate_shot": {
        "title": "重做某个分镜",
        "params": ["project", "episodes", "shot_ref", "overrides"],
        "needs_confirm": True,
        "destructive": False,
    },
    "set_art_style": {
        "title": "改画风/艺术方向",
        "params": ["project", "overrides"],
        "needs_confirm": True,
        "destructive": False,
    },
    "search": {
        "title": "检索资产",
        "params": ["project", "query"],
        "needs_confirm": False,
        "destructive": False,
    },
    "reindex": {
        "title": "重建目录/打标签",
        "params": ["project", "with_ai"],
        "needs_confirm": False,
        "destructive": False,
    },
    "export": {
        "title": "导出成片清单",
        "params": ["project", "episodes"],
        "needs_confirm": False,
        "destructive": False,
    },
}

STAGE_ALIASES = {
    "配音": "voice", "语音": "voice", "台词": "voice",
    "字幕": "subtitle", "画面": "visual", "出图": "visual", "视频": "visual",
    "配乐": "music", "音乐": "music", "合成": "compose", "成片": "compose",
    "分镜": "storyboard", "脚本": "script", "分段": "segment", "分集": "segment",
    "提示词": "promptgen", "分析": "analyze", "导入": "ingest",
}


def _norm_stages(raw) -> list[str]:
    out: list[str] = []
    for s in (raw or []):
        s = str(s).strip()
        if not s:
            continue
        s = STAGE_ALIASES.get(s, s)
        if s in ORDER and s not in out:
            out.append(s)
    return [s for s in ORDER if s in out]


class Action:
    """A parsed, validated action plan."""

    def __init__(self, kind: str, params: dict, *, needs_confirm: bool,
                 title: str, confirm_msg: str = "", note: str = ""):
        self.kind = kind
        self.params = params
        self.needs_confirm = needs_confirm
        self.title = title
        self.confirm_msg = confirm_msg
        self.note = note

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "title": self.title, "params": self.params,
            "needs_confirm": self.needs_confirm, "confirm_msg": self.confirm_msg,
            "note": self.note,
        }

    def __repr__(self) -> str:
        return f"<Action {self.kind} {self.params}>"


def _spec(kind: str) -> dict:
    return ACTION_SPEC.get(kind, {"title": kind, "params": [],
                                  "needs_confirm": True, "destructive": False})


def _build(kind: str, raw: dict, projects: list[str]) -> Action:
    spec = _spec(kind)
    allowed = spec["params"]
    params: dict = {}

    # project: accept a name or slug; default to the only/most recent project
    proj = str(raw.get("project") or "").strip()
    if not proj and projects:
        proj = projects[0]
    if proj:
        params["project"] = proj

    if "episodes" in allowed:
        eps = raw.get("episodes") or []
        if isinstance(eps, (int, str)):
            eps = [eps]
        params["episodes"] = sorted({int(e) for e in eps if str(e).strip().isdigit()})
    if "stages" in allowed:
        params["stages"] = _norm_stages(raw.get("stages"))
    if "overrides" in allowed and isinstance(raw.get("overrides"), dict):
        params["overrides"] = raw["overrides"]
    if "query" in allowed:
        params["query"] = str(raw.get("query") or "").strip()
    if "shot_ref" in allowed:
        params["shot_ref"] = str(raw.get("shot_ref") or "").strip()
    if "with_ai" in allowed:
        params["with_ai"] = bool(raw.get("with_ai", True))

    confirm_msg = str(raw.get("confirm_msg") or "").strip() or _default_confirm(kind, params)
    return Action(kind, params, needs_confirm=spec["needs_confirm"],
                  title=spec["title"], confirm_msg=confirm_msg,
                  note=str(raw.get("note") or "").strip())


def _default_confirm(kind: str, params: dict) -> str:
    p = params
    if kind == "run_pipeline":
        eps = f"第{','.join(map(str, p.get('episodes', [])))}集" if p.get("episodes") else "全部集"
        st = ",".join(p.get("stages", [])) or "全部阶段"
        return f"将对《{p.get('project','')}》的{eps}运行阶段：{st}。会消耗算力/API额度。"
    if kind == "regenerate_shot":
        return f"将重做《{p.get('project','')}》分镜 {p.get('shot_ref','')}。"
    if kind == "set_art_style":
        return f"将修改《{p.get('project','')}》的艺术方向：{p.get('overrides',{})}。"
    if kind == "search":
        return f"检索：{p.get('query','')}"
    if kind == "reindex":
        return f"重建《{p.get('project','')}》的资产目录并打标签。"
    if kind == "export":
        return f"导出《{p.get('project','')}》的成片清单。"
    return "执行该动作。"


def parse(brain, instruction: str, *, projects: Optional[list[str]] = None,
          current_project: str = "") -> Action:
    """Map a free-text instruction to a validated Action plan (no execution)."""
    projects = projects or []
    spec_lines = []
    for k, s in ACTION_SPEC.items():
        spec_lines.append(f"- {k}（{s['title']}）: 参数 {s['params']}")
    sys = (
        "你是短剧工厂的动作解析器。把用户的中文指令映射成一个白名单动作，只输出 JSON。\n"
        "可选动作:\n" + "\n".join(spec_lines) + "\n"
        "输出格式: {\"kind\": \"动作名\", \"project\": \"项目名或空\", "
        "\"episodes\": [集号数字], \"stages\": [\"voice\",\"subtitle\"...], "
        "\"overrides\": {可选的 art_direction/compose 覆盖，如 {\"style\":\"卡通风\"}}, "
        "\"query\": \"检索词\", \"shot_ref\": \"分镜id\", \"with_ai\": true, "
        "\"confirm_msg\": \"一句中文，向用户说明将发生什么\"}\n"
        "规则: kind 必须是白名单之一；只填该动作支持的参数；阶段名用英文规范名"
        f"（{','.join(ORDER)}）或常见中文别名；无法归类时 kind 用 \"search\" 并把原话放 query。"
    )
    ctx = f"可用项目: {projects or '（暂无）'}\n当前项目: {current_project or '（无）'}\n"
    out = brain.json(sys, ctx + "用户指令: " + instruction, role="actions", temperature=0.1)

    if not isinstance(out, dict):
        return Action("search", {"query": instruction}, needs_confirm=False,
                      title="检索资产", confirm_msg=f"检索：{instruction}",
                      note="无法解析为具体动作，已回退为检索。")
    kind = str(out.get("kind") or "search").strip()
    if kind not in ACTION_SPEC:
        kind = "search"
        out["query"] = out.get("query") or instruction
    if not out.get("project") and current_project:
        out["project"] = current_project
    return _build(kind, out, projects)


# --------------------------------------------------------------------------- #
# Execution (only called on an approved plan)
# --------------------------------------------------------------------------- #
def execute(action: Action, cfg: Config, *, projects_root="projects",
            catalog=None) -> dict:
    """Run an approved action. Returns a JSON-serializable result dict."""
    kind = action.kind
    p = action.params
    if kind == "search":
        return _do_search(cfg, p, catalog)
    if kind == "reindex":
        return _do_reindex(cfg, p, projects_root, catalog)

    store = _open(p.get("project", ""), projects_root)
    if store is None:
        return {"ok": False, "error": f"找不到项目: {p.get('project','')}"}

    if kind == "run_pipeline":
        return _do_run(cfg, store, p)
    if kind == "regenerate_shot":
        return _do_regen_shot(cfg, store, p)
    if kind == "set_art_style":
        return _do_set_style(cfg, store, p)
    if kind == "export":
        return _do_export(store, p)
    return {"ok": False, "error": f"未知动作: {kind}"}


def _open(project: str, projects_root) -> Optional[ProjectStore]:
    if not project:
        return None
    from pathlib import Path
    cands = [Path(project), Path(projects_root) / project]
    for c in cands:
        if (c / "project.json").exists():
            return ProjectStore.open(c)
    return None


def _apply_overrides(cfg: Config, overrides: dict) -> None:
    """Apply the safe compose subset of overrides. Art-direction overrides are
    applied directly to the project (see _do_run), not to cfg."""
    if not isinstance(overrides, dict):
        return
    comp = overrides.get("compose") or {}
    for k in ("width", "height", "fps", "transition", "motion_effect", "burn_subtitles"):
        if k in comp:
            setattr(cfg.compose, k, comp[k])


def _do_run(cfg: Config, store: ProjectStore, p: dict) -> dict:
    _apply_overrides(cfg, p.get("overrides", {}))
    # art-direction overrides live on the project, not cfg
    art_over = (p.get("overrides", {}) or {}).get("art_direction") or {}
    if art_over:
        proj = store.load()
        for k, v in art_over.items():
            if hasattr(proj.art_direction, k):
                setattr(proj.art_direction, k, v)
        store.save(proj)
    if p.get("episodes"):
        cfg.pipeline.only_episodes = p["episodes"]
    stages = p.get("stages") or cfg.pipeline.stages_enabled
    ctx = make_context(cfg, store)
    res = run_pipeline(ctx, stages=stages)
    return {"ok": True, "project": store.root.name, "stages": stages,
            "results": {k: str(v)[:200] for k, v in res.items()}}


def _do_regen_shot(cfg: Config, store: ProjectStore, p: dict) -> dict:
    ref = p.get("shot_ref", "")
    proj = store.load()
    hit = None
    for ep in proj.episodes:
        if p.get("episodes") and ep.index not in p["episodes"]:
            continue
        for sc in ep.scenes:
            for sh in sc.shots:
                if sh.id == ref:
                    hit = (ep, sc, sh)
    if not hit:
        return {"ok": False, "error": f"找不到分镜: {ref}"}
    ep, sc, sh = hit
    sh.status = Status.PENDING
    sh.image_path = ""
    sh.video_path = ""
    store.save(proj)
    cfg.pipeline.only_episodes = [ep.index]
    ctx = make_context(cfg, store)
    res = run_pipeline(ctx, stages=["visual"])
    return {"ok": True, "shot": ref, "episode": ep.index,
            "results": {k: str(v)[:200] for k, v in res.items()}}


def _do_set_style(cfg: Config, store: ProjectStore, p: dict) -> dict:
    art_over = (p.get("overrides", {}) or {}).get("art_direction") \
        or (p.get("overrides", {}) or {})
    proj = store.load()
    changed = {}
    for k, v in art_over.items():
        if hasattr(proj.art_direction, k):
            setattr(proj.art_direction, k, v)
            changed[k] = v
    store.save(proj)
    return {"ok": True, "project": store.root.name, "changed": changed}


def _do_export(store: ProjectStore, p: dict) -> dict:
    proj = store.load()
    eps = []
    for ep in proj.episodes:
        if p.get("episodes") and ep.index not in p["episodes"]:
            continue
        eps.append({"index": ep.index, "title": ep.title,
                    "video": ep.video_path, "cover": ep.cover_path,
                    "subtitle": ep.subtitle_path, "status": _sv(ep.status)})
    return {"ok": True, "project": store.root.name, "episodes": eps}


def _sv(s) -> str:
    return s.value if isinstance(s, Status) else str(s or "")


def _do_search(cfg: Config, p: dict, catalog) -> dict:
    if catalog is None:
        return {"ok": False, "error": "目录未初始化"}
    from .brain import Brain
    brain = Brain(cfg)
    q = p.get("query", "")
    filt = brain.expand_query(q) if q else {"keywords": [], "tags": [], "category": "", "kinds": []}
    rows = catalog.search(project=p.get("project") or None,
                          keywords=filt.get("keywords"), tags=filt.get("tags"),
                          category=filt.get("category", ""),
                          kinds=filt.get("kinds") or None,
                          limit=cfg.ai.max_search_results)
    return {"ok": True, "query": q, "filters": filt, "count": len(rows), "results": rows}


def _do_reindex(cfg: Config, p: dict, projects_root, catalog) -> dict:
    if catalog is None:
        return {"ok": False, "error": "目录未初始化"}
    store = _open(p.get("project", ""), projects_root)
    if store is None:
        return {"ok": False, "error": f"找不到项目: {p.get('project','')}"}
    from .brain import Brain
    brain = Brain(cfg)
    with_ai = bool(p.get("with_ai", True)) and brain.probe()["main"]["ok"]
    res = catalog.reindex_project(store, with_ai=with_ai, brain=brain if with_ai else None)
    return {"ok": True, **res}
