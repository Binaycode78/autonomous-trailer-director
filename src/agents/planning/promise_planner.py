"""
Promise Planner Agent
=====================
Builds audience-specific creative briefs based on audience promises and constraint maps.
"""
from __future__ import annotations

from typing import Any
from src.agents.base_agent import BaseAgent
from src.models.trailer import AudiencePromise
from src.models.story_map import StoryMap
from src.models.constraint_map import ConstraintMap


class PromisePlanner(BaseAgent):

    def run(
        self,
        audience_promise: AudiencePromise,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
    ) -> str:
        """
        Generates a structured creative brief string for trailer generation.
        """
        system_prompt = (
            "You are a creative trailer director. Build a concise, compelling "
            "creative brief that aligns with the audience promise while explicitly "
            "honoring all content, spoiler, and legal restrictions."
        )

        user_prompt = f"""
AUDIENCE PROMISE:
Statement: {audience_promise.statement}
Tone: {audience_promise.tone}
Expectations: {audience_promise.what_audience_will_expect}
Protected Elements: {', '.join(audience_promise.what_is_protected)}

EXCLUDED RULES FROM CONSTRAINT MAP:
{[r.description for r in constraint_map.rules if r.action == 'EXCLUDE']}

Build a 3-paragraph creative brief.
"""
        # Call LLM or generate structured brief
        try:
            response = self._call_llm(system_prompt, user_prompt)
            brief = response.strip()
        except Exception:
            # Fallback deterministic brief
            brief = (
                f"CREATIVE BRIEF ({audience_promise.tone.upper()} TRAILER)\n"
                f"Goal: Deliver on the audience promise: '{audience_promise.statement}'.\n"
                f"Tone & Feel: {audience_promise.tone}.\n"
                f"Narrative Focus: Highlight emotional beats and mystery while strictly excluding "
                f"spoiler scenes ({', '.join(story_map.spoiler_map.spoiler_scenes)}).\n"
                f"Safety & Compliance: Honor rating policies and music licensing rules."
            )

        if self._logger:
            self._logger.log_decision(
                agent="PromisePlanner",
                action="create_creative_brief",
                rationale=f"Created creative brief for promise: {audience_promise.statement[:50]}",
                target="creative_brief",
                cost_usd=0.001,
            )

        return brief
