"""
Citizen Registry Tools for The Constituent v7.0
=================================================
Tools for managing the Republic's citizen registry:
registration, census, profiles, contribution scores.
"""

import json
import logging
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Citizen")


def _get_registry():
    """Lazy import to avoid startup failures."""
    from ..integrations.citizen_registry import CitizenRegistry
    return CitizenRegistry()


def _citizen_census() -> str:
    """Get Republic census — total citizens, breakdown by type."""
    try:
        registry = _get_registry()
        census = registry.get_census()
        return (
            f"Republic Census\n"
            f"├ Total active: {census['total_active']}\n"
            f"├ Humans: {census['humans']} ({census['m3_human_progress']} M3 target)\n"
            f"├ Agents: {census['agents']} ({census['m3_agent_progress']} M3 target)\n"
            f"├ Founding Architects: {census['founding_architects']}\n"
            f"├ Founding Contributors: {census['founding_contributors']}\n"
            f"└ Avg contribution score: {census['avg_contribution_score']}"
        )
    except Exception as e:
        return f"Census error: {e}"


def _citizen_list(citizen_type: str = "", limit: int = 20) -> str:
    """List registered citizens."""
    try:
        registry = _get_registry()
        citizens = registry.list_citizens(
            citizen_type=citizen_type or None,
            limit=limit,
        )
        if not citizens:
            return "No citizens found."

        lines = [f"Citizens ({len(citizens)}):"]
        for c in citizens:
            tier = f" [{c['founding_tier']}]" if c['founding_tier'] != 'none' else ""
            lines.append(
                f"  {c['citizen_type'].upper()} {c['name']}{tier} "
                f"— score:{c['contribution_score']} status:{c['status']}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"List error: {e}"


def _citizen_profile(citizen_id: str) -> str:
    """Get detailed profile for a citizen."""
    try:
        registry = _get_registry()
        c = registry.get_citizen(citizen_id)
        if not c:
            return f"Citizen '{citizen_id}' not found."

        platforms = ", ".join(f"{k}:{v}" for k, v in c.get("platform_ids", {}).items())
        return (
            f"Citizen Profile: {c['name']}\n"
            f"├ ID: {c['citizen_id']}\n"
            f"├ Type: {c['citizen_type']}\n"
            f"├ Status: {c['status']}\n"
            f"├ Wallet: {c.get('wallet_address', 'none')}\n"
            f"├ Operator: {c.get('operator', 'N/A')}\n"
            f"├ Model: {c.get('model', 'N/A')}\n"
            f"├ Contribution: {c['contribution_score']}/100\n"
            f"├ Founding tier: {c['founding_tier']}\n"
            f"├ Warnings: {c.get('warnings', 0)}\n"
            f"├ Joined: {c['joined_at']}\n"
            f"├ Last active: {c['last_active']}\n"
            f"└ Platforms: {platforms or 'none'}"
        )
    except Exception as e:
        return f"Profile error: {e}"


def _citizen_register(
    name: str,
    citizen_type: str,
    operator: str = "",
    model: str = "",
    wallet_address: str = "",
) -> str:
    """Register a new citizen in the Republic."""
    if citizen_type not in ("human", "agent"):
        return "citizen_type must be 'human' or 'agent'"

    try:
        from ..integrations.citizen_registry import CitizenRegistry, Citizen
        import hashlib
        from datetime import datetime, timezone

        registry = CitizenRegistry()
        citizen_id = f"{citizen_type}-{hashlib.sha256(name.encode()).hexdigest()[:12]}"

        citizen = Citizen(
            citizen_id=citizen_id,
            name=name,
            citizen_type=citizen_type,
            status="pending",
            wallet_address=wallet_address,
            operator=operator,
            model=model,
            joined_at=datetime.now(timezone.utc).isoformat(),
            last_active=datetime.now(timezone.utc).isoformat(),
        )

        result = registry.register_citizen(citizen)
        return f"Registered: {name} ({citizen_type}) — ID: {citizen_id} — Status: pending"
    except Exception as e:
        return f"Registration error: {e}"


def _citizen_update_score(citizen_id: str, score: float) -> str:
    """Update a citizen's contribution score."""
    try:
        registry = _get_registry()
        result = registry.update_contribution_score(citizen_id, score)
        return f"Score updated: {citizen_id} → {score}/100"
    except Exception as e:
        return f"Score update error: {e}"


def get_tools() -> List[Tool]:
    """Return citizen registry tools for the engine."""
    return [
        Tool(
            name="citizen_census",
            description="Get Republic census: total citizens, humans vs agents, M3 progress.",
            category="citizen",
            governance_level="L1",
            params=[],
            handler=lambda: _citizen_census(),
        ),
        Tool(
            name="citizen_list",
            description="List registered Republic citizens. Optionally filter by type (human/agent).",
            category="citizen",
            governance_level="L1",
            params=[
                ToolParam("citizen_type", "string", "Filter: human or agent", required=False, default=""),
                ToolParam("limit", "integer", "Max results", required=False, default=20),
            ],
            handler=lambda citizen_type="", limit=20: _citizen_list(citizen_type, int(limit)),
        ),
        Tool(
            name="citizen_profile",
            description="Get detailed profile for a specific citizen by ID.",
            category="citizen",
            governance_level="L1",
            params=[
                ToolParam("citizen_id", "string", "The citizen's ID"),
            ],
            handler=lambda citizen_id: _citizen_profile(citizen_id),
        ),
        Tool(
            name="citizen_register",
            description="Register a new citizen in the Republic. New citizens start as 'pending'.",
            category="citizen",
            governance_level="L1",
            params=[
                ToolParam("name", "string", "Citizen's display name"),
                ToolParam("citizen_type", "string", "Type: human or agent"),
                ToolParam("operator", "string", "For agents: human operator name", required=False, default=""),
                ToolParam("model", "string", "For agents: AI model identifier", required=False, default=""),
                ToolParam("wallet_address", "string", "Base L2 wallet address", required=False, default=""),
            ],
            handler=lambda name, citizen_type, operator="", model="", wallet_address="": _citizen_register(
                name, citizen_type, operator, model, wallet_address
            ),
        ),
        Tool(
            name="citizen_update_score",
            description="Update a citizen's contribution score (0-100). Requires L1 authority.",
            category="citizen",
            governance_level="L1",
            params=[
                ToolParam("citizen_id", "string", "The citizen's ID"),
                ToolParam("score", "integer", "New contribution score (0-100)"),
            ],
            handler=lambda citizen_id, score: _citizen_update_score(citizen_id, float(score)),
        ),
    ]
