"""
Analytics Tools for The Constituent v5.0
==========================================
Project metrics and analytics dashboard.
"""

import json
import logging
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Analytics")


def _dashboard(metrics) -> str:
    """Generate a metrics dashboard summary."""
    sprint = metrics.get_sprint_summary()
    ratio = metrics.get_today_ratio()

    return (
        f"📊 Dashboard — Sprint Day {sprint.get('sprint_day', '?')}/21\n"
        f"  Posts: {sprint.get('total_posts', 0)} | "
        f"Commits: {sprint.get('total_commits', 0)} | "
        f"Engagements: {sprint.get('total_engagements', 0)}\n"
        f"  Today ratio: {ratio.get('ratio', 0):.1f} "
        f"({'✅' if ratio.get('on_target') else '❌'} target ≥2.0)\n"
        f"  Platforms: {json.dumps(sprint.get('platforms', {}))}\n"
        f"  Active days: {sprint.get('days_active', 0)}"
    )


def _daily_summary(metrics) -> str:
    """Generate daily summary text (for Telegram briefing)."""
    return metrics.get_daily_summary_text()


def get_tools(metrics) -> List[Tool]:
    return [
        Tool(name="analytics_dashboard", description="Show project metrics dashboard.", category="analytics",
             params=[], handler=lambda: _dashboard(metrics)),
        Tool(name="analytics_daily", description="Generate daily summary for Telegram briefing.", category="analytics",
             params=[], handler=lambda: _daily_summary(metrics)),
    ]
