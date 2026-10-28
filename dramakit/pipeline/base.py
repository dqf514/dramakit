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


# a shot carries at most this much dialogue: a short drama cuts fast
SHOT_DIALOGUE_MAX = 3.5


def _line_duration(line: Line) -> float:
    """Use measured audio duration if the voice stage ran; else estimate."""
    if line.duration and line.duration > 0:
        return line.duration
    return estimate_reading_seconds(line.text)


def _shot_line_map(shots, n_lines: int, max_shot: float = 0.0,
                   line_durs: list[float] | None = None,
                   max_dialogue: float = 0.0) -> dict[str, list[int]] | None:
    """Which lines each shot carries, and who gets the leftovers.

    The storyboard says which lines a shot covers. When it does, the shot
    lasts exactly as long as those lines, so the cut lands on a line boundary
    and the camera is on the person who is talking.

    A shot cannot hold more than the longest video the model can make, and
    it cannot hold more than a few seconds of dialogue either - a short
    drama cuts fast. A shot that claims too much has to give it back.
    """
    if not shots or n_lines <= 0:
        return None
    durs = line_durs or []
    limit = max_shot if max_shot > 0 else 0.0
    if max_dialogue > 0:
        limit = max_dialogue if limit <= 0 else min(limit, max_dialogue)
    claimed: dict[str, list[int]] = {}
    used: set[int] = set()
    for sh in shots:
        idxs = []
        for n in sh.line_indices:
            if 1 <= n <= n_lines and n not in used:
                idxs.append(n)
                used.add(n)
        if idxs and limit > 0 and durs:
            # give back the tail that does not fit into one clip
            total = 0.0
            keep = []
            for n in idxs:
                d = durs[n - 1] if n - 1 < len(durs) else 0.0
                if keep and total + d > limit:
                    break
                total += d
                keep.append(n)
            for n in idxs[len(keep):]:
                used.discard(n)
            idxs = keep
        if len(idxs) > 2:
            # a short drama cuts fast: a shot carries at most two lines
            for n in idxs[2:]:
                used.discard(n)
            idxs = idxs[:2]
        if idxs:
            claimed[sh.id] = idxs
    if not claimed:
        return None
    missing = [n for n in range(1, n_lines + 1) if n not in used]
    if missing:
        # hand each leftover to the shot that sits closest to it in the list -
        # a shot with no lines of its own (an establishing shot) takes it
        # first, so the opening line is not dragged into a later close-up.
        # The length limit still applies: a shot that cannot take the line
        # within it is not considered.
        n_shots = len(shots)

        def length_of(sid: str) -> float:
            return sum(durs[n - 1] for n in claimed.get(sid, []) if n - 1 < len(durs))

        for n in missing:
            d = durs[n - 1] if n - 1 < len(durs) else 0.0
            want = (n - 0.5) / n_lines * n_shots
            fits = [sh for sh in shots
                    if not (limit > 0 and length_of(sh.id) + d > limit)]
            empty = [sh for sh in fits if not claimed.get(sh.id)]
            if empty:
                best = min(empty, key=lambda sh: abs(sh.index - want))
            elif fits:
                best = min(fits, key=lambda sh: abs(sh.index - want))
            else:
                # nothing can take it within the limit: the shot with the
                # shortest dialogue is the least bad home for it
                best = min(shots, key=lambda sh: length_of(sh.id))
            claimed.setdefault(best.id, []).append(n)
        for sid in claimed:
            claimed[sid].sort()

    # The lines have to come out in the order they were written. A storyboard
    # sometimes hands a later line to an earlier shot, and the timeline
    # places the lines inside their shots - the scene would be played back
    # with the dialogue out of order, the answer before the question. When
    # that happens the lines are handed out in order instead, using the
    # storyboard's counts.
    seq: list[int] = []
    for sh in shots:
        seq += claimed.get(sh.id, [])
    if seq != sorted(seq):
        counts = [len(claimed.get(sh.id, [])) for sh in shots]
        claimed = {}
        nxt = 1
        for sh, n in zip(shots, counts):
            if n <= 0:
                continue
            take: list[int] = []
            total = 0.0
            for k in range(nxt, min(nxt + n, n_lines + 1)):
                d = durs[k - 1] if k - 1 < len(durs) else 0.0
                if take and limit > 0 and total + d > limit:
                    break
                take.append(k)
                total += d
            if take:
                claimed[sh.id] = take
                nxt = take[-1] + 1
        # anything the storyboard did not place goes to a shot with room, in
        # order
        left = [k for k in range(1, n_lines + 1) if k not in seq]
        for sh in shots:
            if not left:
                break
            if len(claimed.get(sh.id, [])) >= 2:
                continue
            d = durs[left[0] - 1] if left[0] - 1 < len(durs) else 0.0
            have = sum(durs[k - 1] for k in claimed.get(sh.id, [])
                       if k - 1 < len(durs))
            if limit > 0 and have + d > limit:
                continue
            claimed.setdefault(sh.id, []).append(left.pop(0))
        for sid in claimed:
            claimed[sid].sort()
    return claimed


