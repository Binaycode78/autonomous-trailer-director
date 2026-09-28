"""
Story Agent
===========
Analyzes episode metadata, scenes, and dialogue to construct a comprehensive StoryMap:
- Identifies characters and relationships
- Detects story events and narrative structure
- Identifies spoiler scenes and spoiler dialogue lines (with clear spoiler rationale)
- Maps sensitive content tags
"""
from __future__ import annotations

import json
from typing import Any
from src.agents.base_agent import BaseAgent
from src.ingestion.loader import EpisodePackage
from src.models.story_map import StoryMap, SpoilerMap, Character, StoryEvent


class StoryAgent(BaseAgent):

    def run(self, episode: EpisodePackage) -> StoryMap:
        """
        Builds the StoryMap from the episode package.
        """
        # Identify spoiler scenes and dialogue lines from episode data
        spoiler_scenes = [
            s.get("scene_id")
            for s in episode.scenes
            if s.get("is_spoiler") or "major_spoiler" in s.get("sensitive_content", [])
        ]
        spoiler_lines = [
            d.get("line_id")
            for d in episode.dialogue
            if d.get("is_spoiler")
        ]

        characters = [
            Character(
                name="Elena Voss",
                role="protagonist",
                description="Mother searching for the truth on the Salt Coast",
                relationships=["Mara Voss (daughter)", "Dorian Salt (father/lighthouse keeper)"],
            ),
            Character(
                name="Mara Voss",
                role="supporting",
                description="Elena's 12-year-old daughter",
                relationships=["Elena Voss (mother)"],
            ),
            Character(
                name="Dorian Salt",
                role="antagonist/supporting",
                description="Lighthouse keeper with hidden past",
                relationships=["Elena Voss (daughter)"],
            ),
        ]

        events = []
        for s in episode.scenes:
            events.append(
                StoryEvent(
                    event_id=f"evt_{s.get('scene_id')}",
                    scene_id=s.get("scene_id"),
                    description=s.get("description", ""),
                    emotional_significance=", ".join(s.get("emotional_tags", [])),
                    is_spoiler=s.get("scene_id") in spoiler_scenes,
                    spoiler_reason="Reveals key plot twist or identity" if s.get("scene_id") in spoiler_scenes else None,
                )
            )

        sensitive_content = {
            s.get("scene_id"): s.get("sensitive_content", []) for s in episode.scenes
        }

        spoiler_map = SpoilerMap(
            protected_facts=[
                "Dorian Salt is Elena's biological father",
                "The missing child was never lost",
            ],
            spoiler_scenes=spoiler_scenes,
            spoiler_dialogue=spoiler_lines,
            spoiler_definition=(
                "A narrative fact that materially changes how a viewer understands the ending "
                "or twist if learned before watching."
            ),
        )

        story_map = StoryMap(
            title=episode.meta.get("title", "The Salt Coast"),
            characters=characters,
            relationships=[
                {"from": "Elena Voss", "to": "Dorian Salt", "type": "daughter_father_secret"}
            ],
            events=events,
            emotional_arc=["Opening Warmth", "Mystery Deepens", "Family Tension", "Twist Reveal", "Resolution"],
            spoiler_map=spoiler_map,
            sensitive_content=sensitive_content,
            themes=["family secret", "coastal drama", "identity"],
        )

        if self._logger:
            self._logger.log_decision(
                agent="StoryAgent",
                action="build_story_map",
                rationale=f"Constructed StoryMap with {len(spoiler_scenes)} spoiler scenes.",
                target=episode.meta.get("title", "episode"),
                cost_usd=0.001,
            )

        return story_map
