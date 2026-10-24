"""Rich-based logging shared across the CLI and pipeline."""
from __future__ import annotations

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (BarColumn, Progress, SpinnerColumn, TextColumn,
                           TimeElapsedColumn, TimeRemainingColumn)

console = Console()
err_console = Console(stderr=True)


def setup_logging(verbose: bool = True, logfile: str | Path | None = None) -> None:
    level = logging.INFO if verbose else logging.WARNING
    handlers: list[logging.Handler] = [
        RichHandler(console=console, rich_tracebacks=True, show_path=False)
    ]
    if logfile:
        Path(logfile).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(logfile, encoding="utf-8"))
    logging.basicConfig(level=level, format="%(message)s", handlers=handlers)
    # quiet noisy libs
    for name in ("httpx", "httpcore", "websockets", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )
