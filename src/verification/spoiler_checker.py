"""
Spoiler Checker
===============
Checks that no trailer segment reveals protected story facts.

HARD FAIL conditions:
- Segment uses a scene that is in the spoiler map
- Segment contains dialogue flagged as spoiler
"""
from __future__ import annotations


class SpoilerChecker:
    """
    Checks segments against the story_map spoiler_map.
    Works with dict inputs for compatibility with test fixtures.
    """

    def check_segment(self, segment: dict, story_map: Any, constraint_map: Any = None) -> list[dict]:
        """
        Check a single segment dict.

        Args:
            segment: dict with keys: segment_id, video, evidence (optional)
            story_map: dict with spoiler_map.spoiler_scenes and spoiler_map.spoiler_dialogue

        Returns:
            List of risk flag dicts
        """
        flags = []
        seg_id = segment.get("segment_id", "unknown")
        scene_id = segment.get("video", "")
        evidence = segment.get("evidence", [])

        # Get spoiler data
        if hasattr(story_map, "spoiler_map"):
            sm = story_map.spoiler_map
            spoiler_scenes = getattr(sm, "spoiler_scenes", []) if sm else []
            spoiler_dialogue = getattr(sm, "spoiler_dialogue", []) if sm else []
        elif isinstance(story_map, dict):
            sm = story_map.get("spoiler_map", {})
            spoiler_scenes = sm.get("spoiler_scenes", []) if isinstance(sm, dict) else getattr(sm, "spoiler_scenes", [])
            spoiler_dialogue = sm.get("spoiler_dialogue", []) if isinstance(sm, dict) else getattr(sm, "spoiler_dialogue", [])
        else:
            spoiler_scenes = []
            spoiler_dialogue = []

        # Check scene
        if scene_id in spoiler_scenes:
            flags.append({
                "flag_id": f"SPOILER-SCENE-{seg_id}",
                "severity": "HARD",
                "type": "spoiler",
                "description": (
                    f"segment:{seg_id}: Scene '{scene_id}' is a protected spoiler. "
                    f"Including it reveals protected story facts."
                ),
                "resolution": "Remove this segment and replace with a non-spoiler scene.",
            })

        # Check if any evidence reference points to spoiler dialogue
        for ev in evidence:
            for dlg_id in spoiler_dialogue:
                if dlg_id in ev:
                    flags.append({
                        "flag_id": f"SPOILER-DLG-{seg_id}-{dlg_id}",
                        "severity": "HARD",
                        "type": "spoiler",
                        "description": (
                            f"segment:{seg_id}: Dialogue line '{dlg_id}' is a spoiler. "
                            f"Using it reveals protected story facts."
                        ),
                        "resolution": "Remove the spoiler dialogue or replace with a safe line.",
                    })

        return flags

    def check_ordering(self, segments: list[dict], story_map: dict) -> list[dict]:
        """
        Check if the ordering of segments reveals the spoiler arc.
        E.g., showing scene_09 then scene_11 consecutively reveals the twist progression.
        """
        flags = []
        spoiler_map = story_map.get("spoiler_map", {})
        spoiler_scenes = (
            story_map["spoiler_map"]["spoiler_scenes"]
            if isinstance(story_map, dict)
            else story_map.spoiler_map.spoiler_scenes
        )

        scene_ids = [s.get("video", "") for s in segments]
        spoiler_in_trailer = [s for s in scene_ids if s in spoiler_scenes]

        if len(spoiler_in_trailer) >= 2:
            flags.append({
                "flag_id": "SPOILER-ARC-ORDER",
                "severity": "HARD",
                "type": "spoiler",
                "description": (
                    f"Segment ordering reveals spoiler arc: "
                    f"{spoiler_in_trailer} appear in sequence. "
                    "This progressively reveals the story twist."
                ),
                "resolution": "Remove at least one spoiler scene from the sequence.",
            })

        return flags

    def check_trailer(self, trailer, story_map) -> list[dict]:
        """Check all segments and ordering for a full trailer."""
        all_flags = []
        story_map_dict = story_map if isinstance(story_map, dict) else story_map.model_dump()
        segments = trailer.segments if hasattr(trailer, "segments") else trailer.get("segments", [])
        seg_dicts = [s if isinstance(s, dict) else s.model_dump() for s in segments]

        for seg in seg_dicts:
            all_flags.extend(self.check_segment(seg, story_map_dict))

        all_flags.extend(self.check_ordering(seg_dicts, story_map_dict))
        return all_flags
