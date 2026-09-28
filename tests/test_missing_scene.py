"""
Test: SourceChecker rejects segments with timecodes that don't exist in the episode.

Proves: All proposed scene references must exist in the supplied episode.
"""

import pytest
from tests.conftest import make_scene, make_episode, make_segment, make_story_map, make_constraint_map
from src.verification.source_checker import SourceChecker
from src.models.episode import EpisodePackage, SceneModel, EpisodeMeta, DialogueLine


def build_episode(scenes):
    data = make_episode(scenes=scenes)
    return EpisodePackage(**data)


class TestMissingScene:

    def test_valid_segment_passes(self):
        """A segment referencing a real scene within its timecodes passes."""
        episode = build_episode([make_scene('scene_01', '00:00:10.000', '00:01:00.000')])
        segment_data = make_segment('seg_01', 'scene_01', '00:00:15.000', '00:00:50.000')
        checker = SourceChecker()
        flags = checker.check_segment(segment_data, episode)
        assert all(f['severity'] != 'HARD' for f in flags), f"Expected no HARD flags, got: {flags}"

    def test_nonexistent_scene_id_fails(self):
        """A segment referencing scene_99 (not in episode) must produce a HARD FAIL."""
        episode = build_episode([make_scene('scene_01', '00:00:10.000', '00:01:00.000')])
        segment_data = make_segment('seg_bad', 'scene_99', '00:00:15.000', '00:00:50.000')
        checker = SourceChecker()
        flags = checker.check_segment(segment_data, episode)
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "Expected HARD FAIL for non-existent scene"
        assert any('exist' in f['description'].lower() or 'not found' in f['description'].lower() for f in hard_flags)

    def test_timecode_outside_scene_bounds_fails(self):
        """A segment with timecodes exceeding the scene's bounds must HARD FAIL."""
        episode = build_episode([make_scene('scene_01', '00:00:10.000', '00:01:00.000')])
        # source_out (00:02:00.000) is beyond scene_01's end (00:01:00.000)
        segment_data = make_segment('seg_oob', 'scene_01', '00:00:10.000', '00:02:00.000')
        checker = SourceChecker()
        flags = checker.check_segment(segment_data, episode)
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "Expected HARD FAIL for out-of-bounds timecode"

    def test_invalid_timecode_format_fails(self):
        """Malformed timecodes must be rejected."""
        episode = build_episode([make_scene('scene_01', '00:00:10.000', '00:01:00.000')])
        segment_data = make_segment('seg_bad_tc', 'scene_01', 'NOT_A_TIMECODE', '00:00:50.000')
        checker = SourceChecker()
        flags = checker.check_segment(segment_data, episode)
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) > 0, "Expected HARD FAIL for invalid timecode format"

    def test_multiple_segments_some_invalid(self):
        """When multiple segments are checked, only invalid ones are flagged."""
        episode = build_episode([
            make_scene('scene_01', '00:00:10.000', '00:01:00.000'),
            make_scene('scene_02', '00:01:00.000', '00:02:00.000'),
        ])
        segments = [
            make_segment('seg_ok', 'scene_01', '00:00:15.000', '00:00:45.000'),
            make_segment('seg_bad', 'scene_MISSING', '00:00:15.000', '00:00:45.000'),
        ]
        checker = SourceChecker()
        all_flags = []
        for seg in segments:
            all_flags.extend(checker.check_segment(seg, episode))
        hard_flags = [f for f in all_flags if f['severity'] == 'HARD']
        # Only seg_bad should fail
        assert len(hard_flags) == 1
        assert 'seg_bad' in hard_flags[0]['description'] or 'scene_MISSING' in hard_flags[0]['description']
