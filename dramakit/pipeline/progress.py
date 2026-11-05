"""What the run is doing right now, for the console to show.

A stage that is asked for four scenes at once has four requests in
flight, and the person watching wants to see that - a bar that moves
says nothing about how wide the work is, or how many of the calls are
failing.  So every stage says what it has started, what is running,
what is done and what failed, and the console reads it.

The numbers are kept in a sidecar file next to the project, not in
project.json: the file belongs to the pipeline's save cycle, and this
changes several times a minute.  Writing it is best effort - a
progress that cannot be written must not stop the work.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Optional

# The name of the sidecar file the console reads.
FILE_NAME = ".progress.json"


class Progress:
    """The running tally of one project.

    Every stage that asks the model for something registers itself
    here, and every job says when it starts and when it ends.  The
    console asks for the whole lot and draws it.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.stages: dict[str, dict] = {}
        self.lanes: dict[str, str] = {}

    # -- one stage's record ------------------------------------------------
    def _rec(self, stage: str) -> dict:
        return self.stages.setdefault(stage, {
            "done": 0, "total": 0, "started": 0, "failed": 0,
            "running": 0, "concurrency": 0, "ts": 0, "since": 0,
        })

    # -- what the stages say ---------------------------------------------
    def begin(self, stage: str, total: int, concurrency: int = 0) -> None:
        """A stage starts: this is how much work it has."""
        with self.lock:
            rec = self._rec(stage)
            rec.update(total=int(total), started=0, done=0, failed=0,
                       running=0, concurrency=int(concurrency),
                       since=int(time.time()))
            self._write()

    def began(self, stage: str) -> None:
        """One job of this stage is on its way."""
        with self.lock:
            rec = self._rec(stage)
            rec["started"] += 1
            rec["running"] += 1
            self._write()

    def finished(self, stage: str, ok: bool = True) -> None:
        """One job of this stage is done - or has failed."""
        with self.lock:
            rec = self._rec(stage)
            rec["running"] = max(0, rec["running"] - 1)
            if ok:
                rec["done"] += 1
            else:
                rec["failed"] += 1
            self._write()

    def note(self, stage: str, **fields) -> None:
        """Say something else about a stage."""
        with self.lock:
            self._rec(stage).update(fields)
            self._write()

    def lane(self, lane: str, stage: str) -> None:
        """Which stage a lane is working on."""
        with self.lock:
            self.lanes[lane] = stage
            self._write()

    def lane_done(self, lane: str) -> None:
        with self.lock:
            self.lanes.pop(lane, None)
            self._write()

    # -- what the console reads -------------------------------------------
    def snapshot(self) -> dict:
        """The whole lot, as the console wants it."""
        with self.lock:
            stages = {k: dict(v) for k, v in self.stages.items()}
            lanes = dict(self.lanes)
        inflight = sum(int(s.get("running") or 0) for s in stages.values())
        started = sum(int(s.get("started") or 0) for s in stages.values())
        done = sum(int(s.get("done") or 0) for s in stages.values())
        failed = sum(int(s.get("failed") or 0) for s in stages.values())
        total = sum(int(s.get("total") or 0) for s in stages.values())
        return {
            "stages": stages,
            "lanes": lanes,
            "inflight": inflight,
            "started": started,
            "done": done,
            "failed": failed,
            "total": total,
            "ts": int(time.time()),
        }

    # -- the file ----------------------------------------------------------
    def _write(self) -> None:
        """Put the tally in the sidecar file.

        The shape the console already knew is kept - the stage's done
        and total - and the rest is added beside it, so an older page
        still reads it.
        """
        try:
            data: dict = {}
            if self.path.exists():
                try:
                    data = json.loads(self.path.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    data = {}
            for stage, rec in self.stages.items():
                data[stage] = {
                    "done": rec["done"], "total": rec["total"],
                    "started": rec["started"], "failed": rec["failed"],
                    "running": rec["running"],
                    "concurrency": rec["concurrency"],
                    "since": rec["since"], "ts": rec["ts"] or int(time.time()),
                }
            data["_lanes"] = dict(self.lanes)
            data["_inflight"] = sum(int(s.get("running") or 0)
                                    for s in self.stages.values())
            data["_ts"] = int(time.time())
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, ensure_ascii=False),
                                 encoding="utf-8")
        except Exception:  # noqa: BLE001
            # a progress that cannot be written is not worth stopping for
            pass


def read(path: Path) -> dict:
    """What the sidecar file says, for the console."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def attach(ctx) -> Progress:
    """The tally of this project, made once."""
    prog: Optional[Progress] = getattr(ctx, "_progress", None)
    if prog is None:
        prog = Progress(Path(ctx.store.root) / FILE_NAME)
        ctx._progress = prog
    return prog
