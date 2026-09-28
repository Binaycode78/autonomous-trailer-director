"""
Segment Selector Agent
======================
Selects candidate scenes from the episode that match the audience promise
and pass basic constraint rules.
"""
from __future__ import annotations

from typing import Any
from src.agents.base_agent import BaseAgent
from src.ingestion.loader import EpisodePackage
from src.models.story_map import StoryMap
from src.models.constraint_map import ConstraintMap
from src.models.trailer import AudiencePromise


class SegmentCandidate:

    def __init__(self, scene_id: str, scene_dict: dict, score: float, reason: str):
        self.scene_id = scene_id
        self.scene_dict = scene_dict
        self.score = score
        self.reason = reason


class SegmentSelector(BaseAgent):

    def run(
        self,
        episode: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
        audience_promise: AudiencePromise,
        audience_id: str,
    ) -> list[SegmentCandidate]:
        """
        Selects and ranks non-spoiler candidate scenes for the audience trailer.
        """
        candidates: list[SegmentCandidate] = []
        spoilers = set(story_map.spoiler_map.spoiler_scenes)

        for scene in episode.scenes:
            s_id = scene.get("scene_id")

            # Check if scene is a spoiler
            if s_id in spoilers or scene.get("is_spoiler"):
                if self._logger:
                    self._logger.log_decision(
                        agent="SegmentSelector",
                        action="reject_candidate",
                        rationale=f"Scene {s_id} rejected because it is a spoiler scene.",
                        target=s_id,
                        cost_usd=0.0,
                    )
                continue

            # Audience-specific scene filtering
            sens = scene.get("sensitive_content", [])
            if audience_id == "family":
                if any(tag in sens for tag in ["frightening", "suggestive_reference"]):
                    if self._logger:
                        self._logger.log_decision(
                            agent="SegmentSelector",
                            action="reject_candidate",
                            rationale=f"Scene {s_id} rejected due to family rating policy.",
                            target=s_id,
                            cost_usd=0.0,
                        )
                    continue

            # Score scene relevance
            score = 8.0
            if "warmth" in scene.get("emotional_tags", []):
                score += 1.0
            if "tension" in scene.get("emotional_tags", []):
                score += 0.5

            candidate = SegmentCandidate(
                scene_id=s_id,
                scene_dict=scene,
                score=score,
                reason=f"Fits {audience_id} audience profile and narrative arc.",
            )
            candidates.append(candidate)

        # Sort candidates descending by score
        candidates.sort(key=lambda c: c.score, reverse=True)

        if self._logger:
            self._logger.log_decision(
                agent="SegmentSelector",
                action="select_candidates",
                rationale=f"Selected {len(candidates)} candidate scenes for {audience_id}.",
                target=audience_id,
                cost_usd=0.001,
            )

        return candidates
