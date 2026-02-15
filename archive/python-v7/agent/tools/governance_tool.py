"""
Governance Tools for The Constituent v7.1
==========================================
On-chain governance tools: proposal management, voting, governance status.
Integrates with RepublicGovernance.sol on Base L2.
Supports local signaling mode when on-chain is unavailable.
"""

import logging
from pathlib import Path
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Governance")


def _get_governance_manager():
    """Lazy import to avoid startup failures if web3 is not installed."""
    from ..integrations.governance import GovernanceManager
    return GovernanceManager()


def _governance_status() -> str:
    """Get comprehensive governance status."""
    try:
        gov = _get_governance_manager()
        status = gov.get_governance_status()

        lines = [
            f"Governance Status",
            f"├ Connected: {status.get('connected', False)}",
            f"├ Governor: {status.get('governor_address', 'not configured')}",
            f"├ Token: {status.get('token_address', '')}",
            f"├ Proposals tracked: {status.get('proposals_tracked', 0)}",
        ]

        if status.get("connected"):
            lines.extend([
                f"├ Voting delay: {status.get('voting_delay', '?')} blocks",
                f"├ Voting period: {status.get('voting_period', '?')} blocks",
                f"├ Proposal threshold: {status.get('proposal_threshold', '?')}",
                f"├ Current block: {status.get('current_block', '?')}",
                f"└ Quorum: {status.get('quorum', '?')}",
            ])

        active = status.get("active_proposals", [])
        if active:
            lines.append(f"\nActive Proposals ({len(active)}):")
            for p in active:
                lines.append(f"  • [{p['state']}] {p['title']}")

        return "\n".join(lines)
    except Exception as e:
        return f"Governance status error: {e}"


def _list_proposals(state: str = "") -> str:
    """List all governance proposals."""
    try:
        gov = _get_governance_manager()
        proposals = gov.list_proposals(state_filter=state or None)

        if not proposals:
            return "No proposals found." + (f" (filter: {state})" if state else "")

        lines = [f"Proposals ({len(proposals)}):"]
        for p in proposals[:20]:
            votes = f"For:{p['for_votes']} Against:{p['against_votes']}"
            lines.append(
                f"  [{p['state']}] {p['title']} ({p['category']}) — {votes}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"List proposals error: {e}"


def _create_proposal(title: str, description: str, category: str = "standard") -> str:
    """Create a new governance proposal."""
    try:
        gov = _get_governance_manager()
        result = gov.create_proposal(title, description, category=category)
        status = result.get("status", "unknown")
        pid = result.get("proposal_id", "?")
        return f"Proposal {status}: '{title}' (id={pid}, category={category})"
    except Exception as e:
        return f"Create proposal error: {e}"


def _vote_proposal(proposal_id: str, support: str, reason: str = "") -> str:
    """Cast a vote on a proposal. support: for/against/abstain"""
    support_map = {"for": 1, "against": 0, "abstain": 2}
    support_int = support_map.get(support.lower())
    if support_int is None:
        return f"Invalid support value '{support}'. Use: for, against, abstain"

    try:
        gov = _get_governance_manager()
        result = gov.cast_vote(proposal_id, support_int, reason)
        return f"Vote {result.get('status', 'unknown')}: {support} on {proposal_id}" + (
            f" — {reason}" if reason else ""
        )
    except Exception as e:
        return f"Vote error: {e}"


def _get_voting_power(address: str) -> str:
    """Check voting power for an address."""
    try:
        gov = _get_governance_manager()
        result = gov.get_voting_power(address)
        from web3 import Web3
        balance = Web3.from_wei(result.get("balance", 0), "ether")
        power = Web3.from_wei(result.get("voting_power", 0), "ether")
        delegate = result.get("delegate", "none")
        return (
            f"Address: {address}\n"
            f"Balance: {balance} $REPUBLIC\n"
            f"Voting power: {power}\n"
            f"Delegate: {delegate}"
        )
    except Exception as e:
        return f"Voting power query error: {e}"


def _activate_proposal(proposal_id: str) -> str:
    """Activate a Draft proposal for signaling votes (local mode)."""
    try:
        gov = _get_governance_manager()
        prop = gov._proposals_cache.get(proposal_id)
        if not prop:
            return f"Proposal '{proposal_id}' not found."
        if prop.state == "Active":
            return f"Proposal '{prop.title}' is already Active."
        if prop.state not in ("Draft", "Pending"):
            return f"Cannot activate: proposal is in state '{prop.state}'."

        prop.state = "Active"
        gov._save_proposals()
        logger.info(f"Proposal activated for signaling: {prop.title} ({proposal_id})")
        return (
            f"Proposal ACTIVATED for community voting:\n"
            f"├ ID: {proposal_id}\n"
            f"├ Title: {prop.title}\n"
            f"├ Category: {prop.category}\n"
            f"└ State: Active (signaling mode — votes tracked locally)"
        )
    except Exception as e:
        return f"Activation error: {e}"


def get_tools() -> List[Tool]:
    """Return governance tools for the engine."""
    return [
        Tool(
            name="governance_status",
            description="Show on-chain governance status: proposals, quorum, voting parameters.",
            category="governance",
            governance_level="L1",
            params=[],
            handler=lambda: _governance_status(),
        ),
        Tool(
            name="governance_list_proposals",
            description="List governance proposals. Optionally filter by state (Active, Pending, Defeated, etc.).",
            category="governance",
            governance_level="L1",
            params=[
                ToolParam("state", "string", "Filter by proposal state", required=False, default=""),
            ],
            handler=lambda state="": _list_proposals(state),
        ),
        Tool(
            name="governance_propose",
            description="Create a new governance proposal for the Republic. Requires L2 approval for submission.",
            category="governance",
            governance_level="L2",
            params=[
                ToolParam("title", "string", "Proposal title (concise)"),
                ToolParam("description", "string", "Full proposal description with rationale"),
                ToolParam("category", "string", "Category: standard, constitutional, emergency", required=False, default="standard"),
            ],
            handler=lambda title, description, category="standard": _create_proposal(title, description, category),
        ),
        Tool(
            name="governance_vote",
            description="Cast a vote on a governance proposal. Support: for, against, abstain.",
            category="governance",
            governance_level="L1",
            params=[
                ToolParam("proposal_id", "string", "The proposal ID to vote on"),
                ToolParam("support", "string", "Vote: for, against, or abstain"),
                ToolParam("reason", "string", "Reason for your vote", required=False, default=""),
            ],
            handler=lambda proposal_id, support, reason="": _vote_proposal(proposal_id, support, reason),
        ),
        Tool(
            name="governance_voting_power",
            description="Check the voting power of a wallet address.",
            category="governance",
            governance_level="L1",
            params=[
                ToolParam("address", "string", "The wallet address to check"),
            ],
            handler=lambda address: _get_voting_power(address),
        ),
        Tool(
            name="governance_activate",
            description="Activate a Draft proposal for community signaling votes. Works in local mode without on-chain.",
            category="governance",
            governance_level="L1",
            params=[
                ToolParam("proposal_id", "string", "The proposal ID to activate"),
            ],
            handler=lambda proposal_id: _activate_proposal(proposal_id),
        ),
    ]
