"""Project store: owns the on-disk layout and the project.json manifest.

Directory layout (all paths inside a project are stored RELATIVE to root):

    projects/<slug>/
      project.json            manifest (the Project model)
      source/                 original novel + cleaned text
      audio/                  per-line TTS clips   (line_<id>.mp3)
      images/                 per-shot keyframes   (shot_<id>.png)
      video/                  per-shot clips       (shot_<id>.mp4)
      subs/                   per-episode .srt / .ass
      bgm/                    per-episode music
      episodes/               final rendered ep_001.mp4 ...
      covers/                 ep_001_cover.jpg
      logs/
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Episode, Project, ProjectMeta, Scene, Shot, Status

SUBDIRS = [
    "source", "audio", "images", "video", "subs",
    "bgm", "episodes", "covers", "logs", "characters",
]


def slugify(name: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name.strip()).strip("-")
    return s or "project"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# The lock on a project file is on the file, not on whoever opened it:
# the console opens the project again on every request, and a run holds
# two copies of it at once - the run's own and the one that puts an
# episode together.  A lock that belonged to the object would let those
# write over each other, and on Windows the second write fails outright
# because the file it wants to replace is open elsewhere.
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def lock_for(path: str | Path) -> threading.RLock:
    """The lock that belongs to one project file."""
    key = str(Path(path).resolve()).lower()
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[key] = lock
        return lock


def _replace(tmp: Path, dst: Path, tries: int = 10) -> None:
    """Put the new file over the old one, and wait out the readers.

    Windows will not rename a file over another one that somebody has
    open - and the console reads the project on every request, so the
    window is small but real.  A rename that fails for that reason is
    not a failure: the reader will be gone in a moment.
    """
    for attempt in range(tries):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(0.02 * (attempt + 1))
        except OSError:
            # the temporary file is ours: do not leave it behind
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise


def _read_json(path: Path, tries: int = 10) -> dict:
    """Read a JSON file, waiting out a writer that is renaming over it."""
    for attempt in range(tries):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(0.02 * (attempt + 1))
    return {}


class ProjectStore:
    """Read/write helper bound to one project directory."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.manifest = self.root / "project.json"
        # the lock belongs to the file: everybody who opens this project
        # shares it, whoever opened it
        self.lock = lock_for(self.manifest)
        for d in SUBDIRS:
            (self.root / d).mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- create
    @classmethod
    def create(cls, output_dir: str | Path, name: str,
               source_file: Optional[str | Path] = None) -> "ProjectStore":
        slug = slugify(name)
        root = Path(output_dir) / slug
        # avoid clobbering: append -2, -3 ...
        n = 2
        base = root
        while root.exists() and (root / "project.json").exists():
            root = Path(f"{base}-{n}")
            n += 1
        store = cls(root)
        proj = Project(
            meta=ProjectMeta(
                name=name,
                source_file=str(source_file) if source_file else "",
                title=name,
                created_at=now(),
                updated_at=now(),
            )
        )
        store.save(proj)
        if source_file and Path(source_file).exists():
            dest = store.root / "source" / Path(source_file).name
            shutil.copy2(source_file, dest)
        return store

    @classmethod
    def open(cls, root: str | Path) -> "ProjectStore":
        store = cls(root)
        if not store.manifest.exists():
            raise FileNotFoundError(f"No project.json in {root}")
        return store

    # ---------------------------------------------------------------- persist
    def load(self) -> Project:
        with self.lock:
            return Project.model_validate(_read_json(self.manifest))

    def save(self, proj: Project) -> None:
        """Write the whole manifest, whole or not at all.

        The file is written to a temporary name and renamed over the
        old one, so a reader sees either the old project or the new one
        and never half of each.  The temporary name carries the writer's
        own id, because two writers of the same project would otherwise
        be writing the same temporary file and the reader would see the
        mix of two projects.
        """
        with self.lock:
            proj.meta.updated_at = now()
            tmp = self.manifest.with_suffix(
                f".json.{os.getpid()}.{threading.get_ident()}.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(proj.model_dump(), f, ensure_ascii=False, indent=2)
            _replace(tmp, self.manifest)

    # ---------------------------------------------------------------- helpers
    def rel(self, p: str | Path) -> str:
        """Absolute path -> project-relative string."""
        try:
            return str(Path(p).resolve().relative_to(self.root.resolve())).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    def abs(self, rel: str) -> Path:
        return self.root / rel

    def audio_path(self, line_id: str) -> Path:
        return self.root / "audio" / f"line_{line_id}.mp3"

    def cleaned_text_path(self) -> Path:
        return self.root / "source" / "cleaned.txt"

    def chapters_path(self) -> Path:
        return self.root / "source" / "chapters.json"

    def episode_source_path(self, index: int) -> Path:
        return self.root / "source" / f"ep_{index:03d}.txt"

    def image_path(self, shot_id: str) -> Path:
        return self.root / "images" / f"shot_{shot_id}.png"

    def end_image_path(self, shot_id: str) -> Path:
        return self.root / "images" / f"shot_{shot_id}_end.png"

    def video_path(self, shot_id: str) -> Path:
        return self.root / "video" / f"shot_{shot_id}.mp4"

    def character_voice_path(self, name: str, ext: str = "mp3") -> Path:
        """Where a character's voice sample lives, beside their pictures.

        The sample is made with the rest of the character, so it sits with
        the rest of the character - and, like the pictures, it is per
        season, because a look that changed may have a voice that did not.
        """
        return self.character_dir(name) / f"voice.{ext}"

    def character_dir(self, name: str, season: int = 0) -> Path:
        """Where a character's reference pictures live.

        A season has its own look. A character can change across a long
        story - grow up, change sides, be scarred - so each season draws
        its own reference pictures rather than overwriting the last ones.
        Season 1 pictures stay where they were, so an episode made in
        season 1 keeps drawing the face it was made with. Season 0 is the
        un-seasoned case: a project that predates seasons.
        """
        base = self.root / "characters" / slugify(name)
        if season and season > 1:
            base = base / f"s{season}"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def character_ref_path(self, name: str, view: str, ext: str = "png",
                           season: int = 0) -> Path:
        return self.character_dir(name, season) / f"{slugify(view) or 'ref'}.{ext}"

    def location_dir(self, name: str) -> Path:
        d = self.root / "locations" / slugify(name)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def location_ref_path(self, name: str, view: str = "ref", ext: str = "png") -> Path:
        return self.location_dir(name) / f"{slugify(view) or 'ref'}.{ext}"

    def episode_video_path(self, ep: Episode) -> Path:
        return self.root / "episodes" / f"ep_{ep.index:03d}.mp4"

    def subtitle_path(self, ep: Episode, ext: str = "srt") -> Path:
        return self.root / "subs" / f"ep_{ep.index:03d}.{ext}"

    def bgm_path(self, ep: Episode) -> Path:
        return self.root / "bgm" / f"ep_{ep.index:03d}.mp3"

    def cover_path(self, ep: Episode) -> Path:
        return self.root / "covers" / f"ep_{ep.index:03d}_cover.jpg"

    def project_cover_path(self) -> Path:
        """The picture of the drama itself: the key art with the title on it."""
        return self.root / "covers" / "project_cover.jpg"

    def log_path(self, name: str) -> Path:
        return self.root / "logs" / f"{name}.log"

    # ---------------------------------------------------------------- status
    @staticmethod
    def is_done(node) -> bool:
        return getattr(node, "status", Status.PENDING) == Status.DONE

    def pending_shots(self, proj: Project, episodes: Optional[list[int]] = None):
        for ep in proj.episodes:
            if episodes and ep.index not in episodes:
                continue
            for sc in ep.scenes:
                for sh in sc.shots:
                    yield ep, sc, sh

    def summary(self, proj: Project) -> dict:
        return {
            "episodes": len(proj.episodes),
            "scenes": sum(len(e.scenes) for e in proj.episodes),
            "shots": proj.total_shots,
            "characters": len(proj.characters),
            "shots_with_visual": sum(
                1 for _, _, sh in self.pending_shots(proj) if sh.has_visual
            ),
        }
