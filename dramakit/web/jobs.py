from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class JobStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    project TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    progress_json TEXT,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    finished_at REAL,
                    updated_at REAL NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_updated ON jobs(updated_at DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project, updated_at DESC)")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _clean(job: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in job.items() if k != "stop"}

    def save(self, job: dict[str, Any]) -> None:
        row = self._clean(job)
        now = time.time()
        row.setdefault("created_at", now)
        row["updated_at"] = now
        with self.lock, self._connect() as db:
            db.execute("""
                INSERT INTO jobs (
                    id, kind, project, status, result_json, error, progress_json,
                    created_at, started_at, finished_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind, project=excluded.project, status=excluded.status,
                    result_json=excluded.result_json, error=excluded.error,
                    progress_json=excluded.progress_json, started_at=excluded.started_at,
                    finished_at=excluded.finished_at, updated_at=excluded.updated_at
            """, (
                row["id"], row.get("kind", "job"), row.get("project", ""),
                row.get("status", "queued"), self._json(row.get("result")),
                row.get("error"), self._json(row.get("progress") or {}),
                row["created_at"], row.get("started_at"), row.get("finished_at"), now,
            ))

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        out = dict(row)
        for source, target in (("result_json", "result"), ("progress_json", "progress")):
            raw = out.pop(source, None)
            try:
                out[target] = json.loads(raw) if raw else ({} if target == "progress" else None)
            except (TypeError, ValueError):
                out[target] = {} if target == "progress" else None
        return out

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._row(row) if row else None

    def list(self, *, project: str = "", status: str = "", limit: int = 100) -> list[dict[str, Any]]:
        clauses, params = [], []
        if project:
            clauses.append("project=?")
            params.append(project)
        if status:
            clauses.append("status=?")
            params.append(status)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(max(1, min(int(limit), 500)))
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM jobs" + where + " ORDER BY created_at DESC LIMIT ?", params
            ).fetchall()
        return [self._row(row) for row in rows]

    def active(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM jobs WHERE status IN ('queued','running') ORDER BY created_at"
            ).fetchall()
        return [self._row(row) for row in rows]

    def settle_leftovers(self) -> int:
        now = time.time()
        with self.lock, self._connect() as db:
            cur = db.execute("""
                UPDATE jobs SET status='interrupted',
                    error=COALESCE(NULLIF(error, ''), '服务重启，任务已中断'),
                    finished_at=?, updated_at=?
                WHERE status IN ('queued','running')
            """, (now, now))
            return cur.rowcount