def _assign_by_cast(shots, line_durs: list[float],
                    speakers: list[str],
                    max_shot: float = 0.0,
                    max_dialogue: float = 0.0) -> dict[str, list[int]] | None:
    """Work out which lines each shot carries when the storyboard did not say.

    The lines go to the shot that has the speaker in frame, which keeps the
    cut on the dialogue and the picture on the person who is talking. No
    shot gets more than two lines or more dialogue than the model can make
    in one clip, or one shot ends up carrying the whole conversation.
    """
    if not shots or not speakers:
        return None
    n = len(speakers)
    claimed: dict[str, list[int]] = {}
    limit = max_shot if max_shot > 0 else 0.0
    if max_dialogue > 0:
        limit = max_dialogue if limit <= 0 else min(limit, max_dialogue)

    def length_of(sid: str) -> float:
        return sum(line_durs[i - 1] for i in claimed.get(sid, []))

    used: set[int] = set()
    for k, sp in enumerate(speakers):
        d = line_durs[k] if k < len(line_durs) else 0.0
        cands = [sh for sh in shots
                 if sp in (sh.characters or []) and len(claimed.get(sh.id, [])) < 2
                 and not (limit > 0 and length_of(sh.id) + d > limit)]
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
        d = line_durs[k] if k < len(line_durs) else 0.0
        free = [sh for sh in shots
                if len(claimed.get(sh.id, [])) < 2
                and not (limit > 0 and length_of(sh.id) + d > limit)]
        best = (min(free, key=lambda sh: len(claimed.get(sh.id, []))) if free
                else min(shots, key=lambda sh: len(claimed.get(sh.id, []))))
        claimed.setdefault(best.id, []).append(k + 1)
        used.add(k)
    for sid in claimed:
        claimed[sid].sort()
    return claimed


def build_timeline(ep: Episode, min_shot: float = 1.0,
                   max_shot: float = 0.0, line_gap: float = 0.0) -> Timeline:
    timed_scenes: list[TimedScene] = []
    cursor = 0.0
    for sc in ep.scenes:
        # 1) dialogue length of the scene. Narration is shown on screen but never
        #    spoken, so it must not stretch the scene's audio track.
        spoken = [l for l in sc.lines if not is_narration(l)]
        narration = [l for l in sc.lines if is_narration(l)]
        raw_lines = [(_line_duration(l), l) for l in spoken]
        gap = max(0.0, float(line_gap))
        # the scene has to hold the lines and the breaths between them
        scene_audio = round(sum(d for d, _ in raw_lines)
                            + gap * max(0, len(raw_lines) - 1), 3)

        # 2) how long each shot lasts. When the storyboard says which lines a
        #    shot carries, the shot is exactly as long as those lines - the cut
        #    lands on the dialogue instead of drifting through it.
        line_map = _shot_line_map(sc.shots, len(raw_lines), max_shot=max_shot,
                                   line_durs=[d for d, _ in raw_lines],
                                   max_dialogue=SHOT_DIALOGUE_MAX)
        if line_map is None and sc.shots:
            # the storyboard did not say: work it out from who is in frame
            line_map = _assign_by_cast(sc.shots, [d for d, _ in raw_lines],
                                       [l.speaker for _, l in raw_lines],
                                       max_shot=max_shot,
                                       max_dialogue=SHOT_DIALOGUE_MAX)
        # a shot with lines lasts exactly as long as those lines and the
        # breaths between them; the breath after its last line is the room
        # before the next shot starts
        line_shot_pos = [i for i, sh in enumerate(sc.shots)
                         if line_map and (line_map.get(sh.id) or [])]
        last_line_shot = line_shot_pos[-1] if line_shot_pos else -1
        shot_durs: list[float] = []
        for i, sh in enumerate(sc.shots):
            d = max(sh.duration, min_shot)
            if line_map:
                idxs = line_map.get(sh.id) or []
                owned = sum(raw_lines[i - 1][0] for i in idxs)
                if owned > 0:
                    d = owned + gap * max(0, len(idxs) - 1)
                    if i != last_line_shot:
                        d += gap
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
        #    after another, so the picture and the dialogue stay together.
        #    A short breath between the lines: lines that run into each
        #    other sound like a list being read out.
        timed_lines: list[TimedLine] = []
        if line_map and timed_shots:
            by_shot: dict[str, list[int]] = line_map
            for ts in timed_shots:
                idxs = sorted(by_shot.get(ts.shot.id) or [])
                if not idxs:
                    continue
                inner = ts.start
                total = sum(raw_lines[j - 1][0] for j in idxs)
                gaps_total = gap * max(0, len(idxs) - 1)
                # the room the lines need inside this shot, gaps included
                need = total + gaps_total
                room = max(ts.duration, need)
                # the lines share what is left once the breaths have their room
                share_k = (room - gaps_total) / max(total, 1e-6)
                for n, i in enumerate(idxs):
                    d, l = raw_lines[i - 1]
                    share = d * share_k
                    timed_lines.append(TimedLine(l, sc.id, round(inner, 3),
                                                 round(inner + share, 3)))
                    inner += share
                    if n < len(idxs) - 1:
                        inner += gap * share_k
        else:
            line_cursor = cursor
            for n, (d, l) in enumerate(raw_lines):
                timed_lines.append(TimedLine(l, sc.id, round(line_cursor, 3),
                                             round(line_cursor + d, 3)))
                line_cursor += d
                if n < len(raw_lines) - 1:
                    line_cursor += gap
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
