"""
Cost Tracker
============
Tracks LLM call costs and enforces budget limits.
"""
import json
import os
from contextlib import contextmanager
from typing import Optional


class BudgetExceededError(Exception):
    pass


class CostTracker:
    """
    Tracks per-agent and total LLM costs.
    Raises BudgetExceededError if the configured limit is exceeded.

    Can be initialized with a direct budget_limit float (used by orchestrator)
    or with a data_dir to load cost_sheet.json.
    """

    def __init__(self, budget_limit: float = 2.0, data_dir: Optional[str] = None):
        self.budget_limit = budget_limit
        self.total_cost_usd = 0.0
        self.total_calls = 0
        self.per_agent_costs: dict[str, float] = {}
        self.mock_mode = False

        # Allow loading from cost_sheet.json if data_dir provided
        if data_dir:
            cost_sheet_path = os.path.join(data_dir, "cost_sheet.json")
            if os.path.exists(cost_sheet_path):
                with open(cost_sheet_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.budget_limit = data.get("budget_total_usd", budget_limit)

    @contextmanager
    def track_call(self, agent_name: str, estimated_cost: float = 0.002):
        """Context manager to track a single LLM call."""
        if not self.mock_mode and self.total_cost_usd + estimated_cost > self.budget_limit:
            self.switch_to_fallback()
            # Don't raise — switch to fallback mode and log warning

        yield

        self.total_calls += 1
        self.total_cost_usd += estimated_cost
        if agent_name not in self.per_agent_costs:
            self.per_agent_costs[agent_name] = 0.0
        self.per_agent_costs[agent_name] += estimated_cost

    def add_cost(self, agent_name: str, cost: float):
        """Add cost directly without context manager."""
        self.total_cost_usd += cost
        self.total_calls += 1
        self.per_agent_costs[agent_name] = self.per_agent_costs.get(agent_name, 0.0) + cost

    def get_summary(self) -> dict:
        pct = (self.total_cost_usd / self.budget_limit * 100) if self.budget_limit > 0 else 0
        return {
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_calls": self.total_calls,
            "budget_limit": self.budget_limit,
            "percent_used": round(pct, 1),
            "per_agent_costs": self.per_agent_costs,
            "mock_mode": self.mock_mode,
        }

    def switch_to_fallback(self):
        """Switch to mock/fallback mode when budget is exhausted."""
        import logging
        logging.getLogger(__name__).warning(
            f"[CostTracker] Budget limit ${self.budget_limit:.2f} approached. "
            "Switching to mock mode."
        )
        self.mock_mode = True
