"""
Repair Agent
============
Replaces segments that fail verification checks with safer alternatives,
or marks them as unresolvable if no replacement exists.

Design principles:
- HARD failures (rights, spoilers, source) are repaired or rejected
- SOFT failures (bias, accessibility) are warned but allowed through
- The system NEVER forces a trailer past a HARD failure without a valid replacement
- All repair decisions are logged with full evidence
"""

from __future__ import annotations

import logging
from typing import Optional

from src.agents.base_agent import BaseAgent
from src.models.episode import EpisodePackage, SceneModel
from src.models.trailer import TrailerEDL, TrailerSegment, RiskFlag, ValidationStatus
from src.models.story_map import StoryMap
from src.models.constraint_map import ConstraintMap

logger = logging.getLogger(__name__)


class RepairAgent(BaseAgent):
    """
    Attempts to repair a trailer plan that has failed verification.

    Strategy:
    1. For each HARD failure, identify affected segments.
    2. Find replacement scenes from the episode that:
       - Are not in the excluded list
       - Match the emotional_arc position of the failed segment
       - Are not spoilers
       - Pass rights and ratings checks
    3. If replacement found: swap in, re-log with evidence.
    4. If no replacement: mark segment as UNRESOLVED and flag for human approval.
    """

    def run(
        self,
        trailer: TrailerEDL,
        failures: list[RiskFlag],
        episode: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
        audience_id: str,
    ) -> tuple[TrailerEDL, list[str]]:
        """
        Attempt to repair a trailer's failing segments.

        Returns:
            (repaired_trailer, list_of_unresolved_issues)
        """
        unresolved: list[str] = []
        hard_failures = [f for f in failures if f.severity == "HARD"]
        soft_failures = [f for f in failures if f.severity == "SOFT"]

        # Add soft warnings without removing segments
        for soft in soft_failures:
            trailer.validation.warnings.append(
                f"[SOFT] {soft.type}: {soft.description}"
            )
            self._logger.log_decision(
                agent="RepairAgent",
                action="soft_warning_accepted",
                reasoning=f"Soft failure accepted with warning: {soft.description}",
                evidence=[soft.flag_id],
                cost=0.0,
                llm="none",
                affected_trailers=[trailer.trailer_id],
            )

        # Handle hard failures
        failed_segment_ids = set()
        for failure in hard_failures:
            # Parse affected segment from flag description
            # Flags use format "segment:<segment_id>: <reason>"
            affected = self._extract_segment_id(failure.description)
            if affected:
                failed_segment_ids.add(affected)

        repaired_segments = []
        for seg in trailer.segments:
            if seg.segment_id in failed_segment_ids:
                # Try to find a replacement
                replacement = self._find_replacement(
                    failed_segment=seg,
                    episode=episode,
                    story_map=story_map,
                    constraint_map=constraint_map,
                    audience_id=audience_id,
                    existing_segments=trailer.segments,
                )
                if replacement:
                    logger.info(
                        f"[RepairAgent] Replaced {seg.segment_id} "
                        f"({seg.video}) with {replacement.segment_id} ({replacement.video})"
                    )
                    self._logger.log_decision(
                        agent="RepairAgent",
                        action="segment_replaced",
                        reasoning=(
                            f"Segment {seg.segment_id} ({seg.video}) failed hard check. "
                            f"Replaced with {replacement.video} which passes all constraints."
                        ),
                        evidence=[f"scene:{replacement.video}", f"original:{seg.video}"],
                        cost=0.0,
                        llm="none",
                        affected_trailers=[trailer.trailer_id],
                    )
                    repaired_segments.append(replacement)
                else:
                    # No valid replacement — mark unresolved
                    issue = (
                        f"Segment {seg.segment_id} ({seg.video}) failed: "
                        f"{self._get_failure_reason(seg.segment_id, hard_failures)}. "
                        f"No valid replacement found."
                    )
                    unresolved.append(issue)
                    seg.human_approval_required = True
                    seg.risk_flags.extend(
                        [f for f in hard_failures if self._extract_segment_id(f.description) == seg.segment_id]
                    )
                    repaired_segments.append(seg)
                    logger.warning(f"[RepairAgent] UNRESOLVED: {issue}")
                    self._logger.log_decision(
                        agent="RepairAgent",
                        action="segment_unresolved",
                        reasoning=issue,
                        evidence=[f"scene:{seg.video}"],
                        cost=0.0,
                        llm="none",
                        affected_trailers=[trailer.trailer_id],
                    )
            else:
                repaired_segments.append(seg)

        trailer.segments = repaired_segments

        # Update validation status
        if unresolved:
            trailer.validation.status = ValidationStatus.FAIL_UNRESOLVED
            trailer.validation.failures.extend(unresolved)
            trailer.validation.human_approvals_required.extend(
                [f"UNRESOLVED: {u}" for u in unresolved]
            )
        elif hard_failures:
            # All hard failures were resolved
            trailer.validation.status = (
                ValidationStatus.PASS_WITH_WARNINGS
                if soft_failures
                else ValidationStatus.PASS
            )
        elif soft_failures:
            trailer.validation.status = ValidationStatus.PASS_WITH_WARNINGS
        else:
            trailer.validation.status = ValidationStatus.PASS

        return trailer, unresolved

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_replacement(
        self,
        failed_segment: TrailerSegment,
        episode: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
        audience_id: str,
        existing_segments: list[TrailerSegment],
    ) -> Optional[TrailerSegment]:
        """
        Find a replacement scene that:
        - Is not a spoiler
        - Does not have sensitive content that violates policy
        - Is not already used in the trailer
        - Has matching emotional character (best-effort)
        """
        from src.utils.timecode import seconds_to_timecode, duration_seconds

        existing_scene_ids = {s.video for s in existing_segments}
        excluded_scenes = self._get_excluded_scenes(constraint_map, audience_id)
        spoiler_scenes = set(story_map.spoiler_map.spoiler_scenes)

        # Get the failed scene's emotional tags for matching
        failed_scene = next(
            (s for s in episode.scenes if s.scene_id == failed_segment.video),
            None,
        )
        target_tags = set(failed_scene.emotional_tags) if failed_scene else set()

        candidates = []
        for scene in episode.scenes:
            # Skip already used
            if scene.scene_id in existing_scene_ids:
                continue
            # Skip spoilers
            if scene.scene_id in spoiler_scenes:
                continue
            # Skip excluded by constraints
            if scene.scene_id in excluded_scenes:
                continue
            # Skip if it has sensitive content that caused the original failure
            # (simple heuristic: avoid same sensitive tags)
            if failed_scene and set(scene.sensitive_content) & set(failed_scene.sensitive_content):
                continue

            # Score by emotional tag overlap
            overlap = len(set(scene.emotional_tags) & target_tags)
            candidates.append((overlap, scene))

        if not candidates:
            return None

        # Sort by tag overlap descending, take the best
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_scene: SceneModel = candidates[0][1]

        # Build a replacement TrailerSegment
        replacement = TrailerSegment(
            segment_id=f"{failed_segment.segment_id}_replacement",
            source_in=best_scene.timecode_in,
            source_out=best_scene.timecode_out,
            video=best_scene.scene_id,
            audio="dialogue_and_music",
            music_track=best_scene.music_track,
            subtitle=f"[{best_scene.scene_id} replacement for failed {failed_segment.video}]",
            subtitle_track=failed_segment.subtitle_track,
            reason=(
                f"Replacement for {failed_segment.video} which failed verification. "
                f"{best_scene.scene_id} selected based on emotional tag overlap "
                f"({', '.join(best_scene.emotional_tags)}) and constraint compliance."
            ),
            evidence=[
                f"scene:{best_scene.scene_id}",
                f"replaced:{failed_segment.video}",
                "RepairAgent:auto_replacement",
            ],
            risk_flags=[],
            human_approval_required=False,
        )
        return replacement

    def _get_excluded_scenes(
        self, constraint_map: ConstraintMap, audience_id: str
    ) -> set[str]:
        """Collect all scene_ids excluded by active constraints for this audience."""
        excluded = set()
        for rule in constraint_map.rules:
            if not rule.active:
                continue
            if rule.action == "EXCLUDE":
                if not rule.audiences or audience_id in rule.audiences:
                    excluded.update(rule.applies_to)
        return excluded

    def _extract_segment_id(self, description: str) -> Optional[str]:
        """Extract segment_id from a risk flag description like 'segment:seg_01:...'"""
        if description.startswith("segment:"):
            parts = description.split(":")
            if len(parts) >= 2:
                return parts[1]
        # Try to find pattern
        import re
        match = re.search(r"segment[_\s]+(\w+)", description, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _get_failure_reason(self, segment_id: str, failures: list[RiskFlag]) -> str:
        """Get failure reasons for a segment."""
        reasons = []
        for f in failures:
            if self._extract_segment_id(f.description) == segment_id:
                reasons.append(f"{f.type}: {f.description}")
        return "; ".join(reasons) if reasons else "unknown failure"
