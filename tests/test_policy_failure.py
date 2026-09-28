"""
Test: RatingsChecker blocks age-inappropriate content for each audience.
"""

import pytest
from tests.conftest import make_scene, make_segment
from src.verification.ratings_checker import RatingsChecker


class TestPolicyFailure:

    def setup_method(self):
        self.policies = {
            'family': {
                'audience': 'family',
                'max_age_rating': 'PG',
                'excluded_content_tags': ['frightening', 'suggestive_reference', 'violence', 'strong_language', 'major_spoiler'],
                'max_trailer_duration_seconds': 90,
                'min_trailer_duration_seconds': 30,
                'subtitle_required': True,
            },
            'young_adult': {
                'audience': 'young_adult',
                'max_age_rating': 'PG-13',
                'excluded_content_tags': ['major_spoiler', 'explicit_violence'],
                'no_reveal_twist': True,
                'max_trailer_duration_seconds': 60,
                'min_trailer_duration_seconds': 25,
            },
            'dialect_region': {
                'audience': 'dialect_region',
                'max_age_rating': 'PG-13',
                'excluded_content_tags': ['major_spoiler', 'dialect_as_comedy'],
                'dialect_representation_rules': ['dialect must be used respectfully'],
                'max_trailer_duration_seconds': 75,
                'required_dialect_track': 'mariner',
            },
        }
        self.scenes_data = {
            'scene_01': make_scene('scene_01', sensitive_content=[]),
            'scene_03': make_scene('scene_03', sensitive_content=['frightening']),
            'scene_06': make_scene('scene_06', sensitive_content=['suggestive_reference']),
            'scene_09': make_scene('scene_09', sensitive_content=['major_spoiler'], is_spoiler=True),
        }

    def test_clean_scene_passes_family(self):
        """scene_01 with no sensitive content passes family policy."""
        segment = make_segment('seg_ok', 'scene_01')
        checker = RatingsChecker()
        flags = checker.check_segment(segment, self.scenes_data, self.policies['family'])
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) == 0

    def test_frightening_scene_fails_family(self):
        """scene_03 (frightening) must HARD FAIL for family audience."""
        segment = make_segment('seg_scary', 'scene_03')
        checker = RatingsChecker()
        flags = checker.check_segment(segment, self.scenes_data, self.policies['family'])
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "Frightening scene must fail family policy"
        assert any('frightening' in f['description'].lower() or 'rating' in f['type'].lower() for f in hard_flags)

    def test_suggestive_scene_fails_family(self):
        """scene_06 (suggestive) must HARD FAIL for family audience."""
        segment = make_segment('seg_suggestive', 'scene_06')
        checker = RatingsChecker()
        flags = checker.check_segment(segment, self.scenes_data, self.policies['family'])
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "Suggestive scene must fail family policy"

    def test_spoiler_scene_fails_young_adult(self):
        """scene_09 (major_spoiler) must HARD FAIL for young adult (no_reveal_twist)."""
        segment = make_segment('seg_spoiler_ya', 'scene_09')
        checker = RatingsChecker()
        flags = checker.check_segment(segment, self.scenes_data, self.policies['young_adult'])
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "Major spoiler scene must fail young adult policy"

    def test_frightening_passes_young_adult(self):
        """scene_03 (frightening) is not excluded for young_adult policy."""
        segment = make_segment('seg_scary_ya', 'scene_03')
        checker = RatingsChecker()
        flags = checker.check_segment(segment, self.scenes_data, self.policies['young_adult'])
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        # frightening is not in young_adult excluded_content_tags
        assert len(hard_flags) == 0, "Frightening is allowed for young adults"
