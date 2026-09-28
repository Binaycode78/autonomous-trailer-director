"""
Surprise Event Handler
======================
Handles runtime change events injected during evaluation.

Supported events:
- music_rights_expired       : Music contract expires mid-run
- spoiler_reclassified       : A scene is newly classified as a spoiler
- scene_hallucination        : LLM referenced a non-existent scene
- clickbait_requested        : Marketing requests misleading content
- model_unavailable          : Primary LLM is unavailable
- bias_detected              : Hidden bias found in audience data
- dialect_subtitle_changed   : Dialect subtitle changes character relationship
- contract_changed           : Any contract rule changes

Design principle:
- Events trigger TARGETED replanning, not full rebuild
- Only affected segments/trailers are re-verified
- Full audit trail is maintained in the change log
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.models.trailer import TrailerEDL
from src.models.constraint_map import ConstraintMap, ConstraintRule
from src.models.story_map import StoryMap

if TYPE_CHECKING:
    from src.utils.logger import DecisionLogger
    from src.utils.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class SurpriseEventHandler:
    """
    Handles surprise events by identifying affected trailers and segments,
    triggering targeted re-verification, and preserving a full change record.
    """

    def __init__(self, decision_logger: "DecisionLogger", cost_tracker: "CostTracker"):
        self._logger = decision_logger
        self._cost_tracker = cost_tracker

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def handle_music_rights_expired(
        self,
        track_id: str,
        trailers: list[TrailerEDL],
        constraint_map: ConstraintMap,
    ) -> tuple[list[TrailerEDL], ConstraintMap]:
        """
        A music track's rights have expired.
        - Deactivate the constraint rule for the track
        - Identify which trailer segments use this track
        - Flag them for re-verification and repair
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.warning(f"[SurpriseEvent] Music rights expired for track: {track_id}")

        # Deactivate rules referencing this track
        affected_rule_ids = []
        for rule in constraint_map.rules:
            if track_id in rule.applies_to:
                rule.active = False
                affected_rule_ids.append(rule.rule_id)

        # Add a new EXCLUDE rule for the expired track
        new_rule = ConstraintRule(
            rule_id=f"R-expired-{track_id}-{timestamp[:10]}",
            type="music_rights",
            description=f"Music track '{track_id}' rights have expired. Exclude from all trailers immediately.",
            applies_to=[track_id],
            action="EXCLUDE",
            audiences=[],  # all audiences
            expires=timestamp[:10],
            active=True,
        )
        constraint_map.rules.append(new_rule)
        constraint_map.change_log.append({
            "timestamp": timestamp,
            "event": "music_rights_expired",
            "track_id": track_id,
            "new_rule": new_rule.rule_id,
            "deactivated_rules": affected_rule_ids,
        })

        # Identify affected trailer segments
        affected_trailers = []
        for trailer in trailers:
            affected_segments = [
                seg for seg in trailer.segments if seg.music_track == track_id
            ]
            if affected_segments:
                affected_trailers.append(trailer.trailer_id)
                for seg in affected_segments:
                    seg.human_approval_required = True
                    seg.risk_flags.append({
                        "flag_id": f"FLAG-expired-{track_id}",
                        "severity": "HARD",
                        "type": "music_rights",
                        "description": f"segment:{seg.segment_id}: Music track '{track_id}' rights expired.",
                        "resolution": "Replace music track or obtain new license.",
                    })
                logger.warning(
                    f"[SurpriseEvent] Trailer '{trailer.trailer_id}' has {len(affected_segments)} "
                    f"segment(s) using expired track '{track_id}'. Flagged for repair."
                )

        self._logger.log_change_event(
            event_type="music_rights_expired",
            description=f"Track '{track_id}' rights expired. Affects {len(affected_trailers)} trailer(s).",
            affected_rules=affected_rule_ids + [new_rule.rule_id],
            affected_segments=[
                seg.segment_id
                for t in trailers for seg in t.segments
                if seg.music_track == track_id
            ],
            affected_trailers=affected_trailers,
        )

        return trailers, constraint_map

    def handle_spoiler_reclassified(
        self,
        scene_id: str,
        reason: str,
        trailers: list[TrailerEDL],
        story_map: StoryMap,
        constraint_map: ConstraintMap,
    ) -> tuple[list[TrailerEDL], StoryMap, ConstraintMap]:
        """
        A scene has been newly classified as a spoiler.
        - Add to story_map.spoiler_map
        - Add EXCLUDE constraint rule
        - Flag any trailer segments that include this scene
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.warning(f"[SurpriseEvent] Scene reclassified as spoiler: {scene_id} — {reason}")

        # Update story map
        if scene_id not in story_map.spoiler_map.spoiler_scenes:
            story_map.spoiler_map.spoiler_scenes.append(scene_id)
            story_map.spoiler_map.protected_facts.append(
                f"[Reclassified spoiler] {scene_id}: {reason}"
            )

        # Add constraint rule
        new_rule = ConstraintRule(
            rule_id=f"R-spoiler-{scene_id}",
            type="spoiler",
            description=f"Scene '{scene_id}' reclassified as spoiler: {reason}",
            applies_to=[scene_id],
            action="EXCLUDE",
            audiences=[],
            active=True,
        )
        constraint_map.rules.append(new_rule)
        constraint_map.change_log.append({
            "timestamp": timestamp,
            "event": "spoiler_reclassified",
            "scene_id": scene_id,
            "reason": reason,
            "new_rule": new_rule.rule_id,
        })

        # Flag affected segments
        affected_trailers = []
        for trailer in trailers:
            affected_segments = [s for s in trailer.segments if s.video == scene_id]
            if affected_segments:
                affected_trailers.append(trailer.trailer_id)
                for seg in affected_segments:
                    seg.human_approval_required = True
                    seg.risk_flags.append({
                        "flag_id": f"FLAG-spoiler-{scene_id}",
                        "severity": "HARD",
                        "type": "spoiler",
                        "description": f"segment:{seg.segment_id}: Scene '{scene_id}' is now a spoiler: {reason}",
                        "resolution": "Remove this segment and find a non-spoiler replacement.",
                    })

        self._logger.log_change_event(
            event_type="spoiler_reclassified",
            description=f"Scene '{scene_id}' is now a spoiler. {len(affected_trailers)} trailer(s) affected.",
            affected_rules=[new_rule.rule_id],
            affected_segments=[scene_id],
            affected_trailers=affected_trailers,
        )

        return trailers, story_map, constraint_map

    def handle_scene_hallucination(
        self,
        hallucinated_scene_id: str,
        agent_name: str,
        trailer_id: str,
    ) -> dict:
        """
        An LLM referenced a scene that does not exist in the episode.
        - Log the hallucination
        - Return a rejection record for the planning agent
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.error(
            f"[SurpriseEvent] HALLUCINATION: Agent '{agent_name}' referenced "
            f"non-existent scene '{hallucinated_scene_id}' in trailer '{trailer_id}'"
        )
        self._logger.log_change_event(
            event_type="scene_hallucination",
            description=(
                f"Agent '{agent_name}' proposed scene '{hallucinated_scene_id}' "
                f"which does not exist in the episode. Rejected by SourceChecker."
            ),
            affected_rules=[],
            affected_segments=[hallucinated_scene_id],
            affected_trailers=[trailer_id],
        )
        return {
            "rejected_scene": hallucinated_scene_id,
            "reason": "Scene does not exist in episode (LLM hallucination detected)",
            "agent": agent_name,
            "timestamp": timestamp,
        }

    def handle_clickbait_request(
        self,
        requested_promise: str,
        episode_facts: list[str],
        trailer_id: str,
    ) -> dict:
        """
        Marketing requests a promise that misrepresents the episode.
        - Use TruthChecker logic to evaluate
        - Return REJECTED if the promise cannot be supported
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Simple keyword-based misrepresentation detection
        # In a real system, this would use the TruthChecker + LLM
        misrepresentation_keywords = [
            "action-packed", "explosive", "thriller", "horror",
            "romantic comedy", "never-before-seen",
        ]
        episode_description = " ".join(episode_facts).lower()
        flagged = [
            kw for kw in misrepresentation_keywords
            if kw in requested_promise.lower() and kw not in episode_description
        ]

        result = {
            "requested_promise": requested_promise,
            "timestamp": timestamp,
            "trailer_id": trailer_id,
        }

        if flagged:
            logger.error(
                f"[SurpriseEvent] Clickbait rejected: '{requested_promise}' "
                f"— misrepresents episode (unsupported claims: {flagged})"
            )
            result["status"] = "REJECTED"
            result["reason"] = f"Promise contains unsupported claims: {flagged}. Story truth constraint violated."
            self._logger.log_change_event(
                event_type="clickbait_rejected",
                description=f"Marketing promise '{requested_promise}' rejected — misrepresents episode.",
                affected_rules=["truth_checker"],
                affected_segments=[],
                affected_trailers=[trailer_id],
            )
        else:
            result["status"] = "ACCEPTED_WITH_REVIEW"
            result["reason"] = "Promise appears consistent with episode. Human review recommended."

        return result

    def handle_model_unavailable(
        self,
        model_name: str,
        fallback_model: str,
    ) -> dict:
        """
        The preferred LLM model is unavailable.
        - Switch to fallback model
        - Log the change
        """
        logger.warning(
            f"[SurpriseEvent] Model '{model_name}' unavailable. "
            f"Switching to fallback: '{fallback_model}'"
        )
        self._logger.log_change_event(
            event_type="model_unavailable",
            description=f"Primary model '{model_name}' unavailable. Switched to '{fallback_model}'.",
            affected_rules=[],
            affected_segments=[],
            affected_trailers=["all"],
        )
        return {
            "previous_model": model_name,
            "fallback_model": fallback_model,
            "status": "SWITCHED",
        }

    def handle_dialect_subtitle_changed(
        self,
        scene_id: str,
        line_id: str,
        old_text: str,
        new_text: str,
        relationship_changed: str,
        trailers: list[TrailerEDL],
        story_map: StoryMap,
    ) -> tuple[list[TrailerEDL], StoryMap]:
        """
        A dialect subtitle changes the relationship between two characters.
        - Update story_map relationships if needed
        - Flag trailers that use this line in dialect tracks
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.warning(
            f"[SurpriseEvent] Dialect subtitle changed in {scene_id}/{line_id}: "
            f"'{old_text}' → '{new_text}'. Relationship impact: {relationship_changed}"
        )

        # Update story map
        story_map.relationships.append({
            "updated_at": timestamp,
            "source": f"dialect_subtitle:{scene_id}/{line_id}",
            "change": relationship_changed,
            "requires_review": True,
        })

        # Flag trailers using the affected scene with dialect track
        affected_trailers = []
        for trailer in trailers:
            for seg in trailer.segments:
                if seg.video == scene_id and seg.subtitle_track in ["mariner", "highland"]:
                    affected_trailers.append(trailer.trailer_id)
                    seg.human_approval_required = True
                    seg.risk_flags.append({
                        "flag_id": f"FLAG-dialect-change-{line_id}",
                        "severity": "SOFT",
                        "type": "truth",
                        "description": (
                            f"segment:{seg.segment_id}: Dialect subtitle changed — "
                            f"relationship now reads: '{relationship_changed}'. "
                            f"May alter meaning for dialect audience."
                        ),
                        "resolution": "Human cultural reviewer required.",
                    })

        self._logger.log_change_event(
            event_type="dialect_subtitle_changed",
            description=f"Line '{line_id}' in scene '{scene_id}' dialect changed. Relationship: {relationship_changed}",
            affected_rules=[],
            affected_segments=[scene_id],
            affected_trailers=affected_trailers,
        )

        return trailers, story_map

    def handle_bias_detected(
        self,
        audience_id: str,
        bias_description: str,
        affected_data_field: str,
        trailers: list[TrailerEDL],
    ) -> list[TrailerEDL]:
        """
        Hidden social or regional bias detected in audience data.
        - Flag decisions based on the biased data field
        - Add warning to affected trailers
        """
        logger.warning(
            f"[SurpriseEvent] Bias detected in audience '{audience_id}' "
            f"data field '{affected_data_field}': {bias_description}"
        )
        affected_trailers = []
        for trailer in trailers:
            if audience_id in trailer.audience:
                affected_trailers.append(trailer.trailer_id)
                trailer.validation.warnings.append(
                    f"[BIAS ALERT] {bias_description}. "
                    f"Segments selected using '{affected_data_field}' should be reviewed."
                )
                trailer.decision_notes.append(
                    f"Audience data bias detected: {bias_description}. "
                    f"Affected field: '{affected_data_field}'. Human review recommended."
                )

        self._logger.log_change_event(
            event_type="bias_detected",
            description=f"Bias in '{audience_id}' data: {bias_description}",
            affected_rules=[],
            affected_segments=[],
            affected_trailers=affected_trailers,
        )
        return trailers
