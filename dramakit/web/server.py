"""Zero-dependency local web console server (stdlib http.server).

Design notes:
  * One ThreadingHTTPServer, a single request handler that routes by path.
  * JSON API under /api/*, media previews under /media/*, everything else
    served from web/static (the single-page console).
  * The server holds ONE Config + one Catalog, shared across requests (guarded
    by a lock). Long jobs (pipeline runs, AI setup) run inline; the browser
    shows a spinner. A background job runner keeps the UI responsive for runs.
  * Security: this binds to 127.0.0.1 by default (local only). /media paths are
    canonicalised and confined to the projects dir to prevent traversal.
"""
from __future__ import annotations

import json
import logging
import mimetypes
import threading
import traceback
import uuid
from urllib.parse import quote
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

from ..catalog import Catalog, open_catalog
from ..config import Config
from ..project import ProjectStore

log = logging.getLogger("dramakit.web")

STATIC_DIR = Path(__file__).parent / "static"


# --------------------------------------------------------------------------- #
# Shared server state
# --------------------------------------------------------------------------- #
class State:
    def __init__(self, cfg: Config, config_path: Optional[Path], projects_root: Path):
        self.lock = threading.RLock()
        self.cfg = cfg
        self.config_path = config_path
        self.projects_root = projects_root
        self.catalog: Catalog = open_catalog(cfg, projects_root)
        self.jobs: dict[str, dict] = {}
        self._brain = None

    # -- lazy brain (recreated when config changes) --
    def brain(self):
        from ..ai.brain import Brain
        if self._brain is None:
            self._brain = Brain(self.cfg)
        return self._brain

    def reload_config(self) -> None:
        with self.lock:
            self.cfg = Config.load(self.config_path)
            self.catalog = open_catalog(self.cfg, self.projects_root)
            self._brain = None

    def project_slugs(self) -> list[str]:
        if not self.projects_root.exists():
            return []
        out = []
        for p in sorted(self.projects_root.iterdir()):
            if (p / "project.json").exists():
                out.append(p.name)
        return out

    def open_store(self, slug: str) -> Optional[ProjectStore]:
        root = self.projects_root / slug
        if (root / "project.json").exists():
            return ProjectStore.open(root)
        return None

    # -- background jobs --
    def start_job(self, kind: str, fn) -> str:
        jid = uuid.uuid4().hex[:12]
        self.jobs[jid] = {"id": jid, "kind": kind, "status": "running",
                          "result": None, "error": None}

        def _wrap():
            try:
                res = fn()
                self.jobs[jid].update(status="done", result=res)
            except Exception as e:  # noqa: BLE001
                log.error("job %s failed: %s", jid, traceback.format_exc())
                self.jobs[jid].update(status="error", error=str(e)[:500])

        threading.Thread(target=_wrap, daemon=True).start()
        return jid


