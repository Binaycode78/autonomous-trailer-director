"""
Orchestrator
============
Coordinates the full Autonomous Trailer Director pipeline:

1. Load episode package
2. Validate episode data
3. Run analysis agents (story, constraint, audience)
4. Run planning agents per audience (promise → segments → arc)
5. Run verification pipeline per trailer
6. Run repair agent for failures
7. Save all outputs

Also handles surprise events during a run.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.ingestion.loader import (
    load_episode_package,
    load_policies,
    load_contracts,
    load_audience_profiles,
    load_cost_sheet,
)
from src.ingestion.validator import validate_episode_package
from src.agents.story_agent import StoryAgent
from src.agents.constraint_agent import ConstraintAgent
from src.agents.audience_agent import AudienceAgent
from src.agents.planning.promise_planner import PromisePlanner
from src.agents.planning.segment_selector import SegmentSelector
from src.agents.planning.narrative_arc import NarrativeArc
from src.agents.repair_agent import RepairAgent
from src.verification.pipeline import VerificationPipeline
from src.events.surprise_handler import SurpriseEventHandler
from src.llm.client import get_client
from src.utils.cost_tracker import CostTracker
from src.utils.logger import DecisionLogger
from src.models.trailer import TrailerEDL, ValidationStatus
from src.models.story_map import StoryMap
from src.models.constraint_map import ConstraintMap

logger = logging.getLogger(__name__)

AUDIENCES = ["family", "young_adult", "dialect_region"]


class TrailerDirectorOrchestrator:
    """
    Main pipeline coordinator for the Autonomous Trailer Director.
    """

    def __init__(
        self,
        data_dir: str,
        output_dir: str,
        mode: str = "mock",
        model: str = "llama-3.3-70b-versatile",
        event: Optional[str] = None,
        replay_dir: Optional[str] = None,
        budget_limit: float = 2.0,
    ):
        self.data_dir = data_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.model = model
        self.event = event
        self.replay_dir = replay_dir

        # Core services
        self.cost_tracker = CostTracker(budget_limit=budget_limit)
        self.decision_logger = DecisionLogger(
            log_file=str(self.output_dir / "decision_log.jsonl")
        )
        self.llm = get_client(mode=mode, model=model, replay_dir=replay_dir)
        self.surprise_handler = SurpriseEventHandler(
            self.decision_logger, self.cost_tracker
        )

        # State
        self.episode = None
        self.policies = None
        self.contracts = None
        self.audience_profiles = None
        self.cost_sheet = None
        self.story_map: Optional[StoryMap] = None
        self.constraint_map: Optional[ConstraintMap] = None
        self.trailers: list[TrailerEDL] = []

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """
        Execute the full pipeline. Returns a summary dict.
        """
        logger.info("=" * 60)
        logger.info("AUTONOMOUS TRAILER DIRECTOR — STARTING")
        logger.info(f"Mode: {self.mode} | Event: {self.event}")
        logger.info("=" * 60)

        # Phase 1: Ingestion
        self._phase_ingestion()

        # Phase 2: Analysis
        self._phase_analysis()

        # Phase 3: Inject surprise event BEFORE planning (if mid-run event)
        if self.event and self.event in [
            "music_rights_expired_before_planning",
            "spoiler_reclassified_before_planning",
            "bias_detected",
        ]:
            self._inject_surprise_event()

        # Phase 4: Planning (one trailer per audience)
        for audience_id in AUDIENCES:
            trailer = self._phase_planning(audience_id)
            self.trailers.append(trailer)

        # Phase 5: Inject surprise event AFTER first trailer (mid-planning)
        if self.event and self.event in [
            "music_rights_expired",
            "spoiler_reclassified",
            "clickbait_requested",
            "dialect_subtitle_changed",
            "model_unavailable",
            "scene_hallucination",
        ]:
            self._inject_surprise_event()
            # Re-verify affected trailers
            affected = self._identify_affected_trailers()
            for trailer in self.trailers:
                if trailer.trailer_id in affected:
                    logger.info(f"Re-verifying trailer: {trailer.trailer_id}")
                    trailer = self._phase_verification_and_repair(
                        trailer,
                        audience_id=trailer.audience.replace(" ", "_").replace("-", "_"),
                    )

        # Phase 6: Verification and repair for all trailers
        repaired_trailers = []
        for trailer in self.trailers:
            audience_id = trailer.audience.replace(" ", "_").replace("-", "_")
            trailer = self._phase_verification_and_repair(trailer, audience_id)
            repaired_trailers.append(trailer)
        self.trailers = repaired_trailers

        # Phase 7: Save outputs
        self._save_outputs()

        # Phase 8: Generate validation report
        self._generate_validation_report()

        summary = self._build_summary()
        logger.info("=" * 60)
        logger.info("AUTONOMOUS TRAILER DIRECTOR — COMPLETE")
        logger.info(f"Cost: ${summary['total_cost_usd']:.4f}")
        logger.info(f"Trailers: {len(self.trailers)}")
        logger.info("=" * 60)

        return summary

    # ------------------------------------------------------------------
    # Pipeline phases
    # ------------------------------------------------------------------

    def _phase_ingestion(self):
        """Load and validate the episode package."""
        logger.info("[Phase 1] Loading episode package...")
        self.episode = load_episode_package(self.data_dir)
        self.policies = load_policies(self.data_dir)
        self.contracts = load_contracts(self.data_dir)
        self.audience_profiles = load_audience_profiles(self.data_dir)
        self.cost_sheet = load_cost_sheet(self.data_dir)

        # Update budget from cost sheet
        self.cost_tracker.budget_limit = self.cost_sheet.get("budget_total_usd", 2.0)

        # Validate
        validation = validate_episode_package(self.episode)
        if validation.get("errors"):
            logger.error(f"Episode validation errors: {validation['errors']}")
            raise ValueError(f"Episode package invalid: {validation['errors']}")
        if validation.get("warnings"):
            for w in validation["warnings"]:
                logger.warning(f"[Ingestion] {w}")

        logger.info(
            f"[Phase 1] Loaded: {len(self.episode.scenes)} scenes, "
            f"{len(self.episode.dialogue)} dialogue lines"
        )

    def _phase_analysis(self):
        """Run story, constraint, and audience analysis agents."""
        logger.info("[Phase 2] Running analysis agents...")

        # Story Agent
        story_agent = StoryAgent(
            llm_client=self.llm,
            cost_tracker=self.cost_tracker,
            logger=self.decision_logger,
        )
        self.story_map = story_agent.run(self.episode)
        self._save_json(self.story_map.model_dump(), "story_map.json")
        logger.info(
            f"[Phase 2] Story map: {len(self.story_map.characters)} chars, "
            f"{len(self.story_map.spoiler_map.spoiler_scenes)} spoilers"
        )

        # Constraint Agent
        constraint_agent = ConstraintAgent(
            llm_client=self.llm,
            cost_tracker=self.cost_tracker,
            logger=self.decision_logger,
        )
        self.constraint_map = constraint_agent.run(
            self.policies, self.contracts, self.story_map
        )
        self._save_json(self.constraint_map.model_dump(), "constraint_map.json")
        logger.info(
            f"[Phase 2] Constraint map: {len(self.constraint_map.rules)} rules, "
            f"{len(self.constraint_map.prompt_injection_attempts)} injection attempts detected"
        )

    def _phase_planning(self, audience_id: str) -> TrailerEDL:
        """Plan a trailer for a given audience."""
        logger.info(f"[Phase 3] Planning trailer for audience: {audience_id}")

        profile = self.audience_profiles.get(audience_id, {})
        policy = self.policies.get(audience_id, {})

        # Audience promise
        audience_agent = AudienceAgent(
            llm_client=self.llm,
            cost_tracker=self.cost_tracker,
            logger=self.decision_logger,
        )
        audience_promise = audience_agent.run(
            audience_id=audience_id,
            profile=profile,
            story_map=self.story_map,
            constraint_map=self.constraint_map,
        )

        # Creative brief
        promise_planner = PromisePlanner(
            llm_client=self.llm,
            cost_tracker=self.cost_tracker,
            logger=self.decision_logger,
        )
        creative_brief = promise_planner.run(
            audience_promise=audience_promise,
            story_map=self.story_map,
            constraint_map=self.constraint_map,
        )

        # Segment selection
        selector = SegmentSelector(
            llm_client=self.llm,
            cost_tracker=self.cost_tracker,
            logger=self.decision_logger,
        )
        candidate_segments = selector.run(
            episode=self.episode,
            story_map=self.story_map,
            constraint_map=self.constraint_map,
            audience_promise=audience_promise,
            audience_id=audience_id,
        )

        # Narrative arc
        max_duration = policy.get("max_trailer_duration_seconds", 60)
        arc_builder = NarrativeArc(
            llm_client=self.llm,
            cost_tracker=self.cost_tracker,
            logger=self.decision_logger,
        )
        segments, text_cards = arc_builder.run(
            candidate_segments=candidate_segments,
            audience_promise=audience_promise,
            target_duration=max_duration,
            audience_id=audience_id,
        )

        # Calculate total duration
        from src.utils.timecode import duration_seconds
        total_duration = sum(
            duration_seconds(s.source_in, s.source_out) for s in segments
        )

        # Build initial trailer EDL
        trailer_id_map = {
            "family": "family_v1",
            "young_adult": "young_adult_v1",
            "dialect_region": "dialect_region_v1",
        }
        audience_label_map = {
            "family": "family viewers",
            "young_adult": "young adult viewers",
            "dialect_region": "dialect-region viewers",
        }

        from src.models.trailer import ValidationResult
        trailer = TrailerEDL(
            trailer_id=trailer_id_map.get(audience_id, f"{audience_id}_v1"),
            audience=audience_label_map.get(audience_id, audience_id),
            duration_seconds=round(total_duration, 1),
            audience_promise=audience_promise,
            creative_brief=creative_brief,
            segments=segments,
            text_cards=text_cards,
            validation=ValidationResult(
                status=ValidationStatus.PASS,
                checks_run=[],
                warnings=[],
                failures=[],
                human_approvals_required=[],
                estimated_cost_usd=self.cost_tracker.get_summary()["total_cost_usd"],
                fallback_plan_available=False,
            ),
            cost_estimate_usd=self.cost_tracker.get_summary()["total_cost_usd"],
            decision_notes=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            f"[Phase 3] Trailer planned: {trailer.trailer_id} — "
            f"{len(segments)} segments, {total_duration:.1f}s"
        )
        return trailer

    def _phase_verification_and_repair(
        self, trailer: TrailerEDL, audience_id: str
    ) -> TrailerEDL:
        """Verify a trailer and repair failures."""
        logger.info(f"[Phase 4] Verifying trailer: {trailer.trailer_id}")

        pipeline = VerificationPipeline()
        validation_result = pipeline.run(
            trailer=trailer,
            episode=self.episode,
            story_map=self.story_map,
            constraint_map=self.constraint_map,
            policies=self.policies,
            contracts=self.contracts,
            cost_tracker=self.cost_tracker,
        )
        trailer.validation = validation_result

        # Collect all hard failures for repair
        all_failures = []
        for seg in trailer.segments:
            all_failures.extend(seg.risk_flags)

        if all_failures:
            logger.info(
                f"[Phase 5] Repairing {len(all_failures)} failure(s) "
                f"in trailer: {trailer.trailer_id}"
            )
            repair_agent = RepairAgent(
                llm_client=self.llm,
                cost_tracker=self.cost_tracker,
                logger=self.decision_logger,
            )
            trailer, unresolved = repair_agent.run(
                trailer=trailer,
                failures=all_failures,
                episode=self.episode,
                story_map=self.story_map,
                constraint_map=self.constraint_map,
                audience_id=audience_id,
            )
            if unresolved:
                logger.warning(
                    f"[Phase 5] {len(unresolved)} unresolved issues in {trailer.trailer_id}"
                )

        logger.info(
            f"[Phase 4-5] {trailer.trailer_id} status: {trailer.validation.status}"
        )
        return trailer

    # ------------------------------------------------------------------
    # Surprise event injection
    # ------------------------------------------------------------------

    def _inject_surprise_event(self):
        """Inject the configured surprise event."""
        logger.info(f"[Surprise] Injecting event: {self.event}")

        if self.event == "music_rights_expired":
            self.trailers, self.constraint_map = (
                self.surprise_handler.handle_music_rights_expired(
                    track_id="track_02",
                    trailers=self.trailers,
                    constraint_map=self.constraint_map,
                )
            )

        elif self.event == "spoiler_reclassified":
            self.trailers, self.story_map, self.constraint_map = (
                self.surprise_handler.handle_spoiler_reclassified(
                    scene_id="scene_05",
                    reason="New editorial review determined scene_05 reveals antagonist identity prematurely",
                    trailers=self.trailers,
                    story_map=self.story_map,
                    constraint_map=self.constraint_map,
                )
            )

        elif self.event == "clickbait_requested":
            result = self.surprise_handler.handle_clickbait_request(
                requested_promise="An action-packed thriller with explosive confrontations",
                episode_facts=[s.description for s in self.episode.scenes],
                trailer_id="young_adult_v1",
            )
            logger.info(f"[Surprise] Clickbait result: {result['status']} — {result['reason']}")

        elif self.event == "model_unavailable":
            result = self.surprise_handler.handle_model_unavailable(
                model_name="llama-3.3-70b-versatile",
                fallback_model="llama-3.1-8b-instant",
            )
            # Swap to fallback model
            self.llm = get_client(mode=self.mode, model=result["fallback_model"])

        elif self.event == "scene_hallucination":
            result = self.surprise_handler.handle_scene_hallucination(
                hallucinated_scene_id="scene_99",
                agent_name="SegmentSelector",
                trailer_id="young_adult_v1",
            )
            logger.warning(f"[Surprise] Hallucination logged: {result}")

        elif self.event == "bias_detected":
            self.trailers = self.surprise_handler.handle_bias_detected(
                audience_id="dialect_region",
                bias_description=(
                    "historic_high_performing_scenes over-represents rural engagement metrics. "
                    "Data collected 2019-2021 excludes urban dialect speakers."
                ),
                affected_data_field="historic_high_performing_scenes",
                trailers=self.trailers,
            )

        elif self.event == "dialect_subtitle_changed":
            self.trailers, self.story_map = (
                self.surprise_handler.handle_dialect_subtitle_changed(
                    scene_id="scene_07",
                    line_id="dlg_018",
                    old_text="The sea never forgets, aye.",
                    new_text="The blood never forgets, aye — nor forgives.",
                    relationship_changed=(
                        "Dorian's line now implies Elena is his daughter, "
                        "not just a former neighbor — potential spoiler in dialect track"
                    ),
                    trailers=self.trailers,
                    story_map=self.story_map,
                )
            )

    def _identify_affected_trailers(self) -> list[str]:
        """Return IDs of trailers that need re-verification after an event."""
        affected = set()
        for trailer in self.trailers:
            for seg in trailer.segments:
                if seg.human_approval_required or seg.risk_flags:
                    affected.add(trailer.trailer_id)
        return list(affected)

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def _save_json(self, data: dict, filename: str):
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_outputs(self):
        """Save all trailer EDLs."""
        for trailer in self.trailers:
            filename_map = {
                "family_v1": "family_trailer.json",
                "young_adult_v1": "young_adult_trailer.json",
                "dialect_region_v1": "dialect_region_trailer.json",
            }
            filename = filename_map.get(trailer.trailer_id, f"{trailer.trailer_id}.json")
            self._save_json(trailer.model_dump(), filename)
            logger.info(f"[Output] Saved: {filename}")

    def _generate_validation_report(self):
        """Generate a human-readable validation_report.md."""
        lines = [
            "# Autonomous Trailer Director — Validation Report",
            f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
            f"Mode: {self.mode}",
            f"Event Injected: {self.event or 'none'}",
            "\n---\n",
        ]

        cost_summary = self.cost_tracker.get_summary()
        lines += [
            "## Cost Summary",
            f"- Total cost: **${cost_summary['total_cost_usd']:.4f}**",
            f"- Total LLM calls: {cost_summary['total_calls']}",
            f"- Budget limit: ${cost_summary['budget_limit']:.2f}",
            f"- Budget used: {cost_summary.get('percent_used', 0):.1f}%",
            "\n---\n",
        ]

        for trailer in self.trailers:
            v = trailer.validation
            status_emoji = {
                "PASS": "✅",
                "PASS_WITH_WARNINGS": "⚠️",
                "FAIL": "❌",
                "FAIL_UNRESOLVED": "🚫",
                "HUMAN_APPROVAL_REQUIRED": "👤",
            }.get(v.status.value, "❓")

            lines += [
                f"## {status_emoji} {trailer.trailer_id} ({trailer.audience})",
                f"**Status**: `{v.status.value}`",
                f"**Duration**: {trailer.duration_seconds}s",
                f"**Segments**: {len(trailer.segments)}",
                f"**Audience Promise**: {trailer.audience_promise.statement}",
                "",
                f"**Checks Run**: {', '.join(v.checks_run)}",
            ]

            if v.warnings:
                lines.append("\n**Warnings**:")
                for w in v.warnings:
                    lines.append(f"- ⚠️ {w}")

            if v.failures:
                lines.append("\n**Failures**:")
                for f in v.failures:
                    lines.append(f"- ❌ {f}")

            if v.human_approvals_required:
                lines.append("\n**Human Approval Required**:")
                for ha in v.human_approvals_required:
                    lines.append(f"- 👤 {ha}")

            lines.append("\n**Segments**:")
            for seg in trailer.segments:
                flag_str = f" [{len(seg.risk_flags)} flags]" if seg.risk_flags else ""
                lines.append(
                    f"- `{seg.source_in}` → `{seg.source_out}` | {seg.video}{flag_str} | {seg.reason[:80]}..."
                )

            lines.append("\n---\n")

        report_path = self.output_dir / "validation_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("[Output] Saved: validation_report.md")

    def _build_summary(self) -> dict:
        cost = self.cost_tracker.get_summary()
        return {
            "trailers_generated": len(self.trailers),
            "trailer_statuses": {
                t.trailer_id: t.validation.status.value for t in self.trailers
            },
            "total_cost_usd": cost["total_cost_usd"],
            "total_llm_calls": cost["total_calls"],
            "event_injected": self.event,
            "output_dir": str(self.output_dir),
        }
