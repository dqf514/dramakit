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


def _shot_line_map(shots, n_lines: int, max_shot: float = 0.0,
                   line_durs: list[float] | None = None) -> dict[str, list[int]] | None:
    """Which lines each shot carries, and who gets the leftovers.

    The storyboard says which lines a shot covers. When it does, the shot
    lasts exactly as long as those lines, so the cut lands on a line boundary
    and the camera is on the person who is talking.

    A shot cannot hold more than the longest video the model can make, so a
    shot that claims too much has to give the tail of it back.
    """
    if not shots or n_lines <= 0:
        return None
    durs = line_durs or []
    claimed: dict[str, list[int]] = {}
    used: set[int] = set()
    for sh in shots:
        idxs = []
        for n in sh.line_indices:
            if 1 <= n <= n_lines and n not in used:
                idxs.append(n)
                used.add(n)
        if idxs and max_shot > 0 and durs:
            # give back the tail that does not fit into one clip
            total = 0.0
            keep = []
            for n in idxs:
                d = durs[n - 1] if n - 1 < len(durs) else 0.0
                if keep and total + d > max_shot:
                    break
                total += d
                keep.append(n)
            for n in idxs[len(keep):]:
                used.discard(n)
            idxs = keep
        if idxs:
            claimed[sh.id] = idxs
    if not claimed:
        return None
    missing = [n for n in range(1, n_lines + 1) if n not in used]
    if missing:
        # hand each leftover to the shot that sits closest to it in the list -
        # a shot with no lines of its own (an establishing shot) takes it
        # first, so the opening line is not dragged into a later close-up
        n_shots = len(shots)
        for n in missing:
            want = (n - 0.5) / n_lines * n_shots
            empty = [sh for sh in shots if not claimed.get(sh.id)]
            if empty:
                best = min(empty, key=lambda sh: abs(sh.index - want))
            else:
                best = min(shots, key=lambda sh: abs(min(claimed.get(sh.id) or [n]) - n))
            claimed.setdefault(best.id, []).append(n)
        for sid in claimed:
            claimed[sid].sort()
    return claimed


def _assign_by_cast(shots, line_durs: list[float],
                    speakers: list[str]) -> dict[str, list[int]] | None:
    """Work out which lines each shot carries when the storyboard did not say.

    The lines go to the shot that has the speaker in frame, which keeps the
    cut on the dialogue and the picture on the person who is talking. No
    shot gets more than two lines, or one shot ends up carrying the whole
    conversation.
    """
    if not shots or not speakers:
        return None
    n = len(speakers)
    claimed: dict[str, list[int]] = {}
    used: set[int] = set()
    for k, sp in enumerate(speakers):
        cands = [sh for sh in shots
                 if sp in (sh.characters or []) and len(claimed.get(sh.id, [])) < 2]
        if not cands:
            continue
        want = (k + 0.5) / n * len(shots)
        best = min(cands, key=lambda sh: abs(sh.index - want))
        claimed.setdefault(best.id, []).append(k + 1)
        used.add(k)
    # nobody took a line: put it in the shot with the fewest lines
    for k in range(n):
        if k in used:
            continue
        free = [sh for sh in shots if len(claimed.get(sh.id, [])) < 2]
        best = (min(free, key=lambda sh: len(claimed.get(sh.id, []))) if free
                else min(shots, key=lambda sh: len(claimed.get(sh.id, []))))
        claimed.setdefault(best.id, []).append(k + 1)
        used.add(k)
    for sid in claimed:
        claimed[sid].sort()
    return claimed


def build_timeline(ep: Episode, min_shot: float = 1.0,
                   max_shot: float = 0.0) -> Timeline:
    timed_scenes: list[TimedScene] = []
    cursor = 0.0
    for sc in ep.scenes:
        # 1) dialogue length of the scene. Narration is shown on screen but never
        #    spoken, so it must not stretch the scene's audio track.
        spoken = [l for l in sc.lines if not is_narration(l)]
        narration = [l for l in sc.lines if is_narration(l)]
        raw_lines = [(_line_duration(l), l) for l in spoken]
        scene_audio = round(sum(d for d, _ in raw_lines), 3)

        # 2) how long each shot lasts. When the storyboard says which lines a
        #    shot carries, the shot is exactly as long as those lines - the cut
        #    lands on the dialogue instead of drifting through it.
        line_map = _shot_line_map(sc.shots, len(raw_lines), max_shot=max_shot,
                                   line_durs=[d for d, _ in raw_lines])
        if line_map is None and sc.shots:
            # the storyboard did not say: work it out from who is in frame
            line_map = _assign_by_cast(sc.shots, [d for d, _ in raw_lines],
                                       [l.speaker for _, l in raw_lines])
        shot_durs: list[float] = []
        for sh in sc.shots:
            d = max(sh.duration, min_shot)
            if line_map:
                idxs = line_map.get(sh.id) or []
                owned = sum(raw_lines[i - 1][0] for i in idxs)
                if owned > 0:
                    d = owned
            shot_durs.append(d)
        shot_sum = round(sum(shot_durs), 3)
        scene_dur = max(scene_audio, shot_sum, min_shot)

        # 3) normalize shot durations to fill the scene exactly
        timed_shots: list[TimedShot] = []
        if sc.shots:
            scale = scene_dur / shot_sum if shot_sum > 0 else 1.0
            shot_cursor = cursor
            for i, sh in enumerate(sc.shots):
                d = shot_durs[i] * scale
                if i == len(sc.shots) - 1:               # absorb rounding on last
                    d = scene_dur - (shot_cursor - cursor)
                d = max(d, min_shot)
                timed_shots.append(TimedShot(sh, round(shot_cursor, 3), round(d, 3)))
                shot_cursor += d

        # 4) place the spoken lines: inside the shot that carries them, one
        #    after another, so the picture and the dialogue stay together
        timed_lines: list[TimedLine] = []
        if line_map and timed_shots:
            by_shot: dict[str, list[int]] = line_map
            for ts in timed_shots:
                idxs = sorted(by_shot.get(ts.shot.id) or [])
                inner = ts.start
                for i in idxs:
                    d, l = raw_lines[i - 1]
                    share = d * (ts.duration / max(
                        sum(raw_lines[j - 1][0] for j in idxs), 1e-6))
                    timed_lines.append(TimedLine(l, sc.id, round(inner, 3),
                                                 round(inner + share, 3)))
                    inner += share
        else:
            line_cursor = cursor
            for d, l in raw_lines:
                timed_lines.append(TimedLine(l, sc.id, round(line_cursor, 3),
                                             round(line_cursor + d, 3)))
                line_cursor += d
        timed_lines.sort(key=lambda t: t.start)

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
