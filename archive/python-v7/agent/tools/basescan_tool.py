"""
BaseScan Tools for The Constituent v6.2
========================================
On-chain $REPUBLIC token tracking via BaseScan API.
"""

import json
import logging
from typing import List

from ..tool_registry import Tool, ToolParam
from ..integrations.basescan import BaseScanTracker

logger = logging.getLogger("TheConstituent.Tools.BaseScan")

_tracker: BaseScanTracker = None


def _get_tracker() -> BaseScanTracker:
    global _tracker
    if _tracker is None:
        _tracker = BaseScanTracker()
    return _tracker


def _basescan_token_info() -> str:
    """Get $REPUBLIC token info and on-chain status."""
    tracker = _get_tracker()
    status = tracker.get_full_status()
    lines = [
        f"$REPUBLIC Token Status",
        f"├ Address: {status.get('address', '?')}",
        f"├ Chain: {status.get('chain', '?')}",
    ]
    if "total_supply" in status:
        lines.append(f"├ Supply: {status['total_supply']:,.0f}")
    lines.append(f"├ Holders: {status.get('holders', '?')}")
    lines.append(f"├ Recent transfers: {status.get('recent_transfers', '?')}")
    if "agent_balance" in status:
        lines.append(f"├ Agent balance: {status['agent_balance']:,.0f} $REPUBLIC")
    if "agent_eth" in status:
        lines.append(f"├ Agent ETH: {status['agent_eth']:.6f} ETH")
    lines.append(f"└ Explorer: {status.get('explorer', '?')}")
    return "\n".join(lines)


def _basescan_transfers(limit: int = 10) -> str:
    """Get recent $REPUBLIC token transfers."""
    tracker = _get_tracker()
    result = tracker.get_recent_transfers(limit=int(limit))
    if "error" in result:
        return f"Error: {result['error']}"
    transfers = result.get("transfers", [])
    if not transfers:
        return "No recent transfers found"
    lines = [f"Recent {len(transfers)} $REPUBLIC transfers:"]
    for tx in transfers:
        val = tx.get("value", 0)
        fr = tx.get("from", "?")[:10]
        to = tx.get("to", "?")[:10]
        lines.append(f"  {fr}...→{to}... {val:,.0f} $REPUBLIC")
    return "\n".join(lines)


def _basescan_balance(address: str) -> str:
    """Check $REPUBLIC balance for an address."""
    tracker = _get_tracker()
    result = tracker.get_token_balance(address)
    if "error" in result:
        return f"Error: {result['error']}"
    return f"Balance for {address[:16]}...: {result['balance']:,.0f} $REPUBLIC"


def get_tools() -> List[Tool]:
    """Register BaseScan token tracking tools."""
    return [
        Tool(
            name="basescan_token_info",
            description="Get $REPUBLIC token on-chain status: supply, holders, recent activity, agent balance.",
            category="token",
            params=[],
            handler=_basescan_token_info,
        ),
        Tool(
            name="basescan_transfers",
            description="Get recent $REPUBLIC token transfers on Base L2.",
            category="token",
            params=[
                ToolParam("limit", "integer", "Number of transfers (default 10)", required=False, default=10),
            ],
            handler=lambda limit=10: _basescan_transfers(int(limit)),
        ),
        Tool(
            name="basescan_balance",
            description="Check $REPUBLIC token balance for any Base address.",
            category="token",
            params=[
                ToolParam("address", "string", "Base L2 wallet address to check"),
            ],
            handler=_basescan_balance,
        ),
    ]
