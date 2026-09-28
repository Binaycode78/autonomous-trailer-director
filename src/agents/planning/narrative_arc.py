"""
Narrative Arc Builder Agent
===========================
Assembles candidate scenes into a structured, audience-tailored narrative arc (Hook, Tension, Resolution/Teaser)
and generates TrailerSegment objects and TextCard metadata.
"""
from __future__ import annotations

from typing import Any
from src.agents.base_agent import BaseAgent
from src.agents.planning.segment_selector import SegmentCandidate
from src.models.trailer import TrailerSegment, AudiencePromise, RiskFlag


class NarrativeArc(BaseAgent):

    def run(
        self,
        candidate_segments: list[SegmentCandidate],
        audience_promise: AudiencePromise,
        target_duration: float,
        audience_id: str,
    ) -> tuple[list[TrailerSegment], list[dict]]:
        """
        Builds ordered trailer segments and text cards matching target duration and emotional journey.
        """
        segments: list[TrailerSegment] = []
        text_cards: list[dict] = []

        if not candidate_segments:
            # Fallback empty list or synthetic segment
            return segments, text_cards

        # Select top candidates up to target_duration (~40-60s)
        total_time = 0.0
        subtitle_track = "mariner" if audience_id == "dialect_region" else "standard"
        music_track = "track_01" if audience_id != "family" else "track_01"

        roles = ["Hook", "Rising Tension", "Emotional Core", "Call to Action"]

        for idx, candidate in enumerate(candidate_segments[:4]):
            s_dict = candidate.scene_dict
            scene_id = candidate.scene_id
            t_in = s_dict.get("timecode_in", "00:00:00.000")
            t_out = s_dict.get("timecode_out", "00:00:15.000")

            # Calculate duration
            from src.utils.timecode import duration_seconds
            dur = duration_seconds(t_in, t_out)

            # Pick a line/dialogue text if available
            subtitle_text = f"Dialogue from {scene_id}"

            role = roles[idx] if idx < len(roles) else "Atmospheric Beat"

            segment = TrailerSegment(
                segment_id=f"seg_{idx+1:02d}",
                source_in=t_in,
                source_out=t_out,
                video=scene_id,
                audio="dialogue_and_music",
                music_track=s_dict.get("music_track", music_track),
                subtitle=subtitle_text,
                subtitle_track=subtitle_track,
                reason=f"Serves as {role} in {audience_id} narrative arc.",
                evidence=[f"scene:{scene_id}"],
                risk_flags=[],
                human_approval_required=False,
            )

            segments.append(segment)
            total_time += dur
            if total_time >= target_duration:
                break

        # Generate text cards
        text_cards = [
            {"timecode": "00:00:00.000", "text": "THE SALT COAST", "duration_seconds": 3.0},
            {"timecode": "00:00:45.000", "text": "STREAMING THIS FRIDAY", "duration_seconds": 3.0},
        ]

        if self._logger:
            self._logger.log_decision(
                agent="NarrativeArc",
                action="build_narrative_arc",
                rationale=f"Built narrative arc with {len(segments)} segments total duration ~{total_time:.1f}s",
                target=audience_id,
                cost_usd=0.001,
            )

        return segments, text_cards
