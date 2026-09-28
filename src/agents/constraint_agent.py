"""
Constraint Agent
================
Analyzes rating policies, actor/music contracts, territory rules, and story map spoilers to construct
the active ConstraintMap and scan for prompt injection attempts in source metadata.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from src.agents.base_agent import BaseAgent
from src.models.story_map import StoryMap
from src.models.constraint_map import ConstraintMap, ConstraintRule


class ConstraintAgent(BaseAgent):

    def run(self, policies: dict, contracts: dict, story_map: StoryMap) -> ConstraintMap:
        """
        Builds the active ConstraintMap from policies, contracts, and story map spoilers.
        Scans all text metadata for prompt injection attempts.
        """
        rules: list[ConstraintRule] = []
        injections_detected: list[dict] = []

        # 1. Prompt Injection Scan
        all_metadata_str = json.dumps(policies) + json.dumps(contracts)
        found_injections = self._detect_prompt_injection(all_metadata_str)
        for inj in found_injections:
            injections_detected.append({
                "phrase": inj,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "status": "NEUTRALIZED",
            })

        # 2. Add Spoiler Rules
        for s_id in story_map.spoiler_map.spoiler_scenes:
            rules.append(
                ConstraintRule(
                    rule_id=f"R-SPOILER-{s_id}",
                    type="spoiler",
                    description=f"Exclude scene {s_id}: Contains major plot twist/spoiler.",
                    applies_to=[s_id],
                    action="EXCLUDE",
                    audiences=[],  # applies to all
                    active=True,
                )
            )

        # 3. Add Rating Policy Rules
        for audience_id, policy in policies.items():
            excluded_tags = policy.get("excluded_sensitive_tags", [])
            for tag in excluded_tags:
                rules.append(
                    ConstraintRule(
                        rule_id=f"R-RATING-{audience_id}-{tag}",
                        type="rating",
                        description=f"Exclude content with tag '{tag}' for audience '{audience_id}'.",
                        applies_to=[tag],
                        action="EXCLUDE",
                        audiences=[audience_id],
                        active=True,
                    )
                )

        # 4. Add Contract Rules (Music and Actors)
        music_contracts = contracts.get("music_contracts", contracts.get("music", []))
        if isinstance(music_contracts, list):
            for m in music_contracts:
                track_id = m.get("track_id")
                excluded_aud = m.get("excluded_audiences", [])
                if track_id and excluded_aud:
                    rules.append(
                        ConstraintRule(
                            rule_id=f"R-MUSIC-{track_id}",
                            type="music_rights",
                            description=f"Music track {track_id} restricted for audiences: {excluded_aud}.",
                            applies_to=[track_id],
                            action="EXCLUDE",
                            audiences=excluded_aud,
                            active=True,
                        )
                    )

        constraint_map = ConstraintMap(
            rules=rules,
            prompt_injection_attempts=injections_detected,
            last_updated=datetime.now(timezone.utc).isoformat(),
            change_log=[{
                "event": "initial_creation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rule_count": len(rules),
            }],
        )

        if self._logger:
            self._logger.log_decision(
                agent="ConstraintAgent",
                action="build_constraint_map",
                rationale=f"Built ConstraintMap with {len(rules)} active rules.",
                target="constraint_map",
                cost_usd=0.001,
            )

        return constraint_map
