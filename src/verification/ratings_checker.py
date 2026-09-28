"""
Ratings Checker
===============
Checks age/content rating compliance for each segment against audience policy.

HARD FAIL conditions:
- Scene contains sensitive_content tags that are excluded by the audience's policy
"""
from __future__ import annotations


class RatingsChecker:
    """
    Checks segments against rating policies.
    Works with dict inputs for compatibility with test fixtures.
    """

    def check_segment(
        self,
        segment: dict,
        scenes_data: dict,
        policy: dict,
    ) -> list[dict]:
        """
        Check a single segment dict against a rating policy.

        Args:
            segment: dict with keys: segment_id, video
            scenes_data: dict mapping scene_id -> scene dict (with sensitive_content list)
            policy: audience policy dict with excluded_content_tags list

        Returns:
            List of risk flag dicts
        """
        flags = []
        seg_id = segment.get("segment_id", "unknown")
        scene_id = segment.get("video", "")
        audience = policy.get("audience", "unknown")
        excluded_tags = policy.get("excluded_content_tags", [])

        # Get scene data
        scene = scenes_data.get(scene_id)
        if scene is None:
            # Scene not found — SourceChecker handles this
            return flags

        # Get sensitive content tags from scene
        if isinstance(scene, dict):
            scene_tags = scene.get("sensitive_content", [])
        else:
            scene_tags = getattr(scene, "sensitive_content", [])

        # Check each excluded tag
        for tag in excluded_tags:
            if tag in scene_tags:
                flags.append({
                    "flag_id": f"RATING-{audience.upper()}-{tag.upper()}-{seg_id}",
                    "severity": "HARD",
                    "type": "rating",
                    "description": (
                        f"segment:{seg_id}: Scene '{scene_id}' contains '{tag}' content "
                        f"which is excluded by {audience} audience policy."
                    ),
                    "resolution": (
                        f"Remove segment from {audience} trailer. "
                        f"Find a replacement scene without '{tag}' content."
                    ),
                })

        return flags

    def check_trailer(self, trailer, scenes_data: dict, policy: dict) -> list[dict]:
        """Check all segments in a trailer."""
        all_flags = []
        segments = trailer.segments if hasattr(trailer, "segments") else trailer.get("segments", [])
        for seg in segments:
            seg_dict = seg if isinstance(seg, dict) else seg.model_dump()
            all_flags.extend(self.check_segment(seg_dict, scenes_data, policy))
        return all_flags
