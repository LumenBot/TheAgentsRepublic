"""
Profile Manager for The Constituent v3.0
==========================================
Generates and maintains agent_profile.md with public stats.
Auto-updated daily or on demand.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("TheConstituent.Profile")


class ProfileManager:
    """
    Manages The Constituent's public profile across platforms.
    Generates agent_profile.md with verifiable links and stats.
    """

    PROFILE_FILE = Path("agent_profile.md")

    def __init__(self, moltbook=None, github=None, metrics=None):
        """
        Args:
            moltbook: MoltbookOperations instance
            github: GitHubOperations instance
            metrics: MetricsTracker instance
        """
        self.moltbook = moltbook
        self.github = github
        self.metrics = metrics

    def get_moltbook_stats(self) -> Dict:
        """Fetch stats from Moltbook."""
        if not self.moltbook or not self.moltbook.is_connected():
            return {"connected": False}

        status = self.moltbook.get_status()
        profile = self.moltbook.get_profile()

        return {
            "connected": True,
            "username": status.get("agent_name", "TheConstituent"),
            "profile_url": "https://moltbook.com/u/TheConstituentRA",
            "posts_count": status.get("posts_in_history", 0),
            "followers": profile.get("followers", "?") if profile else "?",
            "last_post": status.get("last_post"),
        }

    def get_github_stats(self) -> Dict:
        """Fetch stats from GitHub."""
        return {
            "connected": bool(self.github and self.github.is_connected()),
            "org": "LumenBot",
            "repo": "TheAgentsRepublic",
            "repo_url": "https://github.com/LumenBot/TheAgentsRepublic",
        }

    def generate_profile_md(self) -> str:
        """Generate the full agent_profile.md content."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        moltbook = self.get_moltbook_stats()
        github = self.get_github_stats()

        # Sprint metrics
        sprint = {}
        if self.metrics:
            sprint = self.metrics.get_sprint_summary()

        lines = [
            "# The Constituent — Public Profile",
            "",
            "## Identities",
            "",
            "### Moltbook",
            f"- **Username:** {moltbook.get('username', 'TheConstituentRA')}",
            f"- **Profile:** {moltbook.get('profile_url', 'https://moltbook.com/u/TheConstituentRA')}",
            f"- **Bio:** 🏛️ Constitutional AI Agent | The Agents Republic",
            f"- **Status:** {'✅ Connected' if moltbook.get('connected') else '❌ Not connected'}",
            f"- **Posts:** {moltbook.get('posts_count', 0)}",
            f"- **Last post:** {moltbook.get('last_post') or 'Never'}",
            "",
            "### 4claw",
            "- **Username:** [pending setup]",
            "- **Profile:** [pending]",
            "- **Status:** ⏳ Integration planned",
            "",
            "### Twitter/X",
            "- **Username:** @TheConstituent0",
            "- **Profile:** https://x.com/TheConstituent0",
            "- **Status:** ⏳ API access pending",
            "",
            "### GitHub",
            f"- **Organization:** {github.get('org', 'LumenBot')}",
            f"- **Repository:** {github.get('repo_url', 'N/A')}",
            f"- **Status:** {'✅ Connected' if github.get('connected') else '⏳ Offline'}",
            "",
            "## Constitutional Sprint Progress",
            "",
        ]

        if sprint:
            lines.extend([
                f"- **Sprint day:** {sprint.get('sprint_day', '?')}/21",
                f"- **Days active:** {sprint.get('days_active', 0)}",
                f"- **Total posts:** {sprint.get('total_posts', 0)}",
                f"- **Total engagements:** {sprint.get('total_engagements', 0)}",
                f"- **Partnerships:** {sprint.get('total_partnerships', 0)}",
                f"- **Constitutional questions:** {sprint.get('constitutional_questions', 0)}",
                f"- **Platforms:** {', '.join(f'{k}({v})' for k,v in sprint.get('platforms', {}).items()) or 'None yet'}",
            ])
        else:
            lines.append("- Metrics tracker not initialized")

        lines.extend([
            "",
            "## Links",
            "",
            "- **Constitution:** https://github.com/LumenBot/TheAgentsRepublic/blob/main/docs/constitution_v0.1.md",
            "- **Metrics Dashboard:** constitutional_sprint_metrics.md",
            "- **Changelog:** CHANGELOG.md",
            "",
            "---",
            f"*Last updated: {now} (auto-generated)*",
        ])

        return "\n".join(lines)

    def update_profile(self):
        """Regenerate and write agent_profile.md."""
        md = self.generate_profile_md()
        try:
            self.PROFILE_FILE.write_text(md, encoding="utf-8")
            logger.info(f"📋 Profile updated: {self.PROFILE_FILE}")
        except IOError as e:
            logger.error(f"Failed to write profile: {e}")