# --------------------------------------------------------------------------- #
# Request handler
# --------------------------------------------------------------------------- #
def _make_handler(state: State):
    class Handler(BaseHTTPRequestHandler):
        server_version = "DramaKitConsole/1.0"
        protocol_version = "HTTP/1.1"

        # ---- plumbing ----
        def log_message(self, fmt, *args):  # silence default stderr logging
            log.debug("http: " + fmt, *args)

        def _send(self, code: int, body: bytes, ctype: str,
                  extra: Optional[dict] = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _json(self, obj, code: int = 200) -> None:
            body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
            self._send(code, body, "application/json; charset=utf-8")

        def _err(self, msg: str, code: int = 400) -> None:
            self._json({"ok": False, "error": msg}, code)

        def _read_body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            raw = self.rfile.read(n)
            try:
                return json.loads(raw.decode("utf-8"))
            except ValueError:
                return {}

        # ---- routing ----
        def do_GET(self):
            u = urlparse(self.path)
            path = unquote(u.path)
            query = parse_qs(u.query)
            try:
                if path.startswith("/api/"):
                    self._route_get_api(path, query)
                elif path.startswith("/media/"):
                    self._serve_media(path[len("/media/"):])
                else:
                    self._serve_static(path)
            except Exception as e:  # noqa: BLE001
                log.error("GET %s failed: %s", path, traceback.format_exc())
                self._err(str(e), 500)

        def do_POST(self):
            u = urlparse(self.path)
            path = unquote(u.path)
            body = self._read_body()
            try:
                self._route_post_api(path, body)
            except Exception as e:  # noqa: BLE001
                log.error("POST %s failed: %s", path, traceback.format_exc())
                self._err(str(e), 500)

        # ---- GET /api ----
        def _route_get_api(self, path: str, query: dict):
            if path == "/api/state":
                return self._json(self._api_state())
            if path == "/api/health":
                return self._json(self._api_health())
            if path == "/api/templates":
                from ..ai.templates import all_templates
                return self._json({"ok": True, **all_templates()})
            if path == "/api/projects":
                return self._json({"ok": True, "projects": self._api_projects()})
            if path.startswith("/api/projects/"):
                slug = path[len("/api/projects/"):]
                return self._json(self._api_project_detail(slug))
            if path == "/api/search":
                q = (query.get("q") or [""])[0]
                slug = (query.get("project") or [""])[0]
                return self._json(self._api_search(q, slug))
            if path == "/api/tags":
                slug = (query.get("project") or [""])[0] or None
                return self._json({"ok": True, "tags": state.catalog.all_tags(slug)})
            if path == "/api/jobs":
                jid = (query.get("id") or [""])[0]
                j = state.jobs.get(jid)
                return self._json({"ok": bool(j), "job": j})
            if path == "/api/config":
                return self._json({"ok": True,
                                   "config": json.loads(state.cfg.model_dump_json())})
            if path == "/api/config/llm":
                return self._json(self._api_config_llm_get())
            if path == "/api/config/models":
                return self._json(self._api_config_models_get())
            if path == "/api/config/production":
                return self._json(self._api_config_production_get())
            if path == "/api/assets":
                slug = (query.get("project") or [""])[0]
                kind = (query.get("kind") or [""])[0]
                if not slug:
                    return self._err("project required", 400)
                rows = state.catalog.get_project_assets(slug, kind or None)
                for r in rows:
                    if r.get("path"):
                        r["media_url"] = _media_url(slug, r["path"])
                return self._json({"ok": True, "assets": rows})
            if path == "/api/progress":
                slug = (query.get("project") or [""])[0]
                if not slug:
                    return self._err("project required", 400)
                pf = (state.projects_root / slug) / ".progress.json"
                data: dict = {}
                if pf.exists():
                    try:
                        import json as _json
                        data = _json.loads(pf.read_text(encoding="utf-8"))
                    except Exception:  # noqa: BLE001
                        data = {}
                return self._json({"ok": True, "progress": data})
            return self._err(f"no such endpoint: {path}", 404)

        # ---- POST /api ----
        def _route_post_api(self, path: str, body: dict):
            if path == "/api/setup":
                return self._json(self._api_setup(body))
            if path == "/api/ai/parse":
                return self._json(self._api_ai_parse(body))
            if path == "/api/ai/run":
                return self._json(self._api_ai_run(body))
            if path == "/api/run":
                return self._json(self._api_run(body))
            if path == "/api/reindex":
                return self._json(self._api_reindex(body))
            if path == "/api/new":
                return self._json(self._api_new(body))
            if path == "/api/config/llm":
                return self._json(self._api_config_llm_save(body))
            if path == "/api/config/models":
                return self._json(self._api_config_models_save(body))
            if path == "/api/config/test_llm":
                return self._json(self._api_config_test_llm(body))
            if path == "/api/config/production":
                return self._json(self._api_config_production_save(body))
            if path == "/api/comfyui/inspect":
                return self._json(self._api_comfyui_inspect(body))
            if path == "/api/comfyui/apply":
                return self._json(self._api_comfyui_apply(body))
            if path == "/api/shot/update":
                return self._json(self._api_shot_update(body))
            if path == "/api/shot/regen":
                return self._json(self._api_shot_regen(body))
            if path == "/api/line/update":
                return self._json(self._api_line_update(body))
            if path == "/api/character/update":
                return self._json(self._api_character_update(body))
            if path == "/api/character/regen":
                return self._json(self._api_character_regen(body))
            return self._err(f"no such endpoint: {path}", 404)

        # ---- static + media ----
        def _serve_static(self, path: str):
            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            f = (STATIC_DIR / rel).resolve()
            if not str(f).startswith(str(STATIC_DIR.resolve())) or not f.is_file():
                f = STATIC_DIR / "index.html"
            ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
            self._send(200, f.read_bytes(), ctype)

        def _serve_media(self, rel: str):
            """rel = <project-slug>/<project-relative-path>. Confined to projects root."""
            parts = rel.split("/", 1)
            if len(parts) != 2:
                return self._err("bad media path", 400)
            slug, sub = parts[0], parts[1]
            base = (state.projects_root / slug).resolve()
            target = (base / sub).resolve()
            if not str(target).startswith(str(base)) or not target.is_file():
                return self._err("not found", 404)
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self._send(200, target.read_bytes(), ctype)

        # ---- API implementations ----
        def _api_state(self) -> dict:
            with state.lock:
                projs = self._api_projects()
                return {
                    "ok": True,
                    "title": state.cfg.web.title,
                    "projects": projs,
                    "current_project": projs[0]["slug"] if projs else "",
                    "config_summary": {
                        "default_model": state.cfg.resolve_llm("").model,
                        "default_base_url": state.cfg.resolve_llm("").base_url,
                        "tag_model": state.cfg.resolve_llm("tag").model,
                        "comfyui": state.cfg.comfyui.base_url,
                        "comfyui_enabled": state.cfg.comfyui.enabled,
                        "comfyui_mode": state.cfg.comfyui.mode,
                        "t2i_workflow": state.cfg.comfyui.t2i_workflow,
                        "i2v_workflow": state.cfg.comfyui.i2v_workflow,
                        "flf_workflow": state.cfg.comfyui.flf_workflow,
                        "first_last_frame": state.cfg.comfyui.first_last_frame,
                        "auto_map": state.cfg.comfyui.auto_map,
                        "auto_workflows": state.cfg.comfyui.auto_workflows,
                        "consistency": state.cfg.characters.consistency,
                        "generate_refs": state.cfg.characters.generate_refs,
                        "generate_location_refs": state.cfg.characters.generate_location_refs,
                        "auto_cast": state.cfg.characters.auto_cast,
                        "checkpoint": state.cfg.comfyui.checkpoint,
                        "tts": state.cfg.tts.provider,
                        "tts_base_url": state.cfg.tts.base_url,
                        "music": state.cfg.music.provider,
                        "music_library": state.cfg.music.library_dir,
                    },
                    "counts": {"projects": len(projs)},
                }

        def _api_projects(self) -> list[dict]:
            out = []
            cat_counts = {p["project"]: p for p in state.catalog.projects()}
            for slug in state.project_slugs():
                store = state.open_store(slug)
                if not store:
                    continue
                try:
                    proj = store.load()
                except Exception:  # noqa: BLE001
                    continue
                cc = cat_counts.get(slug, {})
                out.append({
                    "slug": slug,
                    "name": proj.meta.name,
                    "title": proj.meta.title or proj.meta.name,
                    "genre": proj.art_direction.genre,
                    "style": proj.art_direction.style,
                    "episodes": len(proj.episodes),
                    "shots": proj.total_shots,
                    "characters": len(proj.characters),
                    "updated_at": proj.meta.updated_at,
                    "indexed": int(cc.get("n", 0)),
                })
            out.sort(key=lambda p: p.get("updated_at") or "", reverse=True)
            return out

        def _api_project_detail(self, slug: str) -> dict:
            store = state.open_store(slug)
            if not store:
                return {"ok": False, "error": f"no such project: {slug}"}
            proj = store.load()

            def _sv(s):
                return s.value if hasattr(s, "value") else str(s or "")

            def _char(c):
                d = c.model_dump()
                d["ref_urls"] = [_media_url(slug, r) for r in c.refs()]
                d["ref_sheet_url"] = _media_url(slug, c.ref_sheet)
                return d

            episodes = []
            for ep in proj.episodes:
                scenes = []
                for sc in ep.scenes:
                    shots = [{
                        "id": sh.id, "index": sh.index,
                        "shot_type": sh.shot_type.value, "camera": sh.camera_move,
                        "action": sh.action, "duration": sh.duration,
                        "characters": sh.characters, "status": _sv(sh.status),
                        "prompt": sh.prompt, "negative_prompt": sh.negative_prompt,
                        "end_prompt": sh.end_prompt, "seed": sh.seed, "flf": sh.flf,
                        "gen_meta": sh.gen_meta,
                        "image": _media_url(slug, sh.image_path),
                        "end_image": _media_url(slug, sh.end_image_path),
                        "video": _media_url(slug, sh.video_path),
                    } for sh in sc.shots]
                    lines = [{
                        "id": l.id, "kind": l.kind.value, "speaker": l.speaker,
                        "text": l.text, "emotion": l.emotion,
                        "duration": l.duration, "status": _sv(l.status),
                        "audio": _media_url(slug, l.audio_path),
                    } for l in sc.lines]
                    scenes.append({
                        "id": sc.id, "index": sc.index, "location": sc.location,
                        "time": sc.time_of_day, "mood": sc.mood,
                        "bgm_mood": sc.bgm_mood,
                        "summary": sc.summary, "status": _sv(sc.status),
                        "shots": shots, "lines": lines,
                    })
                episodes.append({
                    "id": ep.id, "index": ep.index, "title": ep.title,
                    "logline": ep.logline, "hook": ep.hook,
                    "status": _sv(ep.status), "stage_status": {k: _sv(v) for k, v in ep.stage_status.items()},
                    "estimated_seconds": ep.estimated_seconds,
                    "video": _media_url(slug, ep.video_path),
                    "cover": _media_url(slug, ep.cover_path),
                    "subtitle": _media_url(slug, ep.subtitle_path or ep.ass_path),
                    "bgm": _media_url(slug, ep.bgm_path),
                    "scenes": scenes,
                })
            locations = []
            for loc in proj.locations:
                d = loc.model_dump()
                d["ref_urls"] = [_media_url(slug, r) for r in loc.ref_images]
                locations.append(d)
            return {
                "ok": True, "slug": slug,
                "meta": proj.meta.model_dump(),
                "art_direction": proj.art_direction.model_dump(),
                "characters": [_char(c) for c in proj.characters],
                "locations": locations,
                "stage_status": {k: _sv(v) for k, v in proj.stage_status.items()},
                "episodes": episodes,
            }

        def _api_health(self) -> dict:
            # Probe does network I/O (ComfyUI ping, edge-tts voice list) that can
            # take >10s when a server is unreachable, so run it as a job and let
            # the browser poll — never block the request thread.
            def _job():
                from ..ai import autoconfig
                rep = autoconfig.probe(state.cfg)
                return {"probe": _slim_probe(rep), "brain": state.brain().probe()}
            jid = state.start_job("health", _job)
            return {"ok": True, "job": jid}

        def _api_search(self, q: str, slug: str) -> dict:
            brain = state.brain()
            filt = brain.expand_query(q) if q.strip() else {
                "keywords": [], "tags": [], "category": "", "kinds": []}
            rows = state.catalog.search(
                project=slug or None, keywords=filt.get("keywords"),
                tags=filt.get("tags"), category=filt.get("category", ""),
                kinds=filt.get("kinds") or None,
                limit=state.cfg.ai.max_search_results)
            for r in rows:
                if r.get("path"):
                    r["media_url"] = _media_url(r["project"], r["path"])
            return {"ok": True, "query": q, "filters": filt,
                    "count": len(rows), "results": rows}

        def _api_setup(self, body: dict) -> dict:
            from ..ai import autoconfig
            intent = body.get("intent", "")
            preset = body.get("genre_preset", "")
            chips = body.get("chips", [])
            extra = body.get("extra", "")
            write = bool(body.get("write", True))

            def _job():
                out_path = state.config_path or Path("config/default.yaml")
                res = autoconfig.setup(state.cfg, intent, genre_preset=preset,
                                       chips=chips, extra=extra, out_path=out_path)
                if write:
                    state.reload_config()
                return {"written": res["written"], "used_llm": res["used_llm"],
                        "art_defaults": res["art_defaults"],
                        "overrides": res["overrides"],
                        "probe": _slim_probe(res["probe"])}

            jid = state.start_job("setup", _job)
            return {"ok": True, "job": jid}

        def _api_ai_parse(self, body: dict) -> dict:
            from ..ai import actions
            instr = body.get("instruction", "")
            current = body.get("project", "")
            act = actions.parse(state.brain(), instr,
                                projects=state.project_slugs(),
                                current_project=current)
            return {"ok": True, "action": act.to_dict()}

        def _api_ai_run(self, body: dict) -> dict:
            """Execute a previously-parsed action (client echoes it back)."""
            from ..ai import actions
            ad = body.get("action") or {}
            kind = ad.get("kind")
            if kind not in actions.ACTION_SPEC:
                return {"ok": False, "error": f"unknown action kind: {kind}"}
            act = actions._build(kind, ad.get("params", {}), state.project_slugs())
            # search/reindex run inline (fast); the rest go to a background job
            if kind in ("search", "reindex", "export"):
                res = actions.execute(act, state.cfg,
                                      projects_root=state.projects_root,
                                      catalog=state.catalog)
                for r in (res.get("results") or []):
                    if r.get("path"):
                        r["media_url"] = _media_url(r["project"], r["path"])
                return {"ok": True, "result": res}

            def _job():
                res = actions.execute(act, state.cfg,
                                      projects_root=state.projects_root,
                                      catalog=state.catalog)
                # keep the catalog fresh after mutations
                slug = act.params.get("project")
                if slug and state.cfg.ai.auto_tag:
                    store = state.open_store(slug)
                    if store:
                        brain = state.brain()
                        with_ai = state.cfg.ai.enabled and brain.probe()["main"]["ok"]
                        state.catalog.reindex_project(
                            store, with_ai=with_ai,
                            brain=brain if with_ai else None)
                return res

            jid = state.start_job(kind, _job)
            return {"ok": True, "job": jid}

        def _api_run(self, body: dict) -> dict:
            from ..ai import actions
            params = {
                "project": body.get("project", ""),
                "episodes": body.get("episodes", []),
                "stages": body.get("stages", []),
                "overrides": body.get("overrides", {}),
            }
            act = actions._build("run_pipeline", params, state.project_slugs())

            def _job():
                res = actions.execute(act, state.cfg,
                                      projects_root=state.projects_root,
                                      catalog=state.catalog)
                slug = act.params.get("project")
                if slug and state.cfg.ai.auto_tag:
                    store = state.open_store(slug)
                    if store:
                        brain = state.brain()
                        with_ai = state.cfg.ai.enabled and brain.probe()["main"]["ok"]
                        state.catalog.reindex_project(
                            store, with_ai=with_ai,
                            brain=brain if with_ai else None)
                return res

            jid = state.start_job("run_pipeline", _job)
            return {"ok": True, "job": jid}

        def _api_reindex(self, body: dict) -> dict:
            slug = body.get("project", "")
            with_ai = bool(body.get("with_ai", True))
            store = state.open_store(slug)
            if not store:
                return {"ok": False, "error": f"no such project: {slug}"}

            def _job():
                brain = state.brain()
                use_ai = with_ai and state.cfg.ai.enabled and brain.probe()["main"]["ok"]
                return state.catalog.reindex_project(
                    store, with_ai=use_ai, brain=brain if use_ai else None)

            jid = state.start_job("reindex", _job)
            return {"ok": True, "job": jid}

        def _api_new(self, body: dict) -> dict:
            name = (body.get("name") or "").strip()
            if not name:
                return {"ok": False, "error": "name required"}
            source = body.get("source", "")
            store = ProjectStore.create(state.projects_root, name,
                                        source or None)
            # seed art direction if provided by setup
            art = body.get("art_defaults") or {}
            if art:
                proj = store.load()
                for k, v in art.items():
                    if hasattr(proj.art_direction, k):
                        setattr(proj.art_direction, k, v)
                store.save(proj)
            state.catalog.reindex_project(store, with_ai=False)
            return {"ok": True, "slug": store.root.name, "path": str(store.root)}

        # ---- shot / line / character editing (storyboard console) ----
        def _get_shot(self, store, ep_index: int, shot_id: str):
            proj = store.load()
            ep = proj.episode(ep_index)
            if ep is None:
                return proj, None, None
            for sc in ep.scenes:
                for sh in sc.shots:
                    if sh.id == shot_id:
                        return proj, ep, sh
            return proj, ep, None

        def _api_shot_update(self, body: dict) -> dict:
            from ..models import ShotType
            store = state.open_store(body.get("project", ""))
            if not store:
                return {"ok": False, "error": "项目不存在"}
            ep_index = int(body.get("episode") or 0)
            shot_id = str(body.get("shot_id") or "")
            fields = body.get("fields") or {}
            with state.lock:
                proj, ep, shot = self._get_shot(store, ep_index, shot_id)
                if shot is None:
                    return {"ok": False, "error": f"没有镜头 {shot_id}"}
                if "shot_type" in fields:
                    try:
                        shot.shot_type = ShotType(str(fields["shot_type"]))
                    except ValueError:
                        return {"ok": False, "error": "未知景别"}
                if "camera" in fields:
                    shot.camera_move = str(fields["camera"] or "固定")
                for key in ("action", "prompt", "negative_prompt", "end_prompt"):
                    if key in fields:
                        setattr(shot, key, str(fields[key] or ""))
                if "characters" in fields:
                    shot.characters = [str(x) for x in (fields["characters"] or []) if str(x).strip()]
                if "duration" in fields:
                    shot.duration = max(0.5, min(float(fields["duration"]), 60.0))
                if "seed" in fields:
                    shot.seed = int(fields["seed"])
                if "flf" in fields:
                    v = fields["flf"]
                    shot.flf = None if v is None else _as_bool(v)
                store.save(proj)
            return {"ok": True, "shot": shot.model_dump(),
                    "image": _media_url(store.root.name, shot.image_path),
                    "video": _media_url(store.root.name, shot.video_path)}

        def _api_shot_regen(self, body: dict) -> dict:
            from ..pipeline import visual as visual_stage
            store = state.open_store(body.get("project", ""))
            if not store:
                return {"ok": False, "error": "项目不存在"}
            ep_index = int(body.get("episode") or 0)
            shot_id = str(body.get("shot_id") or "")
            mode = str(body.get("mode") or "all")
            if mode not in ("image", "video", "all"):
                return {"ok": False, "error": "mode 必须是 image/video/all"}
            slug = store.root.name

            def _job():
                res = visual_stage.regen_shot(store, state.cfg, ep_index, shot_id, mode=mode)
                if res.get("ok") and mode in ("video", "all"):
                    with state.lock:
                        proj = store.load()
                        ep = proj.episode(ep_index)
                        if ep:
                            _invalidate_stages(ep, "compose")
                            store.save(proj)
                return res

            return {"ok": True, "job": state.start_job("regen_shot", _job), "project": slug}

        def _api_line_update(self, body: dict) -> dict:
            from ..models import LineKind, Status
            store = state.open_store(body.get("project", ""))
            if not store:
                return {"ok": False, "error": "项目不存在"}
            ep_index = int(body.get("episode") or 0)
            line_id = str(body.get("line_id") or "")
            fields = body.get("fields") or {}
            with state.lock:
                proj = store.load()
                ep = proj.episode(ep_index)
                line = next((l for sc in (ep.scenes if ep else [])
                             for l in sc.lines if l.id == line_id), None)
                if line is None:
                    return {"ok": False, "error": f"没有台词 {line_id}"}
                voice_keys = ("text", "speaker", "emotion", "kind")
                touched = False
                if "text" in fields:
                    line.text = str(fields["text"] or "")
                    touched = True
                if "speaker" in fields:
                    line.speaker = str(fields["speaker"] or "旁白")
                    touched = True
                if "emotion" in fields:
                    line.emotion = str(fields["emotion"] or "平静")
                    touched = True
                if "kind" in fields:
                    try:
                        line.kind = LineKind(str(fields["kind"]))
                        touched = True
                    except ValueError:
                        return {"ok": False, "error": "未知台词类型"}
                if touched:
                    line.audio_path = ""
                    line.duration = 0.0
                    line.status = Status.PENDING
                    _invalidate_stages(ep, "voice", "subtitle", "compose")
                store.save(proj)
            return {"ok": True, "line": line.model_dump()}

        def _api_character_update(self, body: dict) -> dict:
            from ..models import Status
            store = state.open_store(body.get("project", ""))
            if not store:
                return {"ok": False, "error": "项目不存在"}
            name = str(body.get("name") or "")
            fields = body.get("fields") or {}
            allowed = ("role", "gender", "age", "personality", "appearance",
                       "visual_prompt", "outfit", "hair", "anchor_prompt",
                       "negative_prompt", "consistency", "voice_id", "lora",
                       "voice_pitch", "voice_rate")
            with state.lock:
                proj = store.load()
                char = proj.character(name)
                if char is None:
                    return {"ok": False, "error": f"没有角色 {name}"}
                for key in allowed:
                    if key in fields:
                        setattr(char, key, str(fields[key] or ""))
                if "locked" in fields:
                    char.locked = _as_bool(fields["locked"])
                reset = _as_bool(body.get("reset_prompts"))
                if reset:
                    for ep in proj.episodes:
                        touched_ep = False
                        for sc in ep.scenes:
                            for sh in sc.shots:
                                if any(char.matches(n) for n in sh.characters):
                                    sh.prompt = ""
                                    sh.negative_prompt = ""
                                    sh.status = Status.PENDING
                                    touched_ep = True
                        if touched_ep:
                            _invalidate_stages(ep, "promptgen", "visual", "compose")
                store.save(proj)
            return {"ok": True, "character": char.model_dump(),
                    "ref_urls": [_media_url(store.root.name, r) for r in char.refs()],
                    "reset_prompts": _as_bool(body.get("reset_prompts"))}

        def _api_character_regen(self, body: dict) -> dict:
            from ..pipeline import character as character_stage
            store = state.open_store(body.get("project", ""))
            if not store:
                return {"ok": False, "error": "项目不存在"}
            name = str(body.get("name") or "")
            views = body.get("views") or None
            reset = _as_bool(body.get("reset_prompts"))

            def _job():
                res = character_stage.generate_for_one(store, state.cfg, name, views)
                if res.get("ok") and reset:
                    from ..models import Status
                    with state.lock:
                        proj = store.load()
                        char = proj.character(name)
                        for ep in proj.episodes:
                            touched = False
                            for sc in ep.scenes:
                                for sh in sc.shots:
                                    if char and any(char.matches(n) for n in sh.characters):
                                        sh.prompt = ""
                                        sh.status = Status.PENDING
                                        touched = True
                            if touched:
                                _invalidate_stages(ep, "promptgen", "visual", "compose")
                        store.save(proj)
                return res

            return {"ok": True, "job": state.start_job("character_refs", _job)}

        # ---- production parameters (visual / character / compose) ----
        def _api_config_production_get(self) -> dict:
            with state.lock:
                c = state.cfg
            return {"ok": True,
                    "comfyui": {
                        "enabled": c.comfyui.enabled, "mode": c.comfyui.mode,
                        "base_url": c.comfyui.base_url, "width": c.comfyui.width,
                        "height": c.comfyui.height, "frames": c.comfyui.frames,
                        "fps": c.comfyui.fps, "steps": c.comfyui.steps,
                        "cfg": c.comfyui.cfg, "seed_mode": c.comfyui.seed_mode,
                        "concurrency": c.comfyui.concurrency,
                        "first_last_frame": c.comfyui.first_last_frame,
                        "t2i_workflow": c.comfyui.t2i_workflow,
                        "i2v_workflow": c.comfyui.i2v_workflow,
                        "flf_workflow": c.comfyui.flf_workflow,
                        "auto_map": c.comfyui.auto_map,
                        "auto_workflows": c.comfyui.auto_workflows,
                    },
                    "characters": c.characters.model_dump(),
                    "compose": {
                        "transition": c.compose.transition,
                        "transition_duration": c.compose.transition_duration,
                        "motion_effect": c.compose.motion_effect,
                        "kenburns_scale": c.compose.kenburns_scale,
                        "burn_subtitles": c.compose.burn_subtitles,
                    },
                    "music": {"provider": c.music.provider,
                              "bgm_volume": c.music.bgm_volume,
                              "duck_voice": c.music.duck_voice},
                    "tts": {"provider": c.tts.provider, "concurrency": c.tts.concurrency}}

        def _api_config_production_save(self, body: dict) -> dict:
            from ..ai import autoconfig
            specs = {
                "comfyui": {
                    "enabled": _as_bool, "mode": str, "base_url": str,
                    "width": int, "height": int, "frames": int, "fps": int,
                    "steps": int, "cfg": float, "seed_mode": str,
                    "concurrency": int, "first_last_frame": _as_bool,
                    "t2i_workflow": str, "i2v_workflow": str, "flf_workflow": str,
                    "auto_map": _as_bool, "auto_workflows": _as_bool,
                },
                "characters": {
                    "enabled": _as_bool, "generate_refs": _as_bool,
                    "generate_location_refs": _as_bool, "auto_cast": _as_bool,
                    "consistency": str, "use_llm_anchor": _as_bool,
                },
                "compose": {
                    "transition": str, "transition_duration": float,
                    "motion_effect": str, "kenburns_scale": float,
                    "burn_subtitles": _as_bool,
                },
                "music": {"bgm_volume": float, "duck_voice": _as_bool},
                "tts": {"concurrency": int},
            }
            updates: dict = {}
            for section, fields in specs.items():
                src = body.get(section) or {}
                if not isinstance(src, dict):
                    continue
                for key, cast in fields.items():
                    if key not in src:
                        continue
                    try:
                        updates.setdefault(section, {})[key] = cast(src[key])
                    except (TypeError, ValueError):
                        return {"ok": False,
                                "error": f"{section}.{key} 的值不合法：{src[key]!r}"}
            if not updates:
                return {"ok": True, "updated": {}}
            cfg_path = state.config_path or Path("config/default.yaml")
            try:
                autoconfig.save_settings(cfg_path, updates)
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": f"写入配置失败: {str(e)[:200]}"}
            state.reload_config()
            out = self._api_config_production_get()
            out["updated"] = updates
            return out

        # ---- ComfyUI auto-connect (inspect + apply) ----
        def _display_path(self, path: str) -> str:
            try:
                return str(Path(path).resolve().relative_to(Path(".").resolve())).replace("\\", "/")
            except ValueError:
                return str(Path(path).resolve()).replace("\\", "/")

        def _api_comfyui_inspect(self, body: dict) -> dict:
            from ..providers.comfyui import ComfyUIClient
            from ..providers.workflow_map import infer_workflow, score_workflow
            with state.lock:
                cfg = state.cfg.comfyui.model_copy(deep=True)
            url = str(body.get("base_url") or "").strip()
            if url:
                cfg.base_url = url
            cfg.enabled = True
            client = ComfyUIClient(cfg, Path("."))
            out: dict = {"ok": True, "base_url": cfg.base_url,
                         "reachable": False, "workflows": [],
                         "checkpoints": [], "current_checkpoint": cfg.checkpoint,
                         "recommend": {}}
            if not client.ping():
                out["error"] = "连不上 ComfyUI（检查 --listen、端口、防火墙；局域网记得 use_proxy=false）"
                return out
            out["reachable"] = True
            try:
                st = client.system_stats()
                info = st.get("system", {})
                out["version"] = info.get("comfyui_version", "")
                out["gpus"] = [
                    {"name": d.get("name"),
                     "vram_gb": round(d.get("vram_total", 0) / (1024 ** 3), 1)}
                    for d in info.get("devices", [])
                ]
            except Exception as e:  # noqa: BLE001
                out["warning"] = f"读取 system_stats 失败: {str(e)[:120]}"
            try:
                out["checkpoints"] = client.list_checkpoints()[:40]
            except Exception:  # noqa: BLE001
                pass
            best: dict[str, dict] = {}
            for path in client.workflow_files():
                rel = self._display_path(path)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        graph = json.load(f)
                except Exception as e:  # noqa: BLE001
                    out["workflows"].append({"file": rel, "name": Path(path).name,
                                             "ok": False, "kind": "unknown",
                                             "problems": [f"无法读取: {str(e)[:120]}"]})
                    continue
                if not isinstance(graph, dict):
                    out["workflows"].append({"file": rel, "name": Path(path).name,
                                             "ok": False, "kind": "unknown",
                                             "problems": ["不是 API 格式：应为 JSON 对象"]})
                    continue
                try:
                    info = infer_workflow(graph)
                    nmap = cfg.t2i_nodes if info["kind"] == "t2i" else cfg.i2v_nodes
                    rep = client.validate_workflow(rel, nmap, info["kind"])
                except Exception as e:  # noqa: BLE001
                    out["workflows"].append({"file": rel, "name": Path(path).name,
                                             "ok": False, "kind": "unknown",
                                             "problems": [f"识别失败: {str(e)[:160]}"]})
                    continue
                item = {
                    "file": rel, "name": Path(path).name,
                    "kind": info["kind"], "ok": rep.get("ok", False),
                    "nodes": rep.get("nodes", 0),
                    "map": {k: v for k, v in (rep.get("inferred") or {}).items() if v},
                    "problems": [str(p)[:220] for p in (rep.get("problems") or [])][:6],
                    "warnings": [str(p)[:220] for p in (rep.get("warnings") or [])][:6],
                    "score": score_workflow(info),
                }
                out["workflows"].append(item)
                kind = item["kind"]
                if item["ok"]:
                    if kind == "i2v" and item["map"].get("last_image"):
                        if item["score"] > best.get("flf", {}).get("score", -1):
                            best["flf"] = item
                    if item["score"] > best.get(kind, {}).get("score", -1):
                        best[kind] = item
            out["workflows"].sort(key=lambda x: (x.get("kind") != "t2i", -x.get("score", 0)))
            out["recommend"] = {k: {"file": v["file"], "name": v["name"],
                                    "map": v["map"], "kind": v["kind"]}
                                for k, v in best.items()}
            return out

        def _api_comfyui_apply(self, body: dict) -> dict:
            from ..ai import autoconfig
            root = Path(".")
            scalars: dict = {"enabled": True, "auto_map": True, "auto_workflows": True}
            for key in ("enabled", "auto_map", "auto_workflows"):
                if key in body:
                    scalars[key] = bool(body[key])
            for key in ("base_url", "t2i_workflow", "i2v_workflow",
                        "flf_workflow", "checkpoint", "mode"):
                if key in body and str(body.get(key) or "").strip():
                    scalars[key] = str(body[key]).strip()
            if "flf_workflow" in body and not str(body.get("flf_workflow") or "").strip():
                scalars["flf_workflow"] = ""
            for key in ("t2i_workflow", "i2v_workflow", "flf_workflow"):
                rel = scalars.get(key)
                if not rel:
                    continue
                path = Path(rel) if Path(rel).is_absolute() else root / rel
                if not path.exists():
                    return {"ok": False, "error": f"工作流不存在: {rel}"}
            if "first_last_frame" in body:
                scalars["first_last_frame"] = bool(body["first_last_frame"])
            elif scalars.get("flf_workflow"):
                scalars["first_last_frame"] = True
            if scalars.get("base_url"):
                scalars["base_url"] = scalars["base_url"].rstrip("/")
            maps = {}
            for key in ("t2i_nodes", "i2v_nodes"):
                src = body.get(key)
                if isinstance(src, dict):
                    maps[key] = {str(k): str(v) for k, v in src.items() if v not in (None, "")}
            characters = {}
            if "consistency" in body:
                characters["consistency"] = str(body["consistency"])
            if "generate_location_refs" in body:
                characters["generate_location_refs"] = bool(body["generate_location_refs"])
            if "auto_cast" in body:
                characters["auto_cast"] = bool(body["auto_cast"])
            path = state.config_path or Path("config/default.yaml")
            try:
                autoconfig.save_comfyui_settings(path, scalars, maps, characters)
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": f"写入配置失败: {str(e)[:240]}"}
            state.reload_config()
            with state.lock:
                c = state.cfg.comfyui
                consistency = state.cfg.characters.consistency
            return {"ok": True, "updated": scalars,
                    "config": {"base_url": c.base_url,
                               "t2i_workflow": c.t2i_workflow,
                               "i2v_workflow": c.i2v_workflow,
                               "flf_workflow": c.flf_workflow,
                               "checkpoint": c.checkpoint,
                               "first_last_frame": c.first_last_frame,
                               "auto_map": c.auto_map,
                               "auto_workflows": c.auto_workflows},
                    "consistency": consistency}

        # ---- model registry (settings page) ----
        def _api_config_models_get(self) -> dict:
            from ..ai.templates import MODEL_ROLES
            with state.lock:
                c = state.cfg
            entries = [_model_entry_public(e) for e in c.models.entries]
            if entries:
                default = c.models.default
                if default not in {e["id"] for e in entries}:
                    default = entries[0]["id"]
            else:
                entries, default = _legacy_model_entries(c)
            return {
                "ok": True, "default": default, "entries": entries,
                "roles": MODEL_ROLES, "legacy": not bool(c.models.entries),
                "ai": {"enabled": c.ai.enabled, "language": c.ai.language,
                       "auto_tag": c.ai.auto_tag, "main_timeout": c.ai.main_timeout},
            }

        def _api_config_models_save(self, body: dict) -> dict:
            from ..ai import autoconfig
            from ..ai.templates import MODEL_ROLE_IDS
            raw = body.get("entries")
            if not isinstance(raw, list):
                return {"ok": False, "error": "entries 必须是数组"}
            with state.lock:
                c = state.cfg
            old = {e.id: e for e in c.models.entries}
            out: list[dict] = []
            seen: set[str] = set()
            for i, m in enumerate(raw):
                if not isinstance(m, dict):
                    continue
                eid = str(m.get("id") or "").strip() or f"m{i + 1}"
                while eid in seen:
                    eid = f"{eid}_{i + 1}"
                seen.add(eid)
                base = str(m.get("base_url") or "").strip()
                model = str(m.get("model") or "").strip()
                if not base or not model:
                    return {"ok": False,
                            "error": f"第 {i + 1} 个模型：接口地址和模型名不能为空"}
                # keys: typed wins; empty = keep the saved one; 清除 = forget
                key_in = str(m.get("api_key") or "").strip()
                prev = old.get(eid)
                if _as_bool(m.get("clear_api_key")):
                    key = ""
                elif key_in:
                    key = key_in
                elif prev is not None:
                    key = prev.api_key
                elif not c.models.entries:
                    # first save of the synthesized legacy list: keep working keys
                    if (c.ai.light_model and base == c.ai.light_base_url
                            and model == c.ai.light_model):
                        key = c.ai.light_api_key or c.llm.api_key
                    elif base == c.llm.base_url and model == c.llm.model:
                        key = c.llm.api_key
                    else:
                        key = ""
                else:
                    key = ""
                roles = [str(r) for r in (m.get("roles") or [])]
                out.append({
                    "id": eid, "label": str(m.get("label") or "").strip(),
                    "base_url": base, "model": model, "api_key": key,
                    "temperature": _as_float(m.get("temperature"), 0.7, 0.0, 2.0),
                    "max_tokens": int(_as_float(m.get("max_tokens"), 4096, 1, 200000)),
                    "timeout": _as_float(m.get("timeout"), 300.0, 1.0, 3600.0),
                    "use_proxy": _as_bool(m.get("use_proxy", False)),
                    "roles": [r for r in roles if r in MODEL_ROLE_IDS],
                })
            default = str(body.get("default") or "").strip()
            ids = {e["id"] for e in out}
            if default not in ids:
                default = out[0]["id"] if out else ""
            updates: dict = {}
            if out:
                d = next(e for e in out if e["id"] == default)
                # keep legacy consumers (dj doctor, older tooling) on the
                # default model
                updates["llm"] = {
                    "base_url": d["base_url"], "model": d["model"],
                    "api_key": d["api_key"], "temperature": d["temperature"],
                    "max_tokens": d["max_tokens"], "timeout": d["timeout"],
                    "use_proxy": d["use_proxy"],
                }
            cfg_path = state.config_path or Path("config/default.yaml")
            try:
                autoconfig.save_settings(
                    cfg_path, updates,
                    blocks={"models": {"default": default, "entries": out}})
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": f"写入配置失败: {str(e)[:200]}"}
            state.reload_config()
            return self._api_config_models_get()

        # ---- LLM / AI-brain settings (settings page) ----
        def _api_config_llm_get(self) -> dict:
            with state.lock:
                c = state.cfg
            return {
                "ok": True,
                "llm": {
                    "base_url": c.llm.base_url, "model": c.llm.model,
                    "temperature": c.llm.temperature, "max_tokens": c.llm.max_tokens,
                    "timeout": c.llm.timeout, "use_proxy": c.llm.use_proxy,
                    "api_key_masked": _mask_key(c.llm.api_key),
                    "api_key_set": bool(c.llm.api_key),
                },
                "ai": {
                    "enabled": c.ai.enabled, "language": c.ai.language,
                    "auto_tag": c.ai.auto_tag, "main_timeout": c.ai.main_timeout,
                    "light_base_url": c.ai.light_base_url,
                    "light_model": c.ai.light_model,
                    "light_api_key_masked": _mask_key(c.ai.light_api_key),
                    "light_api_key_set": bool(c.ai.light_api_key),
                    "light_use_proxy": c.ai.light_use_proxy,
                    "light_aliased": not (c.ai.light_model and c.ai.light_base_url),
                },
            }

        def _api_config_llm_save(self, body: dict) -> dict:
            from ..ai import autoconfig
            llm_in = body.get("llm") or {}
            ai_in = body.get("ai") or {}
            updates: dict = {"llm": {}, "ai": {}}
            specs = [("llm", "base_url", str), ("llm", "model", str),
                     ("llm", "temperature", float), ("llm", "max_tokens", int),
                     ("llm", "timeout", float), ("llm", "use_proxy", _as_bool),
                     ("ai", "enabled", _as_bool), ("ai", "language", str),
                     ("ai", "auto_tag", _as_bool), ("ai", "main_timeout", float),
                     ("ai", "light_base_url", str), ("ai", "light_model", str),
                     ("ai", "light_use_proxy", _as_bool)]
            for sec, key, cast in specs:
                src = llm_in if sec == "llm" else ai_in
                if key in src:
                    try:
                        updates[sec][key] = cast(src[key])
                    except (TypeError, ValueError):
                        return {"ok": False, "error": f"{sec}.{key} 的值不合法：{src[key]!r}"}
            # api keys only when explicitly typed; empty string means "keep"
            if body.get("clear_api_key"):
                updates["llm"]["api_key"] = ""
            elif (body.get("api_key") or "").strip():
                updates["llm"]["api_key"] = str(body["api_key"]).strip()
            if body.get("clear_light_api_key"):
                updates["ai"]["light_api_key"] = ""
            elif (body.get("light_api_key") or "").strip():
                updates["ai"]["light_api_key"] = str(body["light_api_key"]).strip()
            cfg_path = state.config_path or Path("config/default.yaml")
            try:
                autoconfig.save_settings(cfg_path, updates)
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": f"写入配置失败: {str(e)[:200]}"}
            state.reload_config()
            return self._api_config_llm_get()

        def _api_config_test_llm(self, body: dict) -> dict:
            from ..ai import autoconfig
            with state.lock:
                cfg = state.cfg
            entry = None
            eid = (body.get("entry_id") or "").strip()
            if eid:
                entry = next((e for e in cfg.models.entries if e.id == eid), None)
            base = (body.get("base_url") or "").strip() or (entry.base_url if entry else "")
            model = (body.get("model") or "").strip() or (entry.model if entry else "")
            if "use_proxy" in body:
                use_proxy = _as_bool(body["use_proxy"])
            else:
                use_proxy = entry.use_proxy if entry else False
            key_in = (body.get("api_key") or "").strip()
            used_saved = False
            if key_in:
                key = key_in
            elif entry is not None:
                key = entry.api_key
                used_saved = bool(key)
            else:
                key = cfg.llm.api_key
                used_saved = bool(key)
            res = autoconfig.test_llm_endpoint(base, key, model, use_proxy=use_proxy)
            res["used_saved_key"] = used_saved
            return {"ok": True, **res}

    return Handler


def _invalidate_stages(ep, *stages: str) -> None:
    """Mark stages stale so a subsequent pipeline run redoes them."""
    from ..models import Status
    for s in stages:
        if s in ep.stage_status:
            ep.stage_status[s] = Status.PENDING


def _mask_key(v: str) -> str:
    if not v:
        return ""
    if len(v) <= 6:
        return "•" * 4
    return v[:4] + "•" * 6 + v[-3:]


def _as_bool(v) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "on")
    return bool(v)


