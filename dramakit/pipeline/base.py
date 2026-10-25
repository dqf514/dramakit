"""Pipeline context, stage base class and the A/V timeline model.

The timeline is the contract that keeps picture, dialogue and subtitles in sync:
  * dialogue (voice clips) drives each scene's real duration
  * a scene's shots are stretched proportionally to exactly cover that duration
  * subtitle cues use the per-line start/end computed here
So the compose stage and the subtitle stage always agree.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..config import Config
from ..models import Episode, Line, Project, Scene, Shot, Status, is_narration
from ..project import ProjectStore
from ..providers import Providers
from ..utils.text import estimate_reading_seconds


@dataclass
class TimedShot:
    shot: Shot
    start: float
    duration: float


@dataclass
class TimedLine:
    line: Line
    scene_id: str
    start: float
    end: float
    is_narration: bool = False


@dataclass
class TimedScene:
    scene: Scene
    start: float
    duration: float
    shots: list[TimedShot] = field(default_factory=list)
    lines: list[TimedLine] = field(default_factory=list)


@dataclass
class Timeline:
    episode: Episode
    scenes: list[TimedScene]
    duration: float

    @property
    def shots(self) -> list[TimedShot]:
        return [ts for sc in self.scenes for ts in sc.shots]

    @property
    def lines(self) -> list[TimedLine]:
        return [tl for sc in self.scenes for tl in sc.lines]


def _line_duration(line: Line) -> float:
    """Use measured audio duration if the voice stage ran; else estimate."""
    if line.duration and line.duration > 0:
        return line.duration
    return estimate_reading_seconds(line.text)


def build_timeline(ep: Episode, min_shot: float = 1.0) -> Timeline:
    timed_scenes: list[TimedScene] = []
    cursor = 0.0
    for sc in ep.scenes:
        # 1) dialogue length of the scene. Narration is shown on screen but never
        #    spoken, so it must not stretch the scene's audio track.
        spoken = [l for l in sc.lines if not is_narration(l)]
        narration = [l for l in sc.lines if is_narration(l)]
        raw_lines = [(_line_duration(l), l) for l in spoken]
        scene_audio = round(sum(d for d, _ in raw_lines), 3)
        # 2) minimum picture length from shot durations
        shot_sum = round(sum(max(sh.duration, min_shot) for sh in sc.shots), 3)
        scene_dur = max(scene_audio, shot_sum, min_shot)

        # 3) normalize shot durations to fill the scene exactly
        timed_shots: list[TimedShot] = []
        if sc.shots:
            scale = scene_dur / shot_sum if shot_sum > 0 else 1.0
            shot_cursor = cursor
            for i, sh in enumerate(sc.shots):
                d = max(sh.duration, min_shot) * scale
                if i == len(sc.shots) - 1:               # absorb rounding on last
                    d = scene_dur - (shot_cursor - cursor)
                d = max(d, min_shot)
                timed_shots.append(TimedShot(sh, round(shot_cursor, 3), round(d, 3)))
                shot_cursor += d

        # 4) place spoken lines back-to-back from scene start
        timed_lines: list[TimedLine] = []
        line_cursor = cursor
        for d, l in raw_lines:
            timed_lines.append(TimedLine(l, sc.id, round(line_cursor, 3),
                                         round(line_cursor + d, 3)))
            line_cursor += d

        # 5) narration: display-only cards spread across the scene. They overlap
        #    the spoken track in time but live in their own on-screen slot.
        if narration:
            slot = scene_dur / len(narration)
            for i, l in enumerate(narration):
                d = min(estimate_reading_seconds(l.text), slot * 0.85)
                s = cursor + i * slot
                timed_lines.append(TimedLine(l, sc.id, round(s, 3),
                                             round(s + d, 3), True))

        timed_scenes.append(TimedScene(sc, round(cursor, 3), round(scene_dur, 3),
                                       timed_shots, timed_lines))
        cursor += scene_dur
    return Timeline(ep, timed_scenes, round(cursor, 3))


# --------------------------------------------------------------------------- #
class Context:
    """Everything a stage needs. Holds the in-memory Project; call save() to persist."""

    def __init__(self, cfg: Config, store: ProjectStore,
                 providers: Optional[Providers] = None):
        self.cfg = cfg
        self.store = store
        self.providers = providers or Providers(cfg, store.root)
        self.project: Project = store.load()
        self.log: logging.Logger = logging.getLogger("dramakit")

    def save(self) -> None:
        self.store.save(self.project)

    # -- episode filtering ---------------------------------------------------
    def target_episodes(self) -> list[Episode]:
        only = self.cfg.pipeline.only_episodes
        if not only:
            return self.project.episodes
        return [e for e in self.project.episodes if e.index in only]

    def stage_done(self, ep: Episode, stage: str) -> bool:
        return ep.stage_status.get(stage) == Status.DONE

    def mark(self, ep: Episode, stage: str, status: Status) -> None:
        ep.stage_status[stage] = status

    # -- path helpers --------------------------------------------------------
    @property
    def root(self) -> Path:
        return self.store.root
