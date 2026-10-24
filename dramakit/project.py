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
import re
import shutil
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


class ProjectStore:
    """Read/write helper bound to one project directory."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.manifest = self.root / "project.json"
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
        with open(self.manifest, "r", encoding="utf-8") as f:
            return Project.model_validate(json.load(f))

    def save(self, proj: Project) -> None:
        proj.meta.updated_at = now()
        tmp = self.manifest.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(proj.model_dump(), f, ensure_ascii=False, indent=2)
        tmp.replace(self.manifest)

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

    def character_dir(self, name: str) -> Path:
        d = self.root / "characters" / slugify(name)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def character_ref_path(self, name: str, view: str, ext: str = "png") -> Path:
        return self.character_dir(name) / f"{slugify(view) or 'ref'}.{ext}"

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
