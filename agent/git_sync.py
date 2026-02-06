"""
The Constituent — Git Auto-Sync
=================================
Automatically commits and pushes data to GitHub for backup.

Runs on a schedule:
- Local commit: every 15 minutes
- Push to GitHub: every hour
- Forced push: before risky operations
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("TheConstituent.GitSync")

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    logger.warning("GitPython not installed — Git sync disabled")


class GitSync:
    """
    Auto-sync agent data to Git for backup and versioning.

    Tracked paths:
    - data/*.json (working memory, tweets)
    - data/*.db (SQLite database)
    - memory/knowledge/*.md (knowledge base)
    - constitution/*.md (Constitution files)
    """

    # Paths to track (relative to repo root)
    TRACKED_PATHS = [
        "data/",
        "memory/",
        "constitution/",
        "agent/data/",
    ]

    def __init__(self, repo_path: str = "."):
        """
        Initialize Git sync.

        Args:
            repo_path: Path to the Git repository root
        """
        self.repo_path = Path(repo_path).resolve()
        self.repo: Optional[git.Repo] = None
        self._enabled = False
        self._last_commit_time: Optional[datetime] = None
        self._last_push_time: Optional[datetime] = None
        self._commit_count = 0

        if not GIT_AVAILABLE:
            logger.info("Git sync disabled (GitPython not installed)")
            return

        try:
            self.repo = git.Repo(self.repo_path)
            self._enabled = True
            logger.info(f"Git sync initialized (repo: {self.repo_path})")
            logger.info(f"  Active branch: {self.repo.active_branch.name}")
            logger.info(f"  Remotes: {[r.name for r in self.repo.remotes]}")
        except git.InvalidGitRepositoryError:
            logger.warning(f"Not a Git repository: {self.repo_path}")
            logger.info("To enable Git sync, run: git init && git remote add origin <url>")
        except Exception as e:
            logger.error(f"Git initialization failed: {e}")

    @property
    def is_enabled(self) -> bool:
        return self._enabled and self.repo is not None

    def auto_commit(self, message: str = None) -> bool:
        """
        Stage tracked files and commit if there are changes.

        Args:
            message: Custom commit message (auto-generated if None)

        Returns:
            True if a commit was made
        """
        if not self.is_enabled:
            return False

        try:
            # Stage tracked paths
            changes_found = False
            for tracked_path in self.TRACKED_PATHS:
                full_path = self.repo_path / tracked_path
                if full_path.exists():
                    self.repo.index.add([tracked_path], force=False)
                    changes_found = True

            # Check if there are staged changes
            if not self.repo.index.diff("HEAD") and not self.repo.untracked_files:
                logger.debug("No changes to commit")
                return False

            # Generate commit message
            if message is None:
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                self._commit_count += 1
                message = f"auto: checkpoint #{self._commit_count} ({now})"

            # Commit
            self.repo.index.commit(message)
            self._last_commit_time = datetime.utcnow()
            logger.info(f"Git commit: {message}")
            return True

        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return False

    def push(self, force: bool = False) -> bool:
        """
        Push to remote (origin).

        Args:
            force: Force push (use with caution)

        Returns:
            True if push succeeded
        """
        if not self.is_enabled:
            return False

        if not self.repo.remotes:
            logger.warning("No remote configured — cannot push")
            return False

        try:
            remote = self.repo.remotes.origin
            branch = self.repo.active_branch.name

            if force:
                remote.push(refspec=f"{branch}:{branch}", force=True)
            else:
                remote.push(refspec=f"{branch}:{branch}")

            self._last_push_time = datetime.utcnow()
            logger.info(f"Git push to origin/{branch} successful")
            return True

        except Exception as e:
            logger.error(f"Git push failed: {e}")
            logger.info("This might be a network issue or authentication problem")
            return False

    def commit_and_push(self, message: str = None) -> bool:
        """Convenience: commit then push."""
        committed = self.auto_commit(message)
        if committed:
            return self.push()
        return False

    def force_backup(self, reason: str = "manual") -> bool:
        """
        Force an immediate commit + push.
        Used before risky operations.
        """
        message = f"backup: {reason} ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})"
        return self.commit_and_push(message)

    def get_status(self) -> dict:
        """Get Git sync status."""
        if not self.is_enabled:
            return {"enabled": False, "reason": "Git not available or not a repository"}

        try:
            return {
                "enabled": True,
                "repo_path": str(self.repo_path),
                "branch": self.repo.active_branch.name,
                "remotes": [r.name for r in self.repo.remotes],
                "has_changes": self.repo.is_dirty(),
                "last_commit": self._last_commit_time.isoformat() if self._last_commit_time else None,
                "last_push": self._last_push_time.isoformat() if self._last_push_time else None,
                "commit_count": self._commit_count
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}
