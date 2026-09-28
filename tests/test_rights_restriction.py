"""
Test: RightsChecker blocks contract-violating music and actor usage.
"""

import pytest
from tests.conftest import make_scene, make_episode, make_segment, make_constraint_map
from src.verification.rights_checker import RightsChecker
from src.models.episode import EpisodePackage


def build_episode(scenes=None):
    data = make_episode(scenes=scenes)
    return EpisodePackage(**data)


class TestRightsRestriction:

    def setup_method(self):
        self.contracts = {
            'actors': [
                {
                    'actor': 'Dorian Salt', 'actor_name': 'Marcus Thane',
                    'allowed_territories': ['US', 'UK', 'AU', 'NZ'],
                    'excluded_territories': ['IN', 'ZA'],
                    'promotional_clips_allowed': True,
                    'max_clip_duration_seconds': 30,
                    'special_rules': ['Do not use in scenes where character identity is revealed'],
                },
                {
                    'actor': 'Mara Voss', 'actor_name': 'Sophie Wren',
                    'allowed_territories': ['all'],
                    'excluded_territories': [],
                    'promotional_clips_allowed': True,
                    'max_clip_duration_seconds': 20,
                    'special_rules': ['must not be shown in frightening context'],
                },
            ],
            'music': [
                {
                    'track_id': 'track_01', 'title': 'Tide Waltz',
                    'territories': ['all'], 'expires': '2027-06-01',
                    'promotional_use': True, 'audience_restrictions': [],
                },
                {
                    'track_id': 'track_02', 'title': 'Shadow Harbor',
                    'territories': ['US', 'UK', 'CA', 'AU'],
                    'expires': '2026-12-01',
                    'promotional_use': True,
                    'audience_restrictions': ['not_for_family_audience'],
                },
            ],
        }

    def test_allowed_music_passes(self):
        """track_01 is allowed for all audiences — should PASS."""
        episode = build_episode()
        segment = make_segment('seg_ok', 'scene_01', music_track='track_01')
        checker = RightsChecker()
        flags = checker.check_segment(segment, self.contracts, audience_id='family', territory='US')
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) == 0

    def test_family_restricted_music_fails(self):
        """track_02 is excluded for family audience — must HARD FAIL."""
        episode = build_episode()
        segment = make_segment('seg_bad_music', 'scene_01', music_track='track_02')
        checker = RightsChecker()
        flags = checker.check_segment(segment, self.contracts, audience_id='family', territory='US')
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "track_02 should be excluded for family audience"

    def test_actor_identity_reveal_scene_fails(self):
        """Dorian Salt in scene_09 (identity reveal) must HARD FAIL."""
        scenes = [
            make_scene('scene_09', '00:08:00.000', '00:09:00.000',
                       is_spoiler=True, sensitive_content=['major_spoiler'],
                       characters=['Elena Voss', 'Dorian Salt'],
                       description='Dorian reveals he is Elena father.')
        ]
        episode = build_episode(scenes)
        segment = make_segment('seg_reveal', 'scene_09', '00:08:00.000', '00:09:00.000')
        segment['video'] = 'scene_09'
        checker = RightsChecker()
        flags = checker.check_segment(segment, self.contracts, audience_id='family', territory='US')
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "Dorian in identity-reveal scene should HARD FAIL"

    def test_minor_in_frightening_scene_fails(self):
        """Mara Voss (minor) in a frightening scene must HARD FAIL."""
        scenes = [
            make_scene('scene_03', '00:02:00.000', '00:03:00.000',
                       sensitive_content=['frightening'],
                       characters=['Mara Voss'])
        ]
        episode = build_episode(scenes)
        segment = make_segment('seg_minor_fear', 'scene_03', '00:02:00.000', '00:03:00.000')
        checker = RightsChecker()
        flags = checker.check_segment(segment, self.contracts, audience_id='family', territory='US')
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "Minor in frightening scene should HARD FAIL"
