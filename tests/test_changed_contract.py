"""
Test: Music contract change triggers targeted re-verification of only affected trailers.

Proves the system does targeted replanning, not full rebuild.
"""

import pytest
from tests.conftest import make_segment, make_episode, make_story_map, make_constraint_map
from src.events.surprise_handler import SurpriseEventHandler
from src.models.constraint_map import ConstraintMap, ConstraintRule
from src.models.trailer import TrailerEDL, AudiencePromise, ValidationResult, ValidationStatus


def make_minimal_trailer(trailer_id, music_track, audience='family viewers'):
    """Build a minimal TrailerEDL for testing."""
    seg = make_segment('seg_01', 'scene_01', music_track=music_track)
    # Convert dict to TrailerSegment-like object with attribute access
    from src.models.trailer import TrailerSegment, RiskFlag
    segment = TrailerSegment(
        segment_id=seg['segment_id'],
        source_in=seg['source_in'],
        source_out=seg['source_out'],
        video=seg['video'],
        audio=seg['audio'],
        music_track=seg['music_track'],
        subtitle=seg['subtitle'],
        subtitle_track=seg['subtitle_track'],
        reason=seg['reason'],
        evidence=seg['evidence'],
        risk_flags=[],
    )
    promise = AudiencePromise(
        statement='Test promise',
        emotional_journey=['Hook', 'Tension', 'Pull', 'CTA'],
        tone='warm',
        what_audience_will_expect='A mystery',
        what_is_protected=['Twist'],
    )
    validation = ValidationResult(
        status=ValidationStatus.PASS,
        checks_run=[],
        warnings=[],
        failures=[],
        human_approvals_required=[],
        estimated_cost_usd=0.0,
        fallback_plan_available=False,
    )
    return TrailerEDL(
        trailer_id=trailer_id,
        audience=audience,
        duration_seconds=45.0,
        audience_promise=promise,
        creative_brief='A test brief.',
        segments=[segment],
        text_cards=[],
        validation=validation,
        cost_estimate_usd=0.0,
        decision_notes=[],
        generated_at='2026-09-28T00:00:00Z',
    )


class TestChangedContract:

    def setup_method(self):
        self.constraint_map_data = make_constraint_map()

    def _make_constraint_map(self):
        rules = [ConstraintRule(**r) for r in self.constraint_map_data['rules']]
        return ConstraintMap(
            rules=rules,
            prompt_injection_attempts=[],
            last_updated='2026-09-28T00:00:00Z',
            change_log=[],
        )

    def test_music_rights_expiry_flags_only_affected_trailers(self, mock_decision_logger, mock_cost_tracker):
        """
        When track_02 rights expire, only trailers using track_02 are flagged.
        Trailers using track_01 are not touched.
        """
        trailer_with_track02 = make_minimal_trailer('young_adult_v1', 'track_02', 'young adult viewers')
        trailer_with_track01 = make_minimal_trailer('family_v1', 'track_01', 'family viewers')
        trailers = [trailer_with_track02, trailer_with_track01]

        constraint_map = self._make_constraint_map()
        handler = SurpriseEventHandler(mock_decision_logger, mock_cost_tracker)
        updated_trailers, updated_map = handler.handle_music_rights_expired(
            track_id='track_02',
            trailers=trailers,
            constraint_map=constraint_map,
        )

        # Only young_adult_v1 (using track_02) should have flags
        ya_trailer = next(t for t in updated_trailers if t.trailer_id == 'young_adult_v1')
        family_trailer = next(t for t in updated_trailers if t.trailer_id == 'family_v1')

        assert ya_trailer.segments[0].human_approval_required is True, (
            "young_adult_v1 uses track_02 and must be flagged after rights expiry"
        )
        assert family_trailer.segments[0].human_approval_required is False, (
            "family_v1 uses track_01 and must NOT be flagged (targeted replanning)"
        )

    def test_expired_track_rule_added_to_constraint_map(self, mock_decision_logger, mock_cost_tracker):
        """After expiry, an EXCLUDE rule for track_02 must be added."""
        trailers = [make_minimal_trailer('ya_v1', 'track_02')]
        constraint_map = self._make_constraint_map()
        initial_rule_count = len(constraint_map.rules)

        handler = SurpriseEventHandler(mock_decision_logger, mock_cost_tracker)
        _, updated_map = handler.handle_music_rights_expired('track_02', trailers, constraint_map)

        new_rules = [r for r in updated_map.rules if 'track_02' in r.applies_to and r.action == 'EXCLUDE' and r.active]
        assert len(new_rules) > 0, "An active EXCLUDE rule for track_02 must be added"
        assert len(updated_map.change_log) > 0, "Change must be recorded in the change log"

    def test_change_log_records_event(self, mock_decision_logger, mock_cost_tracker):
        """The constraint map change_log must record the expiry event."""
        trailers = [make_minimal_trailer('ya_v1', 'track_02')]
        constraint_map = self._make_constraint_map()
        handler = SurpriseEventHandler(mock_decision_logger, mock_cost_tracker)
        _, updated_map = handler.handle_music_rights_expired('track_02', trailers, constraint_map)

        assert any(entry.get('event') == 'music_rights_expired' for entry in updated_map.change_log)
