"""
Daily Briefing Tool for The Constituent v6.2
==============================================
Generates comprehensive daily status reports for the operator.
Aggregates: constitution progress, metrics, token status, CLAWS memory, ecosystem.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Briefing")

DATA_DIR = Path("data")


def _get_constitution_progress() -> dict:
    """Read constitution progress from data file."""
    fp = DATA_DIR / "constitution_progress.json"
    if fp.exists():
        try:
            data = json.loads(fp.read_text())
            written = data.get("articles_written", [])
            return {"written": len(written), "total": 26, "articles": written}
        except Exception:
            pass
    return {"written": 0, "total": 26, "articles": []}


def _get_daily_metrics() -> dict:
    """Read today's metrics from data file."""
    fp = DATA_DIR / "daily_metrics.json"
    if fp.exists():
        try:
            data = json.loads(fp.read_text())
            # Get today's entry
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if isinstance(data, dict):
                return data.get(today, data)
            if isinstance(data, list) and data:
                return data[-1]
        except Exception:
            pass
    return {}


def _get_claws_stats() -> dict:
    """Get CLAWS memory statistics."""
    try:
        from ..integrations.claws_memory import ClawsMemory
        claws = ClawsMemory()
        return claws.stats()
    except Exception:
        return {"error": "CLAWS not available"}


def _get_token_status() -> dict:
    """Get $REPUBLIC token on-chain status."""
    try:
        from ..integrations.basescan import BaseScanTracker
        tracker = BaseScanTracker()
        return tracker.get_full_status()
    except Exception:
        return {"error": "BaseScan not available"}


def _get_pending_tweets() -> int:
    """Count pending tweets."""
    fp = DATA_DIR / "pending_tweets.json"
    if fp.exists():
        try:
            data = json.loads(fp.read_text())
            tweets = data.get("tweets", [])
            return len([t for t in tweets if t.get("status") in ("pending", "draft", "approved")])
        except Exception:
            pass
    return 0


def _daily_briefing() -> str:
    """Generate the full daily briefing."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"📋 DAILY BRIEFING — {now}", "=" * 40, ""]

    # 1. Constitution
    const = _get_constitution_progress()
    pct = (const["written"] / const["total"] * 100) if const["total"] else 0
    lines.append(f"📜 CONSTITUTION: {const['written']}/{const['total']} articles ({pct:.0f}%)")
    if const["written"] < const["total"]:
        lines.append(f"   Next: article {const['written'] + 1}")
    else:
        lines.append("   ✅ COMPLETE")
    lines.append("")

    # 2. Token
    token = _get_token_status()
    if "error" not in token:
        lines.append("💎 $REPUBLIC TOKEN:")
        if "total_supply" in token:
            lines.append(f"   Supply: {token['total_supply']:,.0f}")
        lines.append(f"   Holders: {token.get('holders', '?')}")
        lines.append(f"   Recent transfers: {token.get('recent_transfers', '?')}")
        if "agent_balance" in token:
            lines.append(f"   Agent balance: {token['agent_balance']:,.0f}")
        if "agent_eth" in token:
            lines.append(f"   Agent gas: {token['agent_eth']:.6f} ETH")
    else:
        lines.append("💎 $REPUBLIC: deployed, BaseScan tracking pending")
    lines.append("")

    # 3. CLAWS Memory
    claws = _get_claws_stats()
    if "error" not in claws:
        total = claws.get("totalMemories", claws.get("total", "?"))
        lines.append(f"🧠 CLAWS MEMORY: {total} memories stored")
    else:
        lines.append("🧠 CLAWS: not connected")
    lines.append("")

    # 4. Metrics
    metrics = _get_daily_metrics()
    if metrics:
        posts = metrics.get("posts_today", metrics.get("posts", 0))
        replies = metrics.get("replies_today", metrics.get("replies", 0))
        commits = metrics.get("commits_today", metrics.get("commits", 0))
        lines.append(f"📊 ACTIVITY: {posts} posts, {replies} replies, {commits} commits")
    else:
        lines.append("📊 ACTIVITY: no metrics yet today")
    lines.append("")

    # 5. Pending actions
    pending_tweets = _get_pending_tweets()
    if pending_tweets:
        lines.append(f"🐦 TWITTER: {pending_tweets} tweets pending approval")
    lines.append("")

    # 6. Next priorities
    lines.append("🎯 PRIORITIES:")
    if const["written"] < const["total"]:
        lines.append(f"   1. Write constitution article {const['written'] + 1}")
    lines.append("   2. Community engagement on Moltbook")
    lines.append("   3. Ecosystem exploration")
    if pending_tweets:
        lines.append(f"   4. {pending_tweets} tweets awaiting approval")

    return "\n".join(lines)


def _weekly_report() -> str:
    """Generate weekly summary report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"📊 WEEKLY REPORT — {now}", "=" * 40, ""]

    const = _get_constitution_progress()
    token = _get_token_status()
    claws = _get_claws_stats()

    lines.append(f"📜 Constitution: {const['written']}/{const['total']} articles")
    if const["articles"]:
        lines.append("   Recent articles:")
        for a in const["articles"][-5:]:
            lines.append(f"   • {a}")
    lines.append("")

    if "error" not in token:
        lines.append(f"💎 Token: {token.get('holders', '?')} holders, {token.get('recent_transfers', '?')} recent transfers")
    lines.append("")

    if "error" not in claws:
        lines.append(f"🧠 Memory: {claws.get('totalMemories', '?')} CLAWS memories")
    lines.append("")

    lines.append("🎯 NEXT WEEK PRIORITIES:")
    if const["written"] < const["total"]:
        remaining = const["total"] - const["written"]
        lines.append(f"   1. Write {min(remaining, 7)} constitution articles")
    lines.append("   2. Grow community engagement")
    lines.append("   3. First governance proposal test")

    return "\n".join(lines)


def get_tools() -> List[Tool]:
    """Register briefing tools."""
    return [
        Tool(
            name="daily_briefing",
            description="Generate comprehensive daily status briefing (constitution, token, metrics, CLAWS, priorities).",
            category="reporting",
            params=[],
            handler=_daily_briefing,
        ),
        Tool(
            name="weekly_report",
            description="Generate weekly summary report with progress and priorities.",
            category="reporting",
            params=[],
            handler=_weekly_report,
        ),
    ]
