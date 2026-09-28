"""
Source Checker
==============
Verifies that all segment timecodes exist in the episode.

HARD FAIL conditions:
- Referenced scene_id does not exist in episode
- source_in or source_out timecodes are outside scene bounds
- Timecode format is invalid (not HH:MM:SS.mmm)
"""
from __future__ import annotations
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.episode import EpisodePackage


TIMECODE_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}$")


def _parse_tc(tc: str) -> float:
    """Parse HH:MM:SS.mmm to float seconds."""
    parts = tc.split(":")
    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
    return h * 3600 + m * 60 + s


class SourceChecker:
    """
    Checks that every segment's scene_id and timecodes exist in the episode.
    Returns a list of risk flag dicts compatible with the TrailerSegment model.
    """

    def check_segment(self, segment: dict, episode) -> list[dict]:
        """
        Check a single segment dict against the episode.

        Args:
            segment: dict with keys: segment_id, video, source_in, source_out
            episode: EpisodePackage or dict with 'scenes' list

        Returns:
            List of risk flag dicts with keys: flag_id, severity, type, description, resolution
        """
        flags = []
        seg_id = segment.get("segment_id", "unknown")
        scene_id = segment.get("video", "")
        source_in = segment.get("source_in", "")
        source_out = segment.get("source_out", "")

        # Build scene lookup
        if hasattr(episode, "scenes"):
            scenes = episode.scenes
            scene_map = {
                (s.scene_id if hasattr(s, "scene_id") else s["scene_id"]): s
                for s in scenes
            }
        else:
            scenes = episode.get("scenes", [])
            scene_map = {s["scene_id"]: s for s in scenes}

        # 1. Validate timecode format
        if not TIMECODE_PATTERN.match(source_in):
            flags.append({
                "flag_id": f"SRC-FMT-{seg_id}-in",
                "severity": "HARD",
                "type": "source",
                "description": f"segment:{seg_id}: Invalid source_in timecode format '{source_in}'. Expected HH:MM:SS.mmm.",
                "resolution": "Correct the timecode format.",
            })
            return flags  # Cannot check further without valid timecode

        if not TIMECODE_PATTERN.match(source_out):
            flags.append({
                "flag_id": f"SRC-FMT-{seg_id}-out",
                "severity": "HARD",
                "type": "source",
                "description": f"segment:{seg_id}: Invalid source_out timecode format '{source_out}'. Expected HH:MM:SS.mmm.",
                "resolution": "Correct the timecode format.",
            })
            return flags

        # 2. Check scene exists
        if scene_id not in scene_map:
            flags.append({
                "flag_id": f"SRC-MISSING-{seg_id}",
                "severity": "HARD",
                "type": "source",
                "description": (
                    f"segment:{seg_id}: Scene '{scene_id}' not found in episode. "
                    f"Available scenes: {sorted(scene_map.keys())}."
                ),
                "resolution": "Remove this segment or correct the scene_id.",
            })
            return flags

        # 3. Check timecodes are within scene bounds
        scene = scene_map[scene_id]
        if hasattr(scene, "timecode_in"):
            scene_in = scene.timecode_in
            scene_out = scene.timecode_out
        else:
            scene_in = scene["timecode_in"]
            scene_out = scene["timecode_out"]

        seg_in_s = _parse_tc(source_in)
        seg_out_s = _parse_tc(source_out)
        sc_in_s = _parse_tc(scene_in)
        sc_out_s = _parse_tc(scene_out)

        if seg_in_s < sc_in_s or seg_out_s > sc_out_s:
            flags.append({
                "flag_id": f"SRC-BOUNDS-{seg_id}",
                "severity": "HARD",
                "type": "source",
                "description": (
                    f"segment:{seg_id}: Timecodes [{source_in} → {source_out}] exceed "
                    f"scene '{scene_id}' bounds [{scene_in} → {scene_out}]."
                ),
                "resolution": "Trim the segment to fit within scene bounds.",
            })

        if seg_in_s >= seg_out_s:
            flags.append({
                "flag_id": f"SRC-ORDER-{seg_id}",
                "severity": "HARD",
                "type": "source",
                "description": f"segment:{seg_id}: source_in >= source_out (zero/negative duration).",
                "resolution": "Fix the timecodes so source_in < source_out.",
            })

        return flags

    def check_trailer(self, trailer, episode) -> list[dict]:
        """Check all segments in a trailer."""
        all_flags = []
        segments = trailer.segments if hasattr(trailer, "segments") else trailer.get("segments", [])
        for seg in segments:
            seg_dict = seg if isinstance(seg, dict) else seg.model_dump()
            all_flags.extend(self.check_segment(seg_dict, episode))
        return all_flags
