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
SHOT_DIALOGUE_MAX = 4.5


def _line_duration(line: Line) -> float:
    """Use measured audio duration if the voice stage ran; else estimate."""
    if line.duration and line.duration > 0:
        return line.duration
    return estimate_reading_seconds(line.text)


def _shot_line_map(shots, n_lines: int, max_shot: float = 0.0,
                   line_durs: list[float] | None = None,
                   max_dialogue: float = 0.0,
                   speakers: list[str] | None = None) -> dict[str, list[int]] | None:
    """Which lines each shot carries.

    The storyboard says which shot covers which line, and that is the
    decision: the camera is on the person who is talking. The timeline adds
    two guards.

    - A line is never taken away from the shot the storyboard gave it to.
      Taking one used to shuffle the dialogue along and put one character's
      words over another character's face.
    - A line that belongs to no shot is handed to a shot that has the
      speaker in it, as late as possible, and never in front of the lines
      that were already placed.

    A shot lasts as long as the lines it carries plus the breaths between
    them. The length limit only steers a line that has no home yet: how
    long a storyboard's own shot is, is the storyboard's business.
    """
    if not shots or n_lines <= 0:
        return None
    durs = line_durs or []
    limit = max_shot if max_shot > 0 else 0.0
    if max_dialogue > 0:
        limit = max_dialogue if limit <= 0 else min(limit, max_dialogue)

    def dur_of(n: int) -> float:
        return durs[n - 1] if n - 1 < len(durs) else 0.0

    def spk_of(n: int) -> str:
        if not speakers or n - 1 >= len(speakers):
            return ""
        return speakers[n - 1] or ""

    # 1) the storyboard's own assignment - kept as it is
    claimed: dict[str, list[int]] = {}
    used: set[int] = set()
    for sh in shots:
        idxs = [n for n in sh.line_indices if 1 <= n <= n_lines and n not in used]
        if idxs:
            claimed[sh.id] = idxs
            used.update(idxs)
    if not claimed:
        return None

    def length_of(sid: str) -> float:
        return sum(dur_of(n) for n in claimed.get(sid, []))

    def has_speaker(sh, spk: str) -> bool:
        """True when the shot can show this person talking."""
        if not spk or not sh.characters:
            return True
        return spk in sh.characters

    # 2) the lines that belong to no shot
    missing = [n for n in range(1, n_lines + 1) if n not in used]
    for n in missing:
        d = dur_of(n)
        spk = spk_of(n)
        # the shot it belongs after: the last one carrying a smaller line
        after = -1
        before = len(shots)
        for i, sh in enumerate(shots):
            for ln in claimed.get(sh.id, []):
                if ln < n:
                    after = max(after, i)
                elif ln > n:
                    before = min(before, i)
        # a shot may only take the line if it does not already carry a later
        # one - the dialogue has to come out in order
        window = [i for i in range(max(0, after), min(len(shots), max(before, after + 1)))
                  if not any(ln > n for ln in claimed.get(shots[i].id, []))]
        if not window:
            window = [max(0, min(after, len(shots) - 1))]
        cands = [shots[i] for i in window
                 if has_speaker(shots[i], spk)
                 and not (limit > 0 and length_of(shots[i].id) + d > limit)]
        if not cands:
            cands = [shots[i] for i in window if has_speaker(shots[i], spk)]
        if not cands:
            cands = [shots[i] for i in window]
        # an empty shot first, then the one closest to where the line sits
        cands.sort(key=lambda sh: (len(claimed.get(sh.id, [])), abs(sh.index - after)))
        best = cands[0]
        claimed.setdefault(best.id, []).append(n)
        used.add(n)

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
                                   max_dialogue=SHOT_DIALOGUE_MAX,
                                   speakers=[l.speaker for _, l in raw_lines])
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
            # The director's segment is the shot's length.  A segment is six
            # to fifteen seconds and holds several shots inside it; the
            # dialogue has to fit inside the segment, it never shortens it.
            # (A shot shortened to the length of its words ends up with a
            # prompt that asks for seven seconds of business inside three
            # seconds of clip.)
            d = max(sh.duration, min_shot)
            if max_shot > 0:
                d = min(d, max_shot)
            if line_map:
                idxs = line_map.get(sh.id) or []
                owned = sum(raw_lines[i - 1][0] for i in idxs)
                if owned > 0:
                    need = owned + gap * max(0, len(idxs) - 1)
                    d = max(d, need)
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
        #    A line keeps the length of its own recording. The breath after
        #    the last line of a shot is room at the end of the shot, not
        #    part of the line - stretching the line is what puts the mouth
        #    out of step with the voice.
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
                # only when the shot is too short for its lines do they have
                # to be stretched - and that is worth reporting
                k = need / ts.duration if (ts.duration > 0 and need > ts.duration) else 1.0
                for n, i in enumerate(idxs):
                    d, l = raw_lines[i - 1]
                    share = d * k
                    timed_lines.append(TimedLine(l, sc.id, round(inner, 3),
                                                 round(inner + share, 3)))
                    inner += share
                    if n < len(idxs) - 1:
                        inner += gap * k
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

    def timeline(self, ep: Episode) -> Timeline:
        """The one timeline every stage works from.

        The prompt that asks for the performance, the picture that is cut
        together, the subtitles and the music all have to agree on where a
        line falls inside a shot - otherwise the lips belong to the wrong
        person.
        """
        rng = list(self.cfg.storyboard.shot_duration_range or [])
        dmin = float(rng[0]) if rng else 6.0
        dmax = float(rng[1]) if len(rng) > 1 else 15.0
        cap = float(self.cfg.comfyui.max_video_seconds or 0) or dmax
        return build_timeline(ep,
                              min_shot=dmin,
                              max_shot=min(dmax, cap),
                              line_gap=self.cfg.compose.line_gap)

    def stage_done(self, ep: Episode, stage: str) -> bool:
        return ep.stage_status.get(stage) == Status.DONE

    def mark(self, ep: Episode, stage: str, status: Status) -> None:
        ep.stage_status[stage] = status

    # -- path helpers --------------------------------------------------------
    @property
    def root(self) -> Path:
        return self.store.root