def _as_float(v, default: float, lo: float | None = None,
              hi: float | None = None) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if lo is not None:
        x = max(lo, x)
    if hi is not None:
        x = min(hi, x)
    return x


def _model_entry_public(e) -> dict:
    """ModelEntry → browser-safe dict (never includes the raw API key)."""
    return {
        "id": e.id, "label": e.label, "base_url": e.base_url,
        "model": e.model, "temperature": e.temperature,
        "max_tokens": e.max_tokens, "timeout": e.timeout,
        "use_proxy": e.use_proxy, "roles": list(e.roles),
        "api_key_masked": _mask_key(e.api_key), "api_key_set": bool(e.api_key),
    }


def _legacy_model_entries(cfg: Config) -> tuple[list[dict], str]:
    """Synthesize a model list from the legacy llm / ai.light_* config so the
    settings page can show (and later persist) a registry."""
    from ..ai.templates import MODEL_ROLE_IDS
    has_light = bool(cfg.ai.light_model and cfg.ai.light_base_url)
    main_roles = [r for r in MODEL_ROLE_IDS if not (has_light and r == "tag")]
    entries = [{
        "id": "m1", "label": "当前模型",
        "base_url": cfg.llm.base_url, "model": cfg.llm.model,
        "temperature": cfg.llm.temperature, "max_tokens": cfg.llm.max_tokens,
        "timeout": cfg.llm.timeout, "use_proxy": cfg.llm.use_proxy,
        "roles": main_roles,
        "api_key_masked": _mask_key(cfg.llm.api_key),
        "api_key_set": bool(cfg.llm.api_key),
    }]
    if has_light:
        light_key = cfg.ai.light_api_key or cfg.llm.api_key
        entries.append({
            "id": "m2", "label": "打标小模型",
            "base_url": cfg.ai.light_base_url, "model": cfg.ai.light_model,
            "temperature": cfg.ai.light_temperature,
            "max_tokens": cfg.ai.light_max_tokens,
            "timeout": cfg.ai.light_timeout, "use_proxy": cfg.ai.light_use_proxy,
            "roles": ["tag"],
            "api_key_masked": _mask_key(light_key),
            "api_key_set": bool(light_key),
        })
    return entries, "m1"


