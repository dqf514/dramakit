"""Asset catalog: a SQLite index over everything a project produces.

Every node in the Project tree (episode / scene / shot / line) and every media
asset (image / video / audio / subtitle / bgm / cover) becomes one searchable
row carrying AI-generated tags, a category, a summary and its project-relative
path. This single index powers:

  * project management  — browse/filter by tag, category, kind, status
  * AI retrieval        — natural-language search expanded by the Brain
  * AI actions          — "find every night-shot close-up of the lead" etc.

The DB lives at cfg.ai.catalog_db (default: projects/catalog.db). It is a cache:
`reindex_project()` rebuilds a project's rows from project.json at any time, so
it can always be regenerated and never needs manual upkeep.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Project, Status
from .project import ProjectStore

log = logging.getLogger("dramakit.catalog")

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    ref         TEXT DEFAULT '',
    ep_index    INTEGER DEFAULT 0,
    parent      TEXT DEFAULT '',
    title       TEXT DEFAULT '',
    text        TEXT DEFAULT '',
    summary     TEXT DEFAULT '',
    category    TEXT DEFAULT '',
    tags        TEXT DEFAULT '',
    path        TEXT DEFAULT '',
    status      TEXT DEFAULT '',
    extra       TEXT DEFAULT '',
    updated_at  TEXT DEFAULT '',
    UNIQUE(project, kind, ref)
);
CREATE INDEX IF NOT EXISTS ix_assets_project ON assets(project);
CREATE INDEX IF NOT EXISTS ix_assets_kind    ON assets(kind);
CREATE INDEX IF NOT EXISTS ix_assets_category ON assets(category);
"""

