from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum

class ValidationStatus(str, Enum):
    PASS = 'PASS'
    PASS_WITH_WARNINGS = 'PASS_WITH_WARNINGS'
    FAIL = 'FAIL'
    FAIL_UNRESOLVED = 'FAIL_UNRESOLVED'
    HUMAN_APPROVAL_REQUIRED = 'HUMAN_APPROVAL_REQUIRED'

class RiskFlag(BaseModel):
    flag_id: str
    severity: Literal['HARD', 'SOFT']
    type: str  # 'spoiler', 'rights', 'rating', 'bias', 'source', 'truth', 'accessibility'
    description: str
    resolution: Optional[str] = None

class TrailerSegment(BaseModel):
    segment_id: str
    source_in: str  # HH:MM:SS.mmm
    source_out: str
    video: str  # scene_id
    audio: str  # 'dialogue_and_music' | 'music_only' | 'dialogue_only'
    music_track: Optional[str] = None
    subtitle: str
    subtitle_track: str  # 'standard' | 'mariner' | 'highland'
    reason: str
    evidence: list[str]  # e.g. ['scene:04', 'dlg:012', 'contract:music-01']
    risk_flags: list[RiskFlag]
    human_approval_required: bool = False

class AudiencePromise(BaseModel):
    statement: str
    emotional_journey: list[str]  # ['Hook', 'Tension', 'Emotional Pull', 'CTA']
    tone: str
    what_audience_will_expect: str
    what_is_protected: list[str]  # spoilers/twists NOT revealed

class ValidationResult(BaseModel):
    status: ValidationStatus
    checks_run: list[str]
    warnings: list[str]
    failures: list[str]
    human_approvals_required: list[str]
    estimated_cost_usd: float
    fallback_plan_available: bool

class TrailerEDL(BaseModel):
    trailer_id: str
    audience: str
    duration_seconds: float
    audience_promise: AudiencePromise
    creative_brief: str
    segments: list[TrailerSegment]
    text_cards: list[dict]  # {'timecode': ..., 'text': ..., 'duration_seconds': ...}
    validation: ValidationResult
    cost_estimate_usd: float
    fallback_plan: Optional[dict] = None
    decision_notes: list[str]
    version: str = '1.0'
    generated_at: str
