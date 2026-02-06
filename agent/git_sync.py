"""
The Constituent — Git Auto-Sync v2.3
=======================================
Automatically commits and pushes to GitHub for backup and versioning.

v2.3 changes:
- Tracks ALL project files (not just data/)
- Better push error diagnostics
- Explicit git add for new files
- Push status reporting via callback
- Manual sync command support

Schedule:
- Local commit: every 15 minutes
- Push to GitHub: every hour
- Forced push: before risky operations / on shutdown
"""

import os
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger("TheConstituent.GitSync")

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    # v5.2: Distinguish "GitPython missing" from "git CLI missing"
    _git_cli = shutil.which("git")
    if _git_cli:
        logger.warning(
            "GitPython not installed — Git sync disabled "
            f"(git CLI available at {_git_cli}, install GitPython to enable sync)"
        )
    else:
        logger.warning("Neither GitPython nor git CLI found — Git sync fully disabled")


class GitSync:
    """
    Auto-sync agent data and code to Git.

    Tracked paths (v2.3 — expanded):
    - agent/*.py (agent code — NEW)
    - data/*.json (working memory, tweets, credentials)
    - data/*.db (SQLite database)
    - memory/knowledge/*.md (knowledge base)
    - constitution/*.md (Constitution files)
    - docs/ (documentation)
    - *.md, *.txt (root docs like README)
    """

    # Paths to track (relative to repo root)
    TRACKED_PATHS = [
        "agent/",
        "data/",
        "memory/",
        "constitution/",
        "docs/",
    ]

    # File patterns to always include from repo root
    ROOT_PATTERNS = [
        "*.md",
        "*.txt",
        "*.py",
        ".env.example",
        "requirements.txt",
        "docker-compose.yml",
        "Dockerfile",
        "start.sh",
    ]

    # Files to never commit (sensitive)
    IGNORE_PATTERNS = [
        ".env",
        "*.pyc",
        "__pycache__",
        "*.db-journal",
    ]

    def __init__(self, repo_path: str = ".", notify_fn: Optional[Callable] = None):
        """
        Initialize Git sync.

        Args:
            repo_path: Path to the Git repository root
            notify_fn: Optional async callback for push status notifications
        """
        self.repo_path = Path(repo_path).resolve()
        self.repo: Optional[git.Repo] = None
        self._enabled = False
        self._last_commit_time: Optional[datetime] = None
        self._last_push_time: Optional[datetime] = None
        self._commit_count = 0
        self._push_failures = 0
        self._notify_fn = notify_fn

        if not GIT_AVAILABLE:
            logger.info("Git sync disabled (GitPython not installed)")
            return

        try:
            self.repo = git.Repo(self.repo_path)
            self._enabled = True
            branch = self.repo.active_branch.name
            remotes = [r.name for r in self.repo.remotes]
            logger.info(f"Git sync initialized (repo: {self.repo_path})")
            logger.info(f"  Active branch: {branch}")
            logger.info(f"  Remotes: {remotes}")

            # Check remote URL to detect auth issues early
            if self.repo.remotes:
                remote_url = self.repo.remotes.origin.url
                if "github.com" in remote_url:
                    if remote_url.startswith("https://"):
                        logger.info(f"  Remote URL: HTTPS ({remote_url[:50]}...)")
                        logger.info("  ⚠️  HTTPS requires credential helper or token in URL")
                    elif remote_url.startswith("git@"):
                        logger.info(f"  Remote URL: SSH ({remote_url[:50]}...)")
                    else:
                        logger.info(f"  Remote URL: {remote_url[:60]}")

        except git.InvalidGitRepositoryError:
            logger.warning(f"Not a Git repository: {self.repo_path}")
        except Exception as e:
            logger.error(f"Git initialization failed: {e}")

    @property
    def is_enabled(self) -> bool:
        return self._enabled and self.repo is not None

    def auto_commit(self, message: str = None) -> bool:
        """
        Stage all tracked files and commit if there are changes.

        Args:
            message: Custom commit message (auto-generated if None)

        Returns:
            True if a commit was made
        """
        if not self.is_enabled:
            return False

        try:
            # Stage tracked directories
            for tracked_path in self.TRACKED_PATHS:
                full_path = self.repo_path / tracked_path
                if full_path.exists():
                    # Use git add with --all to catch new, modified, and deleted files
                    self.repo.git.add(tracked_path, A=True)

            # Stage root-level files
            for pattern in self.ROOT_PATTERNS:
                import glob
                matches = glob.glob(str(self.repo_path / pattern))
                for match in matches:
                    rel_path = os.path.relpath(match, self.repo_path)
                    # Skip ignored files
                    skip = False
                    for ignore in self.IGNORE_PATTERNS:
                        if ignore.startswith("*"):
                            if rel_path.endswith(ignore[1:]):
                                skip = True
                        elif rel_path == ignore:
                            skip = True
                    if not skip:
                        try:
                            self.repo.git.add(rel_path)
                        except Exception:
                            pass  # Skip files that can't be added

            # Check if there are staged changes
            staged = self.repo.index.diff("HEAD")
            untracked = [f for f in self.repo.untracked_files
                        if any(f.startswith(p) for p in self.TRACKED_PATHS)]
            
            if not staged and not untracked:
                logger.debug("No changes to commit")
                return False

            # Generate commit message
            if message is None:
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                self._commit_count += 1
                
                # Describe what changed
                changed_files = [d.a_path for d in staged]
                if len(changed_files) <= 3:
                    files_desc = ", ".join(changed_files)
                else:
                    files_desc = f"{len(changed_files)} files"
                
                message = f"auto: checkpoint #{self._commit_count} — {files_desc} ({now})"

            # Commit
            self.repo.index.commit(message)
            self._last_commit_time = datetime.utcnow()
            self._commit_count += 1 if message and not message.startswith("auto:") else 0
            logger.info(f"Git commit: {message}")
            return True

        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return False

    def push(self, force: bool = False) -> bool:
        """
        Push to remote (origin).

        Returns True if push succeeded. Logs detailed error info on failure.
        """
        if not self.is_enabled:
            return False

        if not self.repo.remotes:
            logger.warning("No remote configured — cannot push")
            return False

        try:
            remote = self.repo.remotes.origin
            branch = self.repo.active_branch.name

            logger.info(f"Pushing to origin/{branch}...")

            if force:
                push_info = remote.push(refspec=f"{branch}:{branch}", force=True)
            else:
                push_info = remote.push(refspec=f"{branch}:{branch}")

            # Check push result
            if push_info:
                for info in push_info:
                    if info.flags & info.ERROR:
                        logger.error(f"Push error: {info.summary}")
                        self._push_failures += 1
                        return False
                    elif info.flags & info.REJECTED:
                        logger.error(f"Push rejected: {info.summary}")
                        logger.info("Try: git pull --rebase origin main")
                        self._push_failures += 1
                        return False

            self._last_push_time = datetime.utcnow()
            self._push_failures = 0
            logger.info(f"✅ Git push to origin/{branch} successful")
            return True

        except git.GitCommandError as e:
            self._push_failures += 1
            error_msg = str(e)
            logger.error(f"Git push failed: {error_msg}")

            # Diagnose common issues
            if "Authentication" in error_msg or "403" in error_msg:
                logger.error("🔑 AUTH ISSUE: GitHub credentials not configured")
                logger.error("   Fix: git remote set-url origin https://<TOKEN>@github.com/LumenBot/TheAgentsRepublic.git")
                logger.error("   Or configure git credential helper")
            elif "rejected" in error_msg or "non-fast-forward" in error_msg:
                logger.error("🔀 DIVERGENCE: Local and remote have diverged")
                logger.error("   Fix: git pull --rebase origin main")
            elif "Could not resolve host" in error_msg:
                logger.error("🌐 NETWORK: Cannot reach GitHub")
            else:
                logger.error(f"   Unknown push error. Try manually: git push origin {self.repo.active_branch.name}")

            return False

        except Exception as e:
            self._push_failures += 1
            logger.error(f"Git push failed (unexpected): {e}")
            return False

    def commit_and_push(self, message: str = None) -> bool:
        """Convenience: commit then push."""
        committed = self.auto_commit(message)
        if committed:
            return self.push()
        # Even if no new commit, try to push (there might be unpushed commits)
        return self.push()

    def force_backup(self, reason: str = "manual") -> bool:
        """Force an immediate commit + push."""
        message = f"backup: {reason} ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})"
        return self.commit_and_push(message)

    def sync_now(self) -> dict:
        """
        Full sync: stage all, commit, push.
        Returns detailed status for the operator.
        """
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "committed": False,
            "pushed": False,
            "error": None,
        }

        if not self.is_enabled:
            result["error"] = "Git not available"
            return result

        try:
            # Check current status
            result["branch"] = self.repo.active_branch.name
            result["has_remote"] = len(self.repo.remotes) > 0
            result["dirty"] = self.repo.is_dirty(untracked_files=True)

            # Count unpushed commits
            if result["has_remote"]:
                try:
                    branch = self.repo.active_branch.name
                    ahead = list(self.repo.iter_commits(f"origin/{branch}..{branch}"))
                    result["unpushed_commits"] = len(ahead)
                except:
                    result["unpushed_commits"] = "unknown"

            # Commit
            committed = self.auto_commit(f"sync: manual sync ({datetime.utcnow().strftime('%H:%M UTC')})")
            result["committed"] = committed

            # Push
            if result["has_remote"]:
                pushed = self.push()
                result["pushed"] = pushed
                if not pushed:
                    result["error"] = "Push failed — check logs for details"
            else:
                result["error"] = "No remote configured"

        except Exception as e:
            result["error"] = str(e)

        return result

    def get_status(self) -> dict:
        """Get comprehensive Git sync status."""
        if not self.is_enabled:
            return {"enabled": False, "reason": "Git not available or not a repository"}

        try:
            status = {
                "enabled": True,
                "repo_path": str(self.repo_path),
                "branch": self.repo.active_branch.name,
                "remotes": [r.name for r in self.repo.remotes],
                "dirty": self.repo.is_dirty(untracked_files=True),
                "last_commit": self._last_commit_time.isoformat() if self._last_commit_time else None,
                "last_push": self._last_push_time.isoformat() if self._last_push_time else None,
                "commit_count": self._commit_count,
                "push_failures": self._push_failures,
            }

            # Count unpushed commits
            if self.repo.remotes:
                try:
                    branch = self.repo.active_branch.name
                    ahead = list(self.repo.iter_commits(f"origin/{branch}..{branch}"))
                    status["unpushed_commits"] = len(ahead)
                except:
                    status["unpushed_commits"] = "unknown"

            return status

        except Exception as e:
            return {"enabled": True, "error": str(e)}
