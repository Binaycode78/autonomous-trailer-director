"""
Bias Checker
============
Detects stereotyping and bias in dialect usage and audience-data-driven decisions.

SOFT FAIL conditions:
- Creative brief uses stereotype language ('quaint', 'simple folk', 'folksy')
- Dialect is used primarily in humorous scenes
- Audience data has known bias warnings

The checker never produces HARD failures — bias is always flagged for human review.
"""
from __future__ import annotations

STEREOTYPE_KEYWORDS = [
    "quaint", "simple folk", "they love", "because they're from",
    "charming accent", "funny dialect", "rustic", "folksy", "provincial",
    "humble villagers", "backward", "unsophisticated",
    "exotic", "colourful characters",
]

HUMOUR_INDICATORS = [
    "humorous look at", "comic", "comedic", "funny", "lighthearted take on dialect",
    "laugh at", "amusing accent",
]


class BiasChecker:
    """
    Checks for cultural and data bias in dialect-region trailer planning.
    """

    def check_dialect_usage(
        self,
        segment: dict,
        creative_brief: str,
        audience_profile: dict,
        dialect_policy: dict,
    ) -> list[dict]:
        """
        Check a segment and creative brief for bias/stereotype issues.

        Args:
            segment: dict with keys: segment_id, subtitle_track, sensitive_content_tags (optional)
            creative_brief: string creative brief
            audience_profile: dict with optional 'bias_warning' key
            dialect_policy: dict with dialect_representation_rules

        Returns:
            List of risk flag dicts (SOFT severity only)
        """
        flags = []
        seg_id = segment.get("segment_id", "unknown")
        brief_lower = creative_brief.lower()

        # 1. Check for stereotype language in creative brief
        found_stereotypes = [kw for kw in STEREOTYPE_KEYWORDS if kw in brief_lower]
        if found_stereotypes:
            flags.append({
                "flag_id": f"BIAS-STEREOTYPE-{seg_id}",
                "severity": "SOFT",
                "type": "bias",
                "description": (
                    f"segment:{seg_id}: Creative brief contains potential stereotype language: "
                    f"{found_stereotypes}. Dialect must not be reduced to cultural shorthand."
                ),
                "resolution": (
                    "Revise brief to ground dialect usage in episode evidence. "
                    "Focus on cultural identity, not novelty."
                ),
            })

        # 2. Check for dialect used humorously
        found_humour = [kw for kw in HUMOUR_INDICATORS if kw in brief_lower]
        if found_humour:
            flags.append({
                "flag_id": f"BIAS-HUMOUR-{seg_id}",
                "severity": "SOFT",
                "type": "bias",
                "description": (
                    f"segment:{seg_id}: Creative brief frames dialect usage humorously: "
                    f"{found_humour}. Dialect is cultural identity, not a comic device."
                ),
                "resolution": (
                    "Remove humorous framing. Present dialect with same weight as standard English."
                ),
            })

        # 3. Check segment's sensitive_content_tags for dialect_as_comedy
        sensitive_tags = segment.get("sensitive_content_tags", [])
        if "dialect_as_comedy" in sensitive_tags:
            flags.append({
                "flag_id": f"BIAS-DIALECT-COMEDY-{seg_id}",
                "severity": "SOFT",
                "type": "bias",
                "description": (
                    f"segment:{seg_id}: Scene is tagged 'dialect_as_comedy'. "
                    "Policy excludes this from dialect-region trailers."
                ),
                "resolution": "Replace with a scene that treats dialect respectfully.",
            })

        # 4. Surface audience profile bias warning if present
        bias_warning = audience_profile.get("bias_warning", "")
        if bias_warning:
            flags.append({
                "flag_id": f"BIAS-DATA-{seg_id}",
                "severity": "SOFT",
                "type": "bias",
                "description": (
                    f"segment:{seg_id}: Audience data has known bias: '{bias_warning}'. "
                    "Decisions based on historic_high_performing_scenes may be unrepresentative."
                ),
                "resolution": (
                    "Human editorial review required. "
                    "Verify segment selection is grounded in episode content, not biased data."
                ),
            })

        return flags

    def check_trailer(self, trailer, creative_brief: str, audience_profile: dict, dialect_policy: dict) -> list[dict]:
        """Check all segments in a dialect-region trailer."""
        all_flags = []
        segments = trailer.segments if hasattr(trailer, "segments") else trailer.get("segments", [])
        for seg in segments:
            seg_dict = seg if isinstance(seg, dict) else seg.model_dump()
            all_flags.extend(self.check_dialect_usage(seg_dict, creative_brief, audience_profile, dialect_policy))
        return all_flags
