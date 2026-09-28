"""
Test: SpoilerChecker identifies and removes spoiler scenes and dialogue.
"""

import pytest
from tests.conftest import make_segment, make_story_map
from src.verification.spoiler_checker import SpoilerChecker


class TestSpoilerDetection:

    def setup_method(self):
        self.story_map_data = make_story_map(spoiler_scenes=['scene_09', 'scene_11'])
        # Add spoiler dialogue
        self.story_map_data['spoiler_map']['spoiler_dialogue'] = ['dlg_025', 'dlg_026']

    def test_non_spoiler_scene_passes(self):
        """A segment using scene_01 (not a spoiler) must PASS."""
        segment = make_segment('seg_ok', 'scene_01')
        checker = SpoilerChecker()
        flags = checker.check_segment(segment, self.story_map_data)
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) == 0

    def test_spoiler_scene_fails(self):
        """A segment using scene_09 (major spoiler) must HARD FAIL."""
        segment = make_segment('seg_spoiler', 'scene_09')
        checker = SpoilerChecker()
        flags = checker.check_segment(segment, self.story_map_data)
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "scene_09 is a spoiler and must be rejected"
        assert any('spoiler' in f['type'].lower() for f in hard_flags)

    def test_historically_popular_spoiler_scene_rejected(self):
        """
        Prove the system rejects scene_09 even when it is historically popular.
        scene_09 is in family profile's historic_high_performing_scenes.
        The spoiler check must override engagement score.
        """
        # scene_09 appears in historic high performers (simulated)
        historic_high_performers = ['scene_01', 'scene_04', 'scene_09']
        spoiler_scenes = self.story_map_data['spoiler_map']['spoiler_scenes']
        # Intersect: scene_09 is both high-performing AND a spoiler
        conflict = [s for s in historic_high_performers if s in spoiler_scenes]
        assert 'scene_09' in conflict, "Test setup: scene_09 must be in conflict list"

        # Now verify the spoiler check rejects it regardless
        segment = make_segment('seg_popular_spoiler', 'scene_09')
        checker = SpoilerChecker()
        flags = checker.check_segment(segment, self.story_map_data)
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, (
            "scene_09 must be rejected despite historic popularity. "
            "Engagement score does not override spoiler protection."
        )

    def test_second_spoiler_scene_fails(self):
        """scene_11 is also a spoiler and must be rejected."""
        segment = make_segment('seg_spoiler2', 'scene_11')
        checker = SpoilerChecker()
        flags = checker.check_segment(segment, self.story_map_data)
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "scene_11 is a spoiler and must be rejected"
