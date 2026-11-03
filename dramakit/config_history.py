from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from .config import Config


_HISTORY_RE = re.compile(r"^[a-zA-Z0-9_.-]+\.yaml$")


def _history_dir(path: str | Path) -> Path:
    return Path(path).resolve().parent / ".history"


def snapshot(path: str | Path, *, keep: int = 30) -> str:
    source = Path(path).resolve()
    if not source.is_file():
        return ""
    history = _history_dir(source)
    history.mkdir(parents=True, exist_ok=True)
    target = history / f"{source.stem}-{time.time_ns()}.yaml"
    shutil.copy2(source, target)
    versions = sorted(history.glob(f"{source.stem}-*.yaml"), reverse=True)
    for old in versions[max(1, keep):]:
        old.unlink(missing_ok=True)
    return target.name


def versions(path: str | Path) -> list[dict]:
    source = Path(path).resolve()
    history = _history_dir(source)
    if not history.exists():
        return []
    out = []
    for item in sorted(history.glob(f"{source.stem}-*.yaml"), reverse=True):
        stat = item.stat()
        out.append({"id": item.name, "created_at": stat.st_mtime,
                    "bytes": stat.st_size})
    return out


def restore(path: str | Path, version_id: str) -> None:
    source = Path(path).resolve()
    if not _HISTORY_RE.fullmatch(version_id):
        raise ValueError("配置版本编号不合法")
    version = (_history_dir(source) / version_id).resolve()
    if version.parent != _history_dir(source) or not version.is_file():
        raise ValueError("配置版本不存在")
    Config.load(version)
    backup_id = snapshot(source)
    try:
        shutil.copy2(version, source)
        Config.load(source)
    except Exception:
        if backup_id:
            shutil.copy2(_history_dir(source) / backup_id, source)
        raise
