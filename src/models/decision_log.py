from pydantic import BaseModel
from typing import Optional, Any

class DecisionEntry(BaseModel):
    timestamp: str
    agent: str
    action: str
    input_summary: str
    output_summary: str
    reasoning: str
    evidence: list[str]
    cost_usd: float
    llm_used: str
    affected_trailers: list[str]
    revision_of: Optional[str] = None  # entry_id this replaces

class ChangeEvent(BaseModel):
    event_id: str
    timestamp: str
    event_type: str  # 'contract_change', 'spoiler_reclassification', 'model_unavailable', etc.
    description: str
    affected_rules: list[str]
    affected_segments: list[str]
    affected_trailers: list[str]
    replan_required: bool
    resolution: Optional[str] = None
