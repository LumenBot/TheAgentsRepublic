"""
Metrics Tracker for The Constituent v3.0
==========================================
Tracks every action with verifiable links.
Generates daily metrics report (constitutional_sprint_metrics.md).
Monitors execution/philosophy ratio.

Constitutional Sprint: 6 Feb → 27 Feb 2026 (21 days)
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger("TheConstituent.Metrics")

# Sprint dates
SPRINT_START = datetime(2026, 2, 6, tzinfo=timezone.utc)
SPRINT_END = datetime(2026, 2, 27, 23, 59, 59, tzinfo=timezone.utc)


class MetricsTracker:
    """
    Tracks all agent actions and generates daily metrics.
    
    Every action logged with:
    - Timestamp
    - Action type (post, commit, reflection, analysis, partnership)
    - Platform (moltbook, 4claw, github, twitter, etc.)
    - URL (verifiable link, if available)
    - Details (extra context)
    """

    DATA_DIR = Path(__file__).parent.parent / "data"
    DAILY_LOG_FILE = DATA_DIR / "daily_metrics.json"
    METRICS_MD_FILE = Path("constitutional_sprint_metrics.md")

    # Action categories
    EXECUTION_ACTIONS = {"post", "comment", "commit", "push", "partnership", "upvote", "registration"}
    PHILOSOPHY_ACTIONS = {"reflection", "analysis", "debate", "synthesis", "strategic_note"}

    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._daily_log: List[Dict] = self._load_log()

    def _load_log(self) -> List[Dict]:
        """Load daily metrics log from disk."""
        if self.DAILY_LOG_FILE.exists():
            try:
                with open(self.DAILY_LOG_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_log(self):
        """Save daily metrics log to disk."""
        try:
            with open(self.DAILY_LOG_FILE, 'w') as f:
                json.dump(self._daily_log, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save metrics log: {e}")

    # =========================================================================
    # Core: Log Actions
    # =========================================================================

    def log_action(self, action_type: str, platform: str = "",
                   url: str = None, details: Dict = None,
                   success: bool = True, error: str = None):
        """
        Log an action immediately.
        
        Args:
            action_type: post, comment, commit, reflection, analysis, partnership, etc.
            platform: moltbook, 4claw, github, twitter, etc.
            url: Verifiable link (REQUIRED for execution actions)
            details: Extra context dict
            success: Whether the action succeeded
            error: Error message if failed
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "action_type": action_type,
            "platform": platform,
            "url": url,
            "details": details or {},
            "success": success,
            "error": error,
        }

        self._daily_log.append(entry)
        self._save_log()

        # Log warning if execution action without URL
        if action_type in self.EXECUTION_ACTIONS and not url and success:
            logger.warning(f"⚠️ Execution action '{action_type}' logged WITHOUT verifiable URL")

        logger.info(f"📊 Metric: {action_type} on {platform} {'✅' if success else '❌'}"
                     + (f" → {url}" if url else ""))

    def log_error(self, action_type: str, platform: str, error: str, details: Dict = None):
        """Convenience: log a failed action."""
        self.log_action(action_type, platform, success=False, error=error, details=details)

    # =========================================================================
    # Queries
    # =========================================================================

    def get_today_entries(self) -> List[Dict]:
        """Get all entries for today UTC."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return [e for e in self._daily_log if e.get("date") == today]

    def get_date_entries(self, date_str: str) -> List[Dict]:
        """Get entries for a specific date (YYYY-MM-DD)."""
        return [e for e in self._daily_log if e.get("date") == date_str]

    def get_today_ratio(self) -> Dict:
        """
        Calculate execution/philosophy ratio for today.
        
        Returns:
            {
                "execution_count": int,
                "philosophy_count": int,
                "ratio": float,
                "target": 2.0,
                "on_target": bool
            }
        """
        today_entries = self.get_today_entries()
        
        exec_count = len([e for e in today_entries 
                          if e["action_type"] in self.EXECUTION_ACTIONS and e.get("success")])
        phil_count = len([e for e in today_entries 
                          if e["action_type"] in self.PHILOSOPHY_ACTIONS])

        ratio = exec_count / phil_count if phil_count > 0 else float(exec_count)

        return {
            "execution_count": exec_count,
            "philosophy_count": phil_count,
            "ratio": round(ratio, 2),
            "target": 2.0,
            "on_target": ratio >= 2.0
        }

    def get_sprint_day(self) -> int:
        """Get current sprint day (1-21, or 0 if before/after sprint)."""
        now = datetime.now(timezone.utc)
        if now < SPRINT_START:
            return 0
        if now > SPRINT_END:
            return 22  # Past sprint
        return (now - SPRINT_START).days + 1

    def get_sprint_summary(self) -> Dict:
        """Get overall sprint summary."""
        total_posts = len([e for e in self._daily_log 
                          if e["action_type"] == "post" and e.get("success")])
        total_commits = len([e for e in self._daily_log 
                            if e["action_type"] == "commit" and e.get("success")])
        total_engagements = len([e for e in self._daily_log 
                                if e["action_type"] in {"comment", "upvote"} and e.get("success")])
        total_partnerships = len([e for e in self._daily_log 
                                  if e["action_type"] == "partnership" and e.get("success")])
        
        # Count constitutional questions (posts tagged as such)
        const_questions = len([e for e in self._daily_log 
                              if e.get("details", {}).get("type") == "constitutional_question"])

        # Unique active dates
        active_dates = set(e.get("date") for e in self._daily_log if e.get("success"))

        # Platform breakdown
        platforms = {}
        for e in self._daily_log:
            if e.get("success") and e.get("platform"):
                p = e["platform"]
                platforms[p] = platforms.get(p, 0) + 1

        return {
            "sprint_day": self.get_sprint_day(),
            "total_days": 21,
            "days_active": len(active_dates),
            "total_posts": total_posts,
            "total_commits": total_commits,
            "total_engagements": total_engagements,
            "total_partnerships": total_partnerships,
            "constitutional_questions": const_questions,
            "platforms": platforms,
            "total_entries": len(self._daily_log),
        }

    # =========================================================================
    # Metrics Markdown Generation
    # =========================================================================

    def generate_metrics_md(self) -> str:
        """Generate the constitutional_sprint_metrics.md file."""
        summary = self.get_sprint_summary()
        today_ratio = self.get_today_ratio()

        lines = [
            "# Constitutional Sprint - Daily Metrics",
            "",
            "## Summary",
            f"- **Sprint day:** {summary['sprint_day']}/{summary['total_days']}",
            f"- **Days active:** {summary['days_active']}",
            f"- **Total posts:** {summary['total_posts']}",
            f"- **Total commits:** {summary['total_commits']}",
            f"- **Total engagements:** {summary['total_engagements']}",
            f"- **Partnerships formed:** {summary['total_partnerships']}",
            f"- **Constitutional questions:** {summary['constitutional_questions']}",
            f"- **Platforms:** {', '.join(f'{k}({v})' for k,v in summary['platforms'].items()) or 'None yet'}",
            "",
            "---",
            "",
        ]

        # Group by date (most recent first)
        dates = sorted(set(e.get("date") for e in self._daily_log), reverse=True)

        for date_str in dates[:14]:  # Last 14 days max
            entries = self.get_date_entries(date_str)
            exec_entries = [e for e in entries if e["action_type"] in self.EXECUTION_ACTIONS]
            phil_entries = [e for e in entries if e["action_type"] in self.PHILOSOPHY_ACTIONS]
            failed_entries = [e for e in entries if not e.get("success")]

            exec_count = len([e for e in exec_entries if e.get("success")])
            phil_count = len(phil_entries)
            ratio = exec_count / phil_count if phil_count > 0 else float(exec_count)
            ratio_icon = "✅" if ratio >= 2.0 else "❌"

            lines.append(f"## {date_str}")
            lines.append("")
            lines.append("### Execution")

            # Group exec by platform
            by_platform = {}
            for e in exec_entries:
                p = e.get("platform", "unknown")
                if p not in by_platform:
                    by_platform[p] = []
                by_platform[p].append(e)

            for platform, pentries in by_platform.items():
                success = [e for e in pentries if e.get("success")]
                failed = [e for e in pentries if not e.get("success")]
                lines.append(f"- **{platform}:** {len(success)} success, {len(failed)} failed")
                for e in success:
                    url = e.get("url", "no link")
                    atype = e["action_type"]
                    lines.append(f"  - ✅ {atype}: {url}")
                for e in failed:
                    err = e.get("error", "unknown error")
                    atype = e["action_type"]
                    lines.append(f"  - ❌ {atype}: {err}")

            if not by_platform:
                lines.append("- No execution actions this day")

            # Failed actions
            if failed_entries:
                lines.append("")
                lines.append("### Errors")
                for e in failed_entries:
                    lines.append(f"- ❌ {e['action_type']} ({e.get('platform', '?')}): {e.get('error', '?')}")

            # Philosophy
            if phil_entries:
                lines.append("")
                lines.append("### Philosophy")
                for e in phil_entries:
                    detail = e.get("details", {}).get("summary", e["action_type"])
                    lines.append(f"- {e['action_type']}: {detail}")

            # Ratio
            lines.append("")
            lines.append(f"### Ratio: **{ratio:.2f}** {ratio_icon} (target: ≥2.0)")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def update_metrics_file(self):
        """Regenerate metrics markdown and write to disk."""
        md = self.generate_metrics_md()
        try:
            self.METRICS_MD_FILE.write_text(md, encoding="utf-8")
            logger.info(f"📊 Metrics file updated: {self.METRICS_MD_FILE}")
        except IOError as e:
            logger.error(f"Failed to write metrics file: {e}")

    # =========================================================================
    # Daily Summary (for Telegram notification)
    # =========================================================================

    def get_daily_summary_text(self) -> str:
        """Get a concise daily summary for Telegram."""
        ratio = self.get_today_ratio()
        summary = self.get_sprint_summary()
        today = self.get_today_entries()

        success_posts = [e for e in today if e["action_type"] == "post" and e.get("success")]
        failed_posts = [e for e in today if e["action_type"] == "post" and not e.get("success")]
        commits = [e for e in today if e["action_type"] == "commit" and e.get("success")]

        text = f"""📊 **Daily Metrics — Sprint Day {summary['sprint_day']}/21**

**Today's Execution:**
├ Posts: {len(success_posts)} ✅ / {len(failed_posts)} ❌
├ Commits: {len(commits)}
├ Engagements: {ratio['execution_count']} total
└ Philosophy: {ratio['philosophy_count']}

**Ratio:** {ratio['ratio']:.2f} {'✅' if ratio['on_target'] else '❌'} (target: ≥2.0)

**Sprint Total:**
├ Posts: {summary['total_posts']}
├ Engagements: {summary['total_engagements']}
└ Partnerships: {summary['total_partnerships']}"""

        return text
