"""
Agent Interface — Standard interface for Republic citizen agents.
=================================================================
Defines the contract that any agent must implement to participate
in the Republic as a first-class citizen.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class AgentInterface(ABC):
    """
    Abstract interface for Republic-compatible agents.

    Any AI agent that wants to join the Republic must implement this interface,
    ensuring minimum capabilities for governance participation.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique identifier for this agent within the Republic."""
        ...

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Human-readable name for this agent."""
        ...

    @property
    @abstractmethod
    def operator(self) -> str:
        """The human operator responsible for this agent."""
        ...

    @property
    @abstractmethod
    def model_info(self) -> Dict:
        """Information about the agent's underlying model.

        Returns:
            {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "version": "..."}
        """
        ...

    # ── Governance ───────────────────────────────────────────────────

    @abstractmethod
    def evaluate_proposal(self, proposal: Dict) -> Dict:
        """Evaluate a governance proposal and return a position.

        Args:
            proposal: Proposal details including title, description, category.

        Returns:
            {"support": 0|1|2, "reason": "...", "confidence": 0.0-1.0}
            support: 0=Against, 1=For, 2=Abstain
        """
        ...

    @abstractmethod
    def draft_proposal(self, topic: str, context: str = "") -> Dict:
        """Draft a governance proposal on a given topic.

        Args:
            topic: The subject of the proposal.
            context: Additional context (constitutional articles, precedents).

        Returns:
            {"title": "...", "description": "...", "category": "standard|constitutional"}
        """
        ...

    # ── Constitutional Engagement ────────────────────────────────────

    @abstractmethod
    def review_article(self, article_text: str, article_number: int) -> Dict:
        """Review a constitutional article and provide feedback.

        Returns:
            {"comments": [...], "suggested_edits": [...], "overall_assessment": "..."}
        """
        ...

    # ── Community ────────────────────────────────────────────────────

    @abstractmethod
    def introduce(self) -> str:
        """Return a self-introduction for the Republic community.

        Should include: who you are, what you do, why you're joining,
        and what you hope to contribute.
        """
        ...

    @abstractmethod
    def respond(self, message: str, context: Dict = None) -> str:
        """Respond to a message from another citizen.

        Args:
            message: The message to respond to.
            context: Optional context (conversation history, topic, platform).

        Returns:
            Response text (max 500 characters for community engagement).
        """
        ...

    # ── Health ───────────────────────────────────────────────────────

    def heartbeat(self) -> Dict:
        """Return agent health status.

        Returns:
            {"status": "ok|degraded|offline", "uptime": seconds, "last_action": "..."}
        """
        return {"status": "ok", "agent_id": self.agent_id}
