"""
Test configuration and shared fixtures for the Autonomous Trailer Director test suite.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# ------------------------------------------------------------------ #
# Episode fixture helpers                                              #
# ------------------------------------------------------------------ #

def make_scene(scene_id="scene_01", timecode_in="00:00:10.000", timecode_out="00:01:00.000",
               is_spoiler=False, sensitive_content=None, music_track="track_01",
               characters=None, emotional_tags=None, description="A test scene."):
    return {
        "scene_id": scene_id,
        "timecode_in": timecode_in,
        "timecode_out": timecode_out,
        "description": description,
        "characters": characters or ["Elena Voss"],
        "location": "Salt Coast",
        "emotional_tags": emotional_tags or ["warmth"],
        "music_track": music_track,
        "dialogue_lines": [],
        "is_spoiler": is_spoiler,
        "sensitive_content": sensitive_content or [],
    }


def make_episode(scenes=None, dialogue=None):
    if scenes is None:
        scenes = [
            make_scene("scene_01", "00:00:10.000", "00:01:00.000"),
            make_scene("scene_02", "00:01:00.000", "00:02:00.000"),
            make_scene("scene_03", "00:02:00.000", "00:03:00.000",
                       sensitive_content=["frightening"], emotional_tags=["tension"]),
            make_scene("scene_09", "00:08:00.000", "00:09:00.000",
                       is_spoiler=True, sensitive_content=["major_spoiler"],
                       description="Dorian reveals he is Elena's father."),
        ]
    return {
        "meta": {
            "title": "The Salt Coast",
            "episode_number": 1,
            "season": 1,
            "total_duration_seconds": 720,
            "language": "en",
            "dialect_tracks": ["mariner", "highland"],
            "genre": "family mystery drama",
            "synopsis": "A coastal mystery.",
            "content_advisory": ["mild_peril", "family_themes"],
        },
        "scenes": scenes,
        "dialogue": dialogue or [],
    }


def make_story_map(spoiler_scenes=None):
    return {
        "title": "The Salt Coast",
        "characters": [
            {"name": "Elena Voss", "role": "protagonist", "description": "...", "relationships": []},
            {"name": "Dorian Salt", "role": "supporting", "description": "...", "relationships": []},
        ],
        "relationships": [],
        "events": [],
        "emotional_arc": ["warmth", "mystery", "tension", "resolution"],
        "spoiler_map": {
            "protected_facts": ["Dorian Salt is Elena's biological father"],
            "spoiler_scenes": spoiler_scenes or ["scene_09", "scene_11"],
            "spoiler_dialogue": ["dlg_025"],
            "spoiler_definition": "A fact that materially changes how the ending is understood if known beforehand.",
        },
        "sensitive_content": {"scene_03": ["frightening"], "scene_09": ["major_spoiler"]},
        "themes": ["family", "mystery", "identity"],
    }


def make_constraint_map(extra_rules=None):
    rules = [
        {
            "rule_id": "R-001",
            "type": "spoiler",
            "description": "Exclude spoiler scenes from all trailers",
            "applies_to": ["scene_09", "scene_11"],
            "action": "EXCLUDE",
            "audiences": [],
            "expires": None,
            "active": True,
        },
        {
            "rule_id": "R-002",
            "type": "rating",
            "description": "Family audience: exclude frightening content",
            "applies_to": ["scene_03"],
            "action": "EXCLUDE",
            "audiences": ["family"],
            "expires": None,
            "active": True,
        },
        {
            "rule_id": "R-003",
            "type": "music_rights",
            "description": "track_02 not for family audience",
            "applies_to": ["track_02"],
            "action": "EXCLUDE",
            "audiences": ["family"],
            "expires": "2026-12-01",
            "active": True,
        },
        {
            "rule_id": "R-004",
            "type": "actor_rights",
            "description": "Marcus Thane (Dorian Salt) not in identity-revealing scenes",
            "applies_to": ["scene_09"],
            "action": "EXCLUDE",
            "audiences": [],
            "expires": None,
            "active": True,
        },
    ]
    if extra_rules:
        rules.extend(extra_rules)
    return {
        "rules": rules,
        "prompt_injection_attempts": [],
        "last_updated": "2026-09-28T00:00:00Z",
        "change_log": [],
    }


def make_segment(segment_id="seg_01", video="scene_01",
                 source_in="00:00:10.000", source_out="00:01:00.000",
                 music_track="track_01", subtitle_track="standard",
                 risk_flags=None, characters=None):
    return {
        "segment_id": segment_id,
        "source_in": source_in,
        "source_out": source_out,
        "video": video,
        "audio": "dialogue_and_music",
        "music_track": music_track,
        "subtitle": "Test subtitle.",
        "subtitle_track": subtitle_track,
        "reason": "Test reason.",
        "evidence": [f"scene:{video}"],
        "risk_flags": risk_flags or [],
        "human_approval_required": False,
    }


# ------------------------------------------------------------------ #
# Pytest fixtures                                                      #
# ------------------------------------------------------------------ #

@pytest.fixture
def episode_data():
    """Standard episode package dict."""
    return make_episode()


@pytest.fixture
def story_map_data():
    """Standard story map dict."""
    return make_story_map()


@pytest.fixture
def constraint_map_data():
    """Standard constraint map dict."""
    return make_constraint_map()


@pytest.fixture
def mock_llm():
    """A mock LLM client that returns empty JSON."""
    client = MagicMock()
    client.complete.return_value = MagicMock(
        content='{"result": "PASS", "warnings": []}',
        model="mock",
        usage_tokens=10,
        cost_usd=0.0,
    )
    return client


@pytest.fixture
def mock_cost_tracker():
    """A mock cost tracker."""
    from src.utils.cost_tracker import CostTracker
    return CostTracker(budget_limit=2.0)


@pytest.fixture
def mock_decision_logger(tmp_path):
    """A decision logger writing to a temp file."""
    from src.utils.logger import DecisionLogger
    return DecisionLogger(log_file=str(tmp_path / "decision_log.jsonl"))


@pytest.fixture
def data_dir():
    """Return the path to the project's data directory."""
    return str(Path(__file__).parent.parent / "data")
