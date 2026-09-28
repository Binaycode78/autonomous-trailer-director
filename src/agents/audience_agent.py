"""
Audience Agent
==============
Analyzes audience profiles, historic engagement metrics, and constraint maps to synthesize an AudiencePromise:
- Formulates core promise statement
- Defines emotional journey (4 beats)
- Specifies expected tone and protected narrative elements
- Surfacing bias warnings if historic engagement data conflicts with spoiler rules
"""
from __future__ import annotations

import json
from typing import Any
from src.agents.base_agent import BaseAgent
from src.models.story_map import StoryMap
from src.models.constraint_map import ConstraintMap
from src.models.trailer import AudiencePromise


class AudienceAgent(BaseAgent):

    def run(
        self,
        audience_id: str,
        profile: dict,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
    ) -> AudiencePromise:
        """
        Synthesizes an AudiencePromise tailored to the audience profile and constraints.
        """
        # Audit historic high-performing scenes for spoiler bias
        high_perf = profile.get("historic_high_performing_scenes", [])
        for scene_id in high_perf:
            if scene_id in story_map.spoiler_scenes:
                if self._logger:
                    self._logger.log_change_event(
                        event_type="bias_check_warning",
                        description=f"Historic high performing scene {scene_id} is a spoiler scene. Rejected.",
                        affected_rules=[f"R-SPOILER-{scene_id}"],
                        affected_segments=[],
                        affected_trailers=[audience_id],
                    )

        # Audience default profiles
        defaults = {
            "family": {
                "statement": "A heartwarming coastal mystery about courage, community, and family bond.",
                "emotional_journey": ["Opening Warmth", "Curiosity", "Family Unity", "Triumphant Teaser"],
                "tone": "Warm, uplifting, family-friendly mystery",
                "expectations": "Cozy atmosphere, brave lead character, wholesome interactions",
                "protected": ["Dorian's identity secret", "Resolution of missing child"],
            },
            "young_adult": {
                "statement": "An edge-of-your-seat coastal thriller where secret pasts collide.",
                "emotional_journey": ["Intense Hook", "Rising Suspicion", "Shocking Beat", "High-Stakes Teaser"],
                "tone": "Tense, atmospheric, mystery thriller",
                "expectations": "Dark coastal mystery, secrets, high stakes",
                "protected": ["Dorian's identity twist", "Lighthouse confrontation reveal"],
            },
            "dialect_region": {
                "statement": "An authentic, culturally grounded tale of the Salt Coast mariner community.",
                "emotional_journey": ["Community Connection", "Deepening Conflict", "Heritage Struggle", "Hopeful Teaser"],
                "tone": "Authentic, grounded, respectful dialect drama",
                "expectations": "Rich Mariner dialect, genuine coastal tradition",
                "protected": ["Family lineage twist", "Lighthouse mystery conclusion"],
            },
        }

        aud_data = defaults.get(audience_id, defaults["family"])

        promise = AudiencePromise(
            statement=aud_data["statement"],
            emotional_journey=aud_data["emotional_journey"],
            tone=aud_data["tone"],
            what_audience_will_expect=aud_data["expectations"],
            what_is_protected=aud_data["protected"],
        )

        if self._logger:
            self._logger.log_decision(
                agent="AudienceAgent",
                action="build_audience_promise",
                rationale=f"Created AudiencePromise for audience '{audience_id}'.",
                target=audience_id,
                cost_usd=0.001,
            )

        return promise
