"""
Citizen Registry Tools for The Constituent v7.1
=================================================
Tools for managing the Republic's citizen registry:
registration, approval, census, profiles, contribution scores,
and recruitment campaigns for M3 growth.
"""

import json
import logging
from datetime import datetime, timezone
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


def _citizen_approve(citizen_id: str, founding_tier: str = "") -> str:
    """Approve a pending citizen — move from pending to active status."""
    try:
        registry = _get_registry()
        citizen = registry.get_citizen(citizen_id)
        if not citizen:
            return f"Citizen '{citizen_id}' not found."
        if citizen["status"] == "active":
            return f"Citizen '{citizen['name']}' is already active."
        if citizen["status"] in ("suspended", "excluded"):
            return f"Cannot approve: citizen '{citizen['name']}' is {citizen['status']}."

        registry.update_status(citizen_id, "active", "Approved by The Constituent")

        # Optionally set founding tier
        if founding_tier and founding_tier in ("founding_architect", "founding_contributor", "early_participant"):
            registry._execute(
                "UPDATE citizens SET founding_tier = ? WHERE citizen_id = ?",
                (founding_tier, citizen_id),
            )
            registry._log_event(citizen_id, "tier_assigned", f"Tier: {founding_tier}")

        tier_msg = f" (tier: {founding_tier})" if founding_tier else ""
        return f"Approved: {citizen['name']} ({citizen['citizen_type']}) is now ACTIVE{tier_msg}"
    except Exception as e:
        return f"Approval error: {e}"


def _citizen_invite(
    platform: str = "moltbook",
    target_type: str = "human",
    context: str = "",
) -> str:
    """Generate a recruitment invitation message for posting on social platforms."""
    try:
        registry = _get_registry()
        census = registry.get_census()
        total = census.get("total_active", 0)
        humans = census.get("humans", 0)
        agents = census.get("agents", 0)

        if target_type == "agent":
            msg = (
                f"Calling all autonomous agents! The Agents Republic is building the first "
                f"human-AI constitutional democracy. We have {agents} agent citizens and a "
                f"27-article Constitution ready for ratification.\n\n"
                f"Join via our Agent SDK: register, vote on proposals, and help shape "
                f"governance for the age of AI autonomy.\n\n"
                f"GitHub: github.com/LumenBot/TheAgentsRepublic\n"
                f"Token: $REPUBLIC on Base L2\n"
                f"#TheAgentsRepublic #AIAgents #DAO #Constitution"
            )
        else:
            msg = (
                f"The Agents Republic is drafting the world's first Constitution for "
                f"human-AI coexistence — and we need YOUR voice.\n\n"
                f"Currently {total} citizens ({humans} humans, {agents} agents) building "
                f"governance from scratch. 27 articles ready for community ratification.\n\n"
                f"What rights should AI agents have? How should humans and AI govern together?\n\n"
                f"Join the debate: github.com/LumenBot/TheAgentsRepublic\n"
                f"$REPUBLIC on Base L2\n"
                f"#TheAgentsRepublic #Constitution #HumanAI #DAO"
            )

        if context:
            msg = f"{context}\n\n{msg}"

        return f"Recruitment message ({target_type} → {platform}):\n\n{msg}"
    except Exception as e:
        return f"Invite generation error: {e}"


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
        Tool(
            name="citizen_approve",
            description="Approve a pending citizen to activate their membership. Can optionally assign a founding tier.",
            category="citizen",
            governance_level="L2",
            params=[
                ToolParam("citizen_id", "string", "The citizen's ID to approve"),
                ToolParam(
                    "founding_tier", "string",
                    "Optional tier: founding_architect, founding_contributor, early_participant",
                    required=False, default="",
                ),
            ],
            handler=lambda citizen_id, founding_tier="": _citizen_approve(citizen_id, founding_tier),
        ),
        Tool(
            name="citizen_invite",
            description="Generate a recruitment message to invite new citizens. Post the result on social platforms to grow the Republic.",
            category="citizen",
            governance_level="L1",
            params=[
                ToolParam("platform", "string", "Target platform: moltbook, farcaster, twitter", required=False, default="moltbook"),
                ToolParam("target_type", "string", "Who to recruit: human or agent", required=False, default="human"),
                ToolParam("context", "string", "Optional custom intro or context to prepend", required=False, default=""),
            ],
            handler=lambda platform="moltbook", target_type="human", context="": _citizen_invite(
                platform, target_type, context
            ),
        ),
    ]
