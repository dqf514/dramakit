"""NLE interchange export.

The ffmpeg compose track is deterministic and headless, which is what you want
when rendering hundreds of episodes. But a colourist or an editor still needs a
way to pick the episode up in a real NLE.

This module exports the episode timeline as FCPXML 1.9 - the interchange format
DaVinci Resolve, Premiere Pro and Final Cut all import - so the hand-off is a
single file instead of "here are 23 clips and a spreadsheet".

The exported sequence carries:
  * the picture spine, one asset-clip per shot, at its exact timeline position
  * a dialogue lane (the assembled TTS track, split per shot)
  * a music lane (the H3 bed / BGM)
Subtitles stay a sidecar .srt, which every NLE imports cleanly.
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence
from xml.etree import ElementTree as ET


@dataclass
class Clip:
    """One asset on the timeline."""
    src: str | Path
    offset: float          # timeline position (seconds)
    duration: float        # timeline length (seconds)
    start: float = 0.0     # in-point inside the source (seconds)
    name: str = ""
    has_video: bool = True
    has_audio: bool = False


@dataclass
class Timeline:
    """An NLE sequence ready to be written out."""
    name: str = "DramaKit"
    width: int = 1280
    height: int = 720
    fps: int = 24
    duration: float = 0.0
    video: list[Clip] = field(default_factory=list)
    lanes: dict[int, tuple[str, list[Clip]]] = field(default_factory=dict)


def _tc(seconds: float) -> str:
    """FCPXML rational-ish time string: '12.345s'."""
    return f"{max(seconds, 0.0):.3f}s"


def _file_uri(path: str | Path) -> str:
    p = Path(path).resolve()
    # keep the drive-letter colon and the slashes readable: "file:///E:/dir/x.mp4"
    return "file:///" + urllib.parse.quote(str(p).replace("\\", "/"), safe="/:")


def _fmt_id(n: int) -> str:
    return f"r{n}"


def to_fcpxml(tl: Timeline, event_name: str = "DramaKit") -> str:
    """Render a Timeline as an FCPXML 1.9 document."""
    ET.register_namespace("", "")
    root = ET.Element("fcpxml", {"version": "1.9"})
    resources = ET.SubElement(root, "resources")

    fmt = ET.SubElement(resources, "format", {
        "id": _fmt_id(0),
        "name": f"FFVideoFormat{tl.height}p{tl.fps}",
        "frameDuration": f"1/{tl.fps}s",
        "width": str(tl.width),
        "height": str(tl.height),
        "colorSpace": "1-1-1 (Rec. 709)",
    })
    fmt_id = _fmt_id(0)

    rid = 1
    asset_ids: dict[int, str] = {}   # id(cli) -> resource id

    def asset_for(clip: Clip) -> str:
        nonlocal rid
        key = id(clip)
        if key in asset_ids:
            return asset_ids[key]
        attrs = {
            "id": _fmt_id(rid),
            "name": clip.name or Path(clip.src).stem,
            "src": _file_uri(clip.src),
            "start": _tc(clip.start),
            "duration": _tc(clip.duration),
            "format": fmt_id,
        }
        if clip.has_video:
            attrs["hasVideo"] = "1"
            attrs["videoSources"] = "1"
            attrs["videoFrameRate"] = str(tl.fps)
        if clip.has_audio:
            attrs["hasAudio"] = "1"
            attrs["audioSources"] = "1"
            attrs["audioChannels"] = "2"
            attrs["audioRate"] = "48000"
        ET.SubElement(resources, "asset", attrs)
        asset_ids[key] = _fmt_id(rid)
        rid += 1
        return asset_ids[key]

    # spine assets
    spine_refs: list[tuple[str, Clip]] = []
    for clip in tl.video:
        spine_refs.append((asset_for(clip), clip))

    # lane assets
    lane_refs: dict[int, list[tuple[str, Clip]]] = {}
    for lane, (_label, clips) in tl.lanes.items():
        lane_refs[lane] = [(asset_for(c), c) for c in clips]

    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", {"name": event_name})
    project = ET.SubElement(event, "project", {"name": tl.name})
    sequence = ET.SubElement(project, "sequence", {
        "format": fmt_id,
        "duration": _tc(tl.duration),
        "tcStart": "0s",
        "tcFormat": "NDF",
        "audioLayout": "stereo",
        "audioRate": "48000",
    })

    spine = ET.SubElement(sequence, "spine")
    for ref, clip in spine_refs:
        ET.SubElement(spine, "asset-clip", {
            "ref": ref,
            "offset": _tc(clip.offset),
            "name": clip.name or Path(clip.src).stem,
            "start": _tc(clip.start),
            "duration": _tc(clip.duration),
            "format": fmt_id,
        })

    if lane_refs:
        sections = ET.SubElement(sequence, "section-list")
        for lane in sorted(lane_refs):
            label, clips = tl.lanes[lane]
            section = ET.SubElement(sections, "section", {
                "ref": _fmt_id(rid),
                "lane": str(lane),
                "offset": _tc(0.0),
                "duration": _tc(tl.duration),
                "name": label,
            })
            rid += 1
            for ref, clip in lane_refs[lane]:
                ET.SubElement(section, "asset-clip", {
                    "ref": ref,
                    "offset": _tc(clip.offset),
                    "name": clip.name or Path(clip.src).stem,
                    "start": _tc(clip.start),
                    "duration": _tc(clip.duration),
                    "format": fmt_id,
                })

    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + body + "\n"


def write_fcpxml(tl: Timeline, out: str | Path,
                  event_name: str = "DramaKit") -> str:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_fcpxml(tl, event_name), encoding="utf-8")
    return str(out)
