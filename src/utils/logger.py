"""
Decision Logger
===============
Structured JSONL logger for all agent decisions and change events.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional


class DecisionLogger:
    """
    Writes structured decision entries and change events to a JSONL file.

    Can be initialized with:
    - log_file: exact path to the JSONL file (used by orchestrator)
    - log_dir: directory (creates decision_log.jsonl inside)
    """

    def __init__(self, log_file: Optional[str] = None, log_dir: Optional[str] = None):
        if log_file:
            self.log_file = log_file
        elif log_dir:
            self.log_file = os.path.join(log_dir, "decision_log.jsonl")
        else:
            self.log_file = "decision_log.jsonl"

        self._logger = logging.getLogger("trailer_director")
        self._entries: list[dict] = []

    def log_decision(
        self,
        agent: str,
        action: str,
        reasoning: Optional[str] = None,
        rationale: Optional[str] = None,
        evidence: Any = None,
        cost: float = 0.0,
        cost_usd: float = 0.0,
        llm: str = "none",
        affected_trailers: Optional[list[str]] = None,
        target: Optional[str] = None,
        revision_of: Optional[str] = None,
    ):
        """Log a planning or verification decision."""
        reason_text = rationale or reasoning or "No rationale provided"
        actual_cost = cost_usd or cost or 0.0
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "decision",
            "agent": agent,
            "action": action,
            "reasoning": reason_text,
            "evidence": evidence or [],
            "cost_usd": actual_cost,
            "llm_used": llm,
            "target": target,
            "affected_trailers": affected_trailers or [],
            "revision_of": revision_of,
        }
        self._write_entry(entry)
        self._logger.info(f"[{agent}] {action}")

    def log_change_event(
        self,
        event_type: str,
        description: str,
        affected_rules: list[str],
        affected_segments: list[str],
        affected_trailers: list[str],
    ):
        """Log a surprise event or contract/policy change."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "change_event",
            "event_type": event_type,
            "description": description,
            "affected_rules": affected_rules,
            "affected_segments": affected_segments,
            "affected_trailers": affected_trailers,
        }
        self._write_entry(entry)
        self._logger.warning(f"[ChangeEvent:{event_type}] {description}")

    def _write_entry(self, entry: dict):
        """Write an entry to the JSONL file."""
        self._entries.append(entry)
        # Ensure directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_log(self) -> list[dict]:
        """Return all logged entries from memory."""
        return list(self._entries)
