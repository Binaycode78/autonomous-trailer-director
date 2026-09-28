from pydantic import BaseModel
from typing import Optional, Literal

class ConstraintRule(BaseModel):
    rule_id: str
    type: Literal['spoiler', 'music_rights', 'actor_rights', 'rating', 'territory', 'duration', 'dialect_respect', 'budget']
    description: str
    applies_to: list[str]  # scene_ids, actor names, music track ids
    action: Literal['EXCLUDE', 'WARN', 'REQUIRE_APPROVAL', 'LIMIT']
    audiences: list[str]  # which audiences this applies to, empty = all
    expires: Optional[str] = None  # ISO date if time-limited
    active: bool = True  # can be set False if contract expires

class ConstraintMap(BaseModel):
    rules: list[ConstraintRule]
    prompt_injection_attempts: list[dict]  # detected injection attempts in source data
    last_updated: str
    change_log: list[dict]  # history of changes for replanning