def _media_url(slug: str, rel_path: str) -> str:
    if not rel_path:
        return ""
    segs = "/".join(quote(s) for s in rel_path.lstrip("/").split("/") if s != "")
    return f"/media/{quote(slug)}/{segs}"


def _slim_workflow_report(rep: Optional[dict]) -> Optional[dict]:
    if not rep:
        return None
    return {"file": rep.get("file"), "ok": rep.get("ok"),
            "nodes": rep.get("nodes", 0), "kind": rep.get("kind"),
            "inferred": {k: v for k, v in (rep.get("inferred") or {}).items() if v},
            "warnings": [str(p)[:220] for p in (rep.get("warnings") or [])][:6],
            "problems": [str(p)[:220] for p in (rep.get("problems") or [])][:6]}


def _slim_probe(rep: dict) -> dict:
    """Trim the probe report to what the UI shows."""
    comfy = rep.get("comfyui", {})
    return {
        "ffmpeg": rep.get("ffmpeg"),
        "llm_endpoints": [{"name": e["name"], "models": e["models"][:10]}
                          for e in rep.get("llm_endpoints", [])],
        "llm_main": rep.get("llm_main", {}),
        "comfyui": {"reachable": comfy.get("reachable"),
                    "base_url": comfy.get("base_url"),
                    "version": comfy.get("version", ""),
                    "gpus": comfy.get("gpus", []),
                    "checkpoints": (comfy.get("checkpoints") or [])[:12],
                    "t2i_ok": comfy.get("t2i_ok"), "i2v_ok": comfy.get("i2v_ok"),
                    "flf_ok": comfy.get("flf_ok"),
                    "t2i_report": _slim_workflow_report(comfy.get("t2i_report")),
                    "i2v_report": _slim_workflow_report(comfy.get("i2v_report")),
                    "flf_report": _slim_workflow_report(comfy.get("flf_report"))},
        "tts": {"provider": rep.get("tts", {}).get("provider"),
                "voice_count": rep.get("tts", {}).get("voice_count", 0)},
        "music": {"provider": rep.get("music", {}).get("provider"),
                  "track_count": rep.get("music", {}).get("track_count", 0)},
    }


# --------------------------------------------------------------------------- #
def serve(cfg: Config, *, config_path: Optional[Path] = None,
          host: Optional[str] = None, port: Optional[int] = None,
          open_browser: Optional[bool] = None) -> None:
    host = host or cfg.web.host
    port = port or cfg.web.port
    do_open = cfg.web.open_browser if open_browser is None else open_browser
    projects_root = Path(cfg.pipeline.output_dir).resolve()
    projects_root.mkdir(parents=True, exist_ok=True)
    state = State(cfg, config_path, projects_root)

    handler = _make_handler(state)
    httpd = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    log.info("DramaKit 控制台启动: %s", url)
    print(f"\n  DramaKit 控制台 → {url}")
    print(f"  项目目录: {projects_root}")
    print("  按 Ctrl+C 停止\n")
    if do_open:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  已停止控制台。")
    finally:
        httpd.server_close()