# kinds that are "container" nodes vs media files
KINDS = ["project", "episode", "scene", "shot", "line",
         "image", "video", "audio", "subtitle", "bgm", "cover"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Catalog:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ------------------------------------------------------------------ conn
    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=30)
        c.row_factory = sqlite3.Row
        return c

    def _init_schema(self) -> None:
        with _lock, self._conn() as c:
            c.executescript(SCHEMA)

    # ---------------------------------------------------------------- upsert
    def upsert(self, *, project: str, kind: str, ref: str = "", ep_index: int = 0,
               parent: str = "", title: str = "", text: str = "", summary: str = "",
               category: str = "", tags: Optional[list[str]] = None, path: str = "",
               status: str = "", extra: Optional[dict] = None) -> int:
        tags_s = ",".join(dict.fromkeys([t for t in (tags or []) if t]))
        extra_s = json.dumps(extra or {}, ensure_ascii=False)
        with _lock, self._conn() as c:
            cur = c.execute(
                """INSERT INTO assets
                   (project,kind,ref,ep_index,parent,title,text,summary,category,
                    tags,path,status,extra,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(project,kind,ref) DO UPDATE SET
                     ep_index=excluded.ep_index, parent=excluded.parent,
                     title=excluded.title, text=excluded.text,
                     summary=COALESCE(NULLIF(excluded.summary,''), assets.summary),
                     category=COALESCE(NULLIF(excluded.category,''), assets.category),
                     tags=CASE WHEN excluded.tags<>'' THEN excluded.tags ELSE assets.tags END,
                     path=excluded.path, status=excluded.status,
                     extra=excluded.extra, updated_at=excluded.updated_at""",
                (project, kind, ref, ep_index, parent, title, text, summary,
                 category, tags_s, path, status, extra_s, _now()),
            )
            return cur.lastrowid or 0

    def clear_project(self, project: str) -> None:
        with _lock, self._conn() as c:
            c.execute("DELETE FROM assets WHERE project=?", (project,))

    def set_tags(self, asset_id: int, tags: list[str], category: str = "",
                 summary: str = "") -> None:
        tags_s = ",".join(dict.fromkeys([t for t in tags if t]))
        with _lock, self._conn() as c:
            c.execute(
                """UPDATE assets SET tags=?,
                     category=CASE WHEN ?<>'' THEN ? ELSE category END,
                     summary=CASE WHEN ?<>'' THEN ? ELSE summary END,
                     updated_at=?
                   WHERE id=?""",
                (tags_s, category, category, summary, summary, _now(), asset_id),
            )

    # ----------------------------------------------------------------- query
    def projects(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                """SELECT project,
                          COUNT(*) AS n,
                          SUM(kind='episode') AS episodes,
                          SUM(kind='shot')    AS shots,
                          SUM(kind='video')   AS videos,
                          MAX(updated_at)     AS updated_at
                   FROM assets GROUP BY project ORDER BY updated_at DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    def all_tags(self, project: Optional[str] = None) -> dict[str, int]:
        q = "SELECT tags FROM assets"
        args: tuple = ()
        if project:
            q += " WHERE project=?"
            args = (project,)
        counts: dict[str, int] = {}
        with self._conn() as c:
            for (tags_s,) in c.execute(q, args).fetchall():
                for t in (tags_s or "").split(","):
                    t = t.strip()
                    if t:
                        counts[t] = counts.get(t, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def search(self, *, project: Optional[str] = None, keywords: Optional[list[str]] = None,
               tags: Optional[list[str]] = None, category: str = "",
               kinds: Optional[list[str]] = None, status: str = "",
               limit: int = 60) -> list[dict]:
        """Deterministic filter. keywords match title/text/summary/tags (LIKE,
        AND-combined); tags are OR-matched against the tag list."""
        where, args = [], []
        if project:
            where.append("project=?"); args.append(project)
        if category:
            where.append("category=?"); args.append(category)
        if status:
            where.append("status=?"); args.append(status)
        if kinds:
            where.append(f"kind IN ({','.join('?'*len(kinds))}); ".replace("; ", ""))
            args.extend(kinds)
        for kw in (keywords or []):
            kw = kw.strip()
            if not kw:
                continue
            where.append("(title LIKE ? OR text LIKE ? OR summary LIKE ? OR tags LIKE ?)")
            like = f"%{kw}%"
            args.extend([like, like, like, like])
        if tags:
            conds = []
            for t in tags:
                t = t.strip()
                if not t:
                    continue
                conds.append("(',' || tags || ',') LIKE ?")
                args.append(f"%,{t},%")
            if conds:
                where.append("(" + " OR ".join(conds) + ")")
        sql = "SELECT * FROM assets"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ep_index, kind, id LIMIT ?"
        args.append(limit)
        with self._conn() as c:
            rows = c.execute(sql, args).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get(self, asset_id: int) -> Optional[dict]:
        with self._conn() as c:
            r = c.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
        return _row_to_dict(r) if r else None

    def get_project_assets(self, project: str, kind: Optional[str] = None) -> list[dict]:
        q = "SELECT * FROM assets WHERE project=?"
        args: list = [project]
        if kind:
            q += " AND kind=?"
            args.append(kind)
        q += " ORDER BY ep_index, kind, id"
        with self._conn() as c:
            return [_row_to_dict(r) for r in c.execute(q, args).fetchall()]

    # ------------------------------------------------------------- reindex
    def reindex_project(self, store: ProjectStore, *, with_ai: bool = False,
                        brain=None, progress=None) -> dict:
        """Rebuild every row for one project from its project.json.

        with_ai=True additionally asks the Brain to tag/classify text-bearing
        nodes (episode logline, scene summary, shot action, line text). Media
        rows inherit their parent shot/episode tags so filters stay coherent.
        """
        proj: Project = store.load()
        slug = store.root.name
        self.clear_project(slug)
        counts: dict[str, int] = {}

        def bump(k): counts[k] = counts.get(k, 0) + 1

        def _tag(text: str, hint: str) -> dict:
            if not (with_ai and brain and text.strip()):
                return {"tags": [], "category": "", "summary": ""}
            return brain.tag(text, extra_hint=hint)

        # project-level row
        pt = _tag(f"{proj.meta.title} {proj.meta.synopsis} "
                  f"{' '.join(c.name + c.role for c in proj.characters)}",
                  "整部短剧的题材/风格")
        self.upsert(project=slug, kind="project", ref=proj.meta.name,
                    title=proj.meta.title or proj.meta.name,
                    text=proj.meta.synopsis, summary=pt["summary"],
                    category=pt["category"] or proj.art_direction.genre,
                    tags=pt["tags"] + [proj.art_direction.genre, proj.art_direction.style],
                    path="project.json", status=_s(proj.stage_status.get("compose")),
                    extra={"genre": proj.art_direction.genre,
                           "style": proj.art_direction.style,
                           "characters": [c.name for c in proj.characters]})
        bump("project")

        # character & location reference images (project-level, generated in the
        # character stage) — without these the asset browser can't show 定妆三视图 /
        # 场景参考图 even though they exist on disk and in project.json.
        cst = _s(proj.stage_status.get("character"))
        for c in proj.characters:
            ctags = [c.name] + ([c.role] if c.role else [])
            seen: set[str] = set()
            for img in list(c.refs()) + ([c.ref_sheet] if c.ref_sheet else []):
                if img and img not in seen:
                    seen.add(img)
                    _media(self, slug, "image", f"{c.name}/{Path(img).name}", 0,
                           img, ctags, "角色参考", cst, bump)
        for loc in proj.locations:
            for img in loc.ref_images:
                if img:
                    _media(self, slug, "image", f"{loc.name}/{Path(img).name}", 0,
                           img, [loc.name], "场景参考", cst, bump)

        for ep in proj.episodes:
            ep_tags_base = [f"第{ep.index}集"]
            t = _tag(f"{ep.title} {ep.logline} {ep.hook} {' '.join(ep.key_beats)}",
                     "这一集的剧情/情绪")
            self.upsert(project=slug, kind="episode", ref=ep.id, ep_index=ep.index,
                        title=ep.title or f"第{ep.index}集", text=ep.logline,
                        summary=t["summary"], category=t["category"],
                        tags=ep_tags_base + t["tags"],
                        path=ep.video_path or store.rel(store.episode_video_path(ep)),
                        status=_s(ep.status),
                        extra={"hook": ep.hook, "scenes": len(ep.scenes),
                               "shots": ep.total_shots})
            bump("episode")

            # final media for the episode
            _media(self, slug, "video", ep.id, ep.index, ep.video_path,
                   ep_tags_base + t["tags"], "成片", _s(ep.status), bump)
            _media(self, slug, "cover", ep.id, ep.index, ep.cover_path,
                   ep_tags_base + t["tags"], "封面", _s(ep.status), bump)
            _media(self, slug, "subtitle", ep.id, ep.index, ep.subtitle_path or ep.ass_path,
                   ep_tags_base + t["tags"], "字幕", _s(ep.status), bump)
            _media(self, slug, "bgm", ep.id, ep.index, ep.bgm_path,
                   ep_tags_base + t["tags"], "配乐", _s(ep.status), bump)
            _media(self, slug, "audio", ep.id, ep.index, ep.voice_path,
                   ep_tags_base + t["tags"], "配音", _s(ep.status), bump)

            for sc in ep.scenes:
                st = _tag(f"{sc.location} {sc.summary} 情绪:{sc.mood} "
                          + " ".join(l.text for l in sc.lines[:8]),
                          "这场戏的时空/情绪/类型")
                sc_tags = ep_tags_base + [sc.time_of_day, sc.mood] + st["tags"]
                self.upsert(project=slug, kind="scene", ref=sc.id, ep_index=ep.index,
                            parent=ep.id, title=sc.summary[:40] or sc.location,
                            text=sc.summary + " " + " ".join(l.text for l in sc.lines),
                            summary=st["summary"], category=st["category"] or sc.mood,
                            tags=[x for x in sc_tags if x], path="",
                            status=_s(sc.status),
                            extra={"location": sc.location, "time": sc.time_of_day,
                                   "mood": sc.mood, "shots": len(sc.shots)})
                bump("scene")

                for sh in sc.shots:
                    sht = _tag(f"{sh.action} 景别:{sh.shot_type.value} "
                               f"运镜:{sh.camera_move} 角色:{' '.join(sh.characters)} "
                               f"提示词:{sh.prompt}", "这个分镜的画面内容")
                    sh_tags = sc_tags + [sh.shot_type.value, sh.camera_move] + sht["tags"]
                    self.upsert(project=slug, kind="shot", ref=sh.id, ep_index=ep.index,
                                parent=sc.id, title=sh.action[:40],
                                text=sh.action + " " + sh.prompt,
                                summary=sht["summary"], category=sht["category"] or sh.shot_type.value,
                                tags=[x for x in sh_tags if x],
                                path=sh.video_path or sh.image_path,
                                status=_s(sh.status),
                                extra={"shot_type": sh.shot_type.value,
                                       "camera": sh.camera_move,
                                       "characters": sh.characters,
                                       "prompt": sh.prompt, "seed": sh.seed})
                    bump("shot")
                    _media(self, slug, "image", sh.id, ep.index, sh.image_path,
                           [x for x in sh_tags if x], "画面", _s(sh.status), bump,
                           parent=sc.id)
                    _media(self, slug, "video", sh.id, ep.index, sh.video_path,
                           [x for x in sh_tags if x], "视频", _s(sh.status), bump,
                           parent=sc.id)

                for ln in sc.lines:
                    lt = _tag(f"{ln.speaker}: {ln.text} 情绪:{ln.emotion}",
                              "这句台词的情绪/类型")
                    self.upsert(project=slug, kind="line", ref=ln.id, ep_index=ep.index,
                                parent=sc.id, title=ln.speaker,
                                text=ln.text, summary=lt["summary"],
                                category=lt["category"] or ln.kind.value,
                                tags=[x for x in (ep_tags_base + [ln.speaker, ln.emotion,
                                                                  ln.kind.value] + lt["tags"]) if x],
                                path=ln.audio_path, status=_s(ln.status),
                                extra={"speaker": ln.speaker, "emotion": ln.emotion,
                                       "kind": ln.kind.value, "duration": ln.duration})
                    bump("line")
                    _media(self, slug, "audio", ln.id, ep.index, ln.audio_path,
                           [x for x in (ep_tags_base + [ln.speaker]) if x], "配音",
                           _s(ln.status), bump, parent=sc.id, ref_prefix="line")

            if progress:
                progress(ep.index, len(proj.episodes))

        return {"project": slug, "counts": counts,
                "total": sum(counts.values()), "with_ai": with_ai}


def _media(cat: Catalog, project: str, kind: str, ref: str, ep_index: int,
           path: str, tags: list[str], category: str, status: str, bump,
           parent: str = "", ref_prefix: str = "") -> None:
    """Insert a media-file row only when the file path is set."""
    if not path:
        return
    r = f"{ref_prefix}{ref}" if ref_prefix else ref
    cat.upsert(project=project, kind=kind, ref=r, ep_index=ep_index, parent=parent,
               title=Path(path).name, text="", category=category,
               tags=[x for x in tags if x], path=path, status=status,
               extra={"file": Path(path).name})
    bump(kind)


def _s(status) -> str:
    if isinstance(status, Status):
        return status.value
    return str(status or "")


def _row_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["tags"] = [t for t in (d.get("tags") or "").split(",") if t]
    try:
        d["extra"] = json.loads(d.get("extra") or "{}")
    except json.JSONDecodeError:
        d["extra"] = {}
    return d


def open_catalog(cfg, root: Optional[Path] = None) -> Catalog:
    """Resolve cfg.ai.catalog_db against the projects dir / cwd and open it."""
    db = Path(cfg.ai.catalog_db)
    if not db.is_absolute():
        base = Path(root) if root else Path(cfg.pipeline.output_dir)
        db = base / db
    return Catalog(db)
