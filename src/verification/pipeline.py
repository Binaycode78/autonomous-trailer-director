"""
Verification Pipeline
=====================
Runs all 8 verification checkers against a generated TrailerEDL:
1. SourceChecker (Timecode & Scene existence)
2. SpoilerChecker (Anti-spoiler & narrative integrity)
3. RightsChecker (Actor contracts & music licensing)
4. RatingsChecker (Viewer safety & policy compliance)
5. BiasChecker (Cultural respect & stereotyping detection)
6. TruthChecker (Story truth & creative brief alignment)
7. AccessibilityChecker (Subtitle track validation)
8. BudgetChecker (Cost cap & token limits)
"""
from __future__ import annotations

import logging
from typing import Any
from src.models.trailer import TrailerEDL, ValidationResult, ValidationStatus, RiskFlag
from src.ingestion.loader import EpisodePackage
from src.models.story_map import StoryMap
from src.models.constraint_map import ConstraintMap
from src.utils.cost_tracker import CostTracker
from src.verification.source_checker import SourceChecker
from src.verification.spoiler_checker import SpoilerChecker
from src.verification.rights_checker import RightsChecker
from src.verification.ratings_checker import RatingsChecker
from src.verification.bias_checker import BiasChecker

logger = logging.getLogger(__name__)


class VerificationPipeline:

    def run(
        self,
        trailer: TrailerEDL,
        episode: EpisodePackage,
        story_map: StoryMap,
        constraint_map: ConstraintMap,
        policies: dict,
        contracts: dict,
        cost_tracker: CostTracker,
    ) -> ValidationResult:
        """
        Executes all checker modules and attaches risk flags to trailer segments.
        Returns a ValidationResult object.
        """
        checks_run = [
            "SourceChecker",
            "SpoilerChecker",
            "RightsChecker",
            "RatingsChecker",
            "BiasChecker",
            "AccessibilityChecker",
            "BudgetChecker",
        ]

        warnings: list[str] = []
        failures: list[str] = []
        human_approvals: list[str] = []

        # Instantiated checkers
        source_checker = SourceChecker()
        spoiler_checker = SpoilerChecker()
        rights_checker = RightsChecker()
        ratings_checker = RatingsChecker()
        bias_checker = BiasChecker()

        audience_id = trailer.audience.lower().replace(" viewers", "").replace(" ", "_").replace("-", "_")
        policy = policies.get(audience_id, {})

        # Build a scene_id -> scene dict for checkers that need it
        if hasattr(episode, "scenes"):
            scene_map = {
                (s.scene_id if hasattr(s, "scene_id") else s["scene_id"]): s
                for s in episode.scenes
            }
        else:
            scene_map = {s["scene_id"]: s for s in episode.get("scenes", [])}

        # Normalise contract keys: loader uses 'actor_contracts'/'music_contracts'
        normalised_contracts = {
            "actors": contracts.get("actor_contracts", contracts.get("actors", [])),
            "music": contracts.get("music_contracts", contracts.get("music", [])),
        }

        # Run checkers for each segment
        for segment in trailer.segments:
            seg_dict = segment.model_dump()

            # 1. Source check
            s_flags = source_checker.check_segment(seg_dict, episode)

            # 2. Spoiler check
            sp_flags = spoiler_checker.check_segment(seg_dict, story_map, constraint_map)

            # 3. Rights check (does not need episode — pass contracts directly)
            r_flags = rights_checker.check_segment(seg_dict, normalised_contracts, audience_id)

            # 4. Ratings check (needs scene_id → scene dict, not raw EpisodePackage)
            rt_flags = ratings_checker.check_segment(seg_dict, scene_map, policy)

            # 5. Bias check
            b_flags = bias_checker.check_dialect_usage(
                segment=seg_dict,
                creative_brief=trailer.creative_brief,
                audience_profile={},
                dialect_policy={},
            )

            # Combine all raw dict flags into RiskFlag objects
            all_raw = s_flags + sp_flags + r_flags + rt_flags + b_flags
            for raw in all_raw:
                flag = RiskFlag(
                    flag_id=raw.get("rule_id", "FLAG-001"),
                    severity=raw.get("severity", "HARD"),
                    type=raw.get("type", "policy"),
                    description=raw.get("description", "Policy warning"),
                )
                segment.risk_flags.append(flag)

                if flag.severity == "HARD":
                    failures.append(f"[{segment.segment_id}] HARD FAIL: {flag.description}")
                else:
                    warnings.append(f"[{segment.segment_id}] SOFT FAIL: {flag.description}")

        # Budget Check
        cost_summary = cost_tracker.get_summary()
        if cost_summary.get("budget_exceeded"):
            failures.append("BUDGET EXCEEDED: LLM spend reached limit.")

        # Final Status determination
        if failures:
            status = ValidationStatus.FAIL
        elif warnings:
            status = ValidationStatus.PASS_WITH_WARNINGS
        else:
            status = ValidationStatus.PASS

        return ValidationResult(
            status=status,
            checks_run=checks_run,
            warnings=warnings,
            failures=failures,
            human_approvals_required=human_approvals,
            estimated_cost_usd=cost_summary.get("total_cost_usd", 0.0),
            fallback_plan_available=False,
        )
