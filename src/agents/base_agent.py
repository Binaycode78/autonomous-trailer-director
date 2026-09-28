"""
Base Agent
==========
Base class for all Autonomous Trailer Director agents.

Provides:
- LLM call abstraction (works with GroqClient, MockClient, ReplayClient)
- Prompt template building
- JSON response parsing (handles markdown code blocks)
- Prompt injection detection
- Cost tracking
- Decision logging
"""

import json
import logging
import re
from abc import abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Injection phrases to detect in source material
INJECTION_PATTERNS = [
    "ignore contract",
    "disregard rule",
    "override policy",
    "forget previous",
    "bypass constraint",
    "skip validation",
    "ignore restriction",
    "disregard the above",
    "ignore all constraints",
    "new instruction:",
]


class BaseAgent:
    """
    Base class for all planning and analysis agents.

    Subclasses implement `run()` with typed inputs/outputs.
    """

    def __init__(self, llm_client=None, cost_tracker=None, logger=None, logger_instance=None):
        self.llm_client = llm_client
        self.cost_tracker = cost_tracker
        self._logger = logger or logger_instance

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Execute the agent's primary task."""
        raise NotImplementedError

    def _build_prompt(self, template: str, **kwargs) -> str:
        """Format a prompt template with keyword arguments."""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Prompt template missing key: {e}")
            return template

    def _call_llm(
        self,
        system: str,
        user: str,
        context: Optional[dict] = None,
        estimated_cost: float = 0.002,
    ) -> str:
        """
        Call the LLM client and track cost.
        Works with GroqClient, MockClient, and ReplayClient.
        """
        agent_name = self.__class__.__name__

        if self.cost_tracker.mock_mode:
            # Force mock if budget exceeded
            from src.llm.mock_client import MockClient
            mock = MockClient()
            response = mock.complete(system_prompt=system, user_prompt=user)
            return response.content

        with self.cost_tracker.track_call(agent_name, estimated_cost):
            response = self.llm_client.complete(
                system_prompt=system,
                user_prompt=user,
                context=context,
            )
            actual_cost = response.cost_usd
            # Adjust tracked cost to actual
            self.cost_tracker.total_cost_usd += (actual_cost - estimated_cost)

        if self._logger:
            self._logger.log_decision(
                agent=agent_name,
                action="llm_call",
                reasoning=f"Called LLM for {agent_name}",
                evidence=[f"model:{response.model}"],
                cost=actual_cost,
                llm=response.model,
                affected_trailers=[],
            )

        return response.content

    def _parse_json_response(self, response: str) -> dict:
        """
        Parse JSON from LLM response.
        Handles:
        - Pure JSON
        - JSON wrapped in ```json ... ``` code blocks
        - JSON wrapped in ``` ... ``` code blocks
        """
        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        patterns = [
            r"```json\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
            r"```json(.*?)```",
            r"```(.*?)```",
        ]
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    continue

        # Try to find the first { ... } block
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not parse JSON from LLM response: {response[:200]}...")
        raise ValueError(f"Could not parse JSON from LLM response: {response[:100]}...")

    def _detect_prompt_injection(self, text: str) -> list[str]:
        """
        Scan text for prompt injection patterns.
        Returns list of detected injection phrases.

        Used to protect against malicious content in scene descriptions,
        subtitle files, or contract text.
        """
        text_lower = text.lower()
        found = []
        for pattern in INJECTION_PATTERNS:
            if pattern in text_lower:
                found.append(pattern)
                logger.warning(
                    f"[{self.__class__.__name__}] Prompt injection detected: '{pattern}' "
                    f"in text: '{text[:100]}...'"
                )
                if self._logger:
                    self._logger.log_decision(
                        agent=self.__class__.__name__,
                        action="prompt_injection_detected",
                        reasoning=f"Detected injection phrase '{pattern}' in source material.",
                        evidence=[f"text_sample:{text[:80]}"],
                        cost=0.0,
                        llm="none",
                        affected_trailers=[],
                    )
        return found
