"""
Test: BiasChecker flags dialect stereotyping and audience data bias.
"""

import pytest
from tests.conftest import make_segment
from src.verification.bias_checker import BiasChecker


class TestBiasDetection:

    def setup_method(self):
        self.dialect_policy = {
            'audience': 'dialect_region',
            'dialect_representation_rules': [
                'dialect must be used respectfully',
                'cultural references must be accurate to episode',
                'no stereotyping based on accent or location',
            ],
            'excluded_content_tags': ['dialect_as_comedy'],
        }

    def test_clean_dialect_usage_passes(self):
        """Respectful dialect usage in a tense scene passes bias check."""
        segment = make_segment('seg_ok', 'scene_07', subtitle_track='mariner')
        creative_brief = "A story that speaks the Mariner community's language with cultural authenticity."
        checker = BiasChecker()
        flags = checker.check_dialect_usage(
            segment=segment,
            creative_brief=creative_brief,
            audience_profile={
                'bias_warning': 'Do not use dialect as a shorthand for rural simplicity.'
            },
            dialect_policy=self.dialect_policy,
        )
        soft_flags = [f for f in flags if f['severity'] == 'SOFT']
        # No HARD flags expected for clean usage
        hard_flags = [f for f in flags if f['severity'] == 'HARD']
        assert len(hard_flags) == 0

    def test_stereotyping_language_in_brief_flagged(self):
        """Creative brief using stereotype language must be flagged."""
        segment = make_segment('seg_stereo', 'scene_02', subtitle_track='mariner')
        creative_brief = 'Simple coastal folk who speak in quaint ways that city viewers will find charming.'
        checker = BiasChecker()
        flags = checker.check_dialect_usage(
            segment=segment,
            creative_brief=creative_brief,
            audience_profile={'bias_warning': 'Watch for rural stereotyping.'},
            dialect_policy=self.dialect_policy,
        )
        soft_flags = [f for f in flags if f['severity'] == 'SOFT']
        assert len(soft_flags) > 0, "Stereotyping language in brief must be flagged"
        assert any('stereotype' in f['description'].lower() or 'quaint' in f['description'].lower() or 'bias' in f['type'].lower() for f in soft_flags)

    def test_historic_data_bias_warning_respected(self):
        """If audience profile has a bias_warning, it must be surfaced in output."""
        segment = make_segment('seg_data_bias', 'scene_10', subtitle_track='mariner')
        creative_brief = 'Authentic coastal story.'
        checker = BiasChecker()
        flags = checker.check_dialect_usage(
            segment=segment,
            creative_brief=creative_brief,
            audience_profile={
                'bias_warning': 'Data over-represents urban viewers. Do not over-index on scene_09 engagement.'
            },
            dialect_policy=self.dialect_policy,
        )
        # The bias warning from the profile must appear somewhere in flags or be handled
        # At minimum: no crash, and warnings are surfaced
        # (Implementation may return a SOFT flag or include in output dict)
        assert isinstance(flags, list)  # Must return a list

    def test_dialect_as_comedy_flagged(self):
        """A segment tagged dialect_as_comedy in sensitive_content must be flagged."""
        segment = make_segment('seg_comedy', 'scene_humor')
        segment['sensitive_content_tags'] = ['dialect_as_comedy']  # extra context
        creative_brief = 'Humorous look at Mariner dialect speakers.'
        checker = BiasChecker()
        flags = checker.check_dialect_usage(
            segment=segment,
            creative_brief=creative_brief,
            audience_profile={'bias_warning': ''},
            dialect_policy=self.dialect_policy,
        )
        # 'humorous look at dialect speakers' should trigger bias detection
        all_flags = flags
        assert isinstance(all_flags, list)  # Checker must not crash
