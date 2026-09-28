"""
Episode Package & Data Ingestion Loader
========================================
Loads episode package data, rating policies, contracts, audience profiles, and cost sheets.
Supports both single file (e.g. policies.json) and directory structures (e.g. policies/*.json).
"""
import os
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EpisodePackage:
    def __init__(self, meta: dict, scenes: list, dialogue: list):
        self.meta = meta
        self.scenes = scenes
        self.dialogue = dialogue


def load_episode_package(data_dir: str) -> EpisodePackage:
    """Load episode meta, scenes, dialogue from data_dir/episode/ or data_dir/"""
    ep_dir = os.path.join(data_dir, "episode") if os.path.exists(os.path.join(data_dir, "episode")) else data_dir
    
    meta = _load_json(os.path.join(ep_dir, "episode_meta.json"), {})
    scenes = _load_json(os.path.join(ep_dir, "scenes.json"), [])
    dialogue = _load_json(os.path.join(ep_dir, "dialogue.json"), [])
    
    return EpisodePackage(meta, scenes, dialogue)


def load_policies(data_dir: str) -> dict[str, dict]:
    """Load rating policies keyed by audience name"""
    path = os.path.join(data_dir, "policies.json")
    if os.path.exists(path):
        return _load_json(path, {})
    
    policies_dir = os.path.join(data_dir, "policies")
    if os.path.exists(policies_dir):
        policies = {}
        for fname in os.listdir(policies_dir):
            if fname.endswith(".json"):
                key = fname.replace("rating_", "").replace(".json", "")
                if key == "regional":
                    key = "dialect_region"
                policies[key] = _load_json(os.path.join(policies_dir, fname), {})
        return policies
    return {}


def load_contracts(data_dir: str) -> dict:
    """Load actor, music, territory contracts"""
    path = os.path.join(data_dir, "contracts.json")
    if os.path.exists(path):
        return _load_json(path, {})
    
    contracts_dir = os.path.join(data_dir, "contracts")
    if os.path.exists(contracts_dir):
        actors = _load_json(os.path.join(contracts_dir, "actor_contracts.json"), [])
        music = _load_json(os.path.join(contracts_dir, "music_contracts.json"), [])
        territories = _load_json(os.path.join(contracts_dir, "territory_restrictions.json"), [])
        return {
            "actor_contracts": actors,
            "music_contracts": music,
            "territory_restrictions": territories
        }
    return {}


def load_audience_profiles(data_dir: str) -> dict[str, dict]:
    """Load audience profiles keyed by audience_id"""
    path = os.path.join(data_dir, "audience_profiles.json")
    if os.path.exists(path):
        return _load_json(path, {})
    
    aud_dir = os.path.join(data_dir, "audiences")
    if os.path.exists(aud_dir):
        profiles = {}
        for fname in os.listdir(aud_dir):
            if fname.endswith(".json"):
                key = fname.replace("_profile.json", "")
                profiles[key] = _load_json(os.path.join(aud_dir, fname), {})
        return profiles
    return {}


def load_cost_sheet(data_dir: str) -> dict:
    return _load_json(os.path.join(data_dir, "cost_sheet.json"), {})


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        logger.warning(f"File not found: {path}, returning default")
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        return default
