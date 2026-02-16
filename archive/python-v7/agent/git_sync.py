"""
The Constituent — Git Auto-Sync v2.4
=======================================
Automatically commits and pushes to GitHub for backup and versioning.

v2.4 changes (v5.3.1):
- CLI fallback: works with git CLI when GitPython not installed
- shutil.which("git") check instead of import git
- All methods work in both GitPython and CLI modes

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
import glob as globmod
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger("TheConstituent.GitSync")

# Detect available git backends
_HAS_GITPYTHON = False
try:
    import git
    _HAS_GITPYTHON = True
except ImportError:
    pass

_GIT_CLI = shutil.which("git")

if _HAS_GITPYTHON:
    logger.info("Git backend: GitPython")
elif _GIT_CLI:
    logger.info(f"Git backend: CLI ({_GIT_CLI})")
else:
    logger.warning("No git available — Git sync fully disabled")


class GitSync:
    """
    Auto-sync agent data and code to Git.

    v2.4: Works with either GitPython or git CLI (subprocess fallback).

    Tracked paths (v2.3 — expanded):
    - agent/*.py (agent code)
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
        self.repo = None  # GitPython Repo object (if available)
        self._enabled = False
        self._use_cli = False  # True = subprocess mode, False = GitPython mode
        self._last_commit_time: Optional[datetime] = None
        self._last_push_time: Optional[datetime] = None
        self._commit_count = 0
        self._push_failures = 0
        self._notify_fn = notify_fn

        # Try GitPython first
        if _HAS_GITPYTHON:
            try:
                self.repo = git.Repo(self.repo_path)
                self._enabled = True
                self._use_cli = False
                branch = self.repo.active_branch.name
                remotes = [r.name for r in self.repo.remotes]
                logger.info(f"Git sync initialized via GitPython (repo: {self.repo_path})")
                logger.info(f"  Active branch: {branch}")
                logger.info(f"  Remotes: {remotes}")

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
                return
            except Exception as e:
                logger.warning(f"GitPython init failed: {e}")

        # Fallback to CLI mode
        if _GIT_CLI:
            # Verify this is a git repo
            result = self._run_git(["rev-parse", "--is-inside-work-tree"])
            if result and result.strip() == "true":
                self._enabled = True
                self._use_cli = True
                branch = self._run_git(["branch", "--show-current"]) or "unknown"
                logger.info(f"Git sync initialized via CLI (repo: {self.repo_path})")
                logger.info(f"  Active branch: {branch.strip()}")
            else:
                logger.warning(f"Not a Git repository: {self.repo_path}")
        else:
            logger.info("Git sync disabled (no git available)")

    def _run_git(self, args: list, check: bool = False) -> Optional[str]:
        """Run a git CLI command and return stdout, or None on error."""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True, text=True,
                cwd=str(self.repo_path),
                timeout=30,
            )
            if check and result.returncode != 0:
                logger.error(f"git {' '.join(args)} failed: {result.stderr.strip()}")
                return None
            return result.stdout
        except Exception as e:
            logger.error(f"git {' '.join(args)} error: {e}")
            return None

    def _run_git_rc(self, args: list) -> tuple:
        """Run a git CLI command, return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True, text=True,
                cwd=str(self.repo_path),
                timeout=30,
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)

    @property
    def is_enabled(self) -> bool:
        if self._use_cli:
            return self._enabled
        return self._enabled and self.repo is not None

    # =================================================================
    # auto_commit
    # =================================================================

    def auto_commit(self, message: str = None) -> bool:
        """
        Stage all tracked files and commit if there are changes.

        Returns:
            True if a commit was made
        """
        if not self.is_enabled:
            return False

        if self._use_cli:
            return self._auto_commit_cli(message)
        return self._auto_commit_gitpython(message)

    def _auto_commit_cli(self, message: str = None) -> bool:
        """Stage and commit using git CLI."""
        try:
            # Stage tracked directories
            for tracked_path in self.TRACKED_PATHS:
                full_path = self.repo_path / tracked_path
                if full_path.exists():
                    self._run_git(["add", "-A", tracked_path])

            # Stage root-level files
            for pattern in self.ROOT_PATTERNS:
                matches = globmod.glob(str(self.repo_path / pattern))
                for match in matches:
                    rel_path = os.path.relpath(match, self.repo_path)
                    skip = False
                    for ignore in self.IGNORE_PATTERNS:
                        if ignore.startswith("*"):
                            if rel_path.endswith(ignore[1:]):
                                skip = True
                        elif rel_path == ignore:
                            skip = True
                    if not skip:
                        self._run_git(["add", rel_path])

            # Check for staged changes
            rc, stdout, _ = self._run_git_rc(["diff", "--cached", "--name-only"])
            if not stdout.strip():
                logger.debug("No changes to commit")
                return False

            # Generate message
            if message is None:
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                self._commit_count += 1
                changed = [f for f in stdout.strip().split("\n") if f]
                if len(changed) <= 3:
                    files_desc = ", ".join(changed)
                else:
                    files_desc = f"{len(changed)} files"
                message = f"auto: checkpoint #{self._commit_count} — {files_desc} ({now})"

            # Commit
            rc, _, stderr = self._run_git_rc(["commit", "-m", message])
            if rc != 0:
                logger.error(f"Git commit failed: {stderr.strip()}")
                return False

            self._last_commit_time = datetime.utcnow()
            self._commit_count += 1 if message and not message.startswith("auto:") else 0
            logger.info(f"Git commit: {message}")
            return True

        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return False

    def _auto_commit_gitpython(self, message: str = None) -> bool:
        """Stage and commit using GitPython."""
        try:
            for tracked_path in self.TRACKED_PATHS:
                full_path = self.repo_path / tracked_path
                if full_path.exists():
                    self.repo.git.add(tracked_path, A=True)

            for pattern in self.ROOT_PATTERNS:
                matches = globmod.glob(str(self.repo_path / pattern))
                for match in matches:
                    rel_path = os.path.relpath(match, self.repo_path)
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
                            pass

            staged = self.repo.index.diff("HEAD")
            untracked = [f for f in self.repo.untracked_files
                        if any(f.startswith(p) for p in self.TRACKED_PATHS)]

            if not staged and not untracked:
                logger.debug("No changes to commit")
                return False

            if message is None:
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                self._commit_count += 1
                changed_files = [d.a_path for d in staged]
                if len(changed_files) <= 3:
                    files_desc = ", ".join(changed_files)
                else:
                    files_desc = f"{len(changed_files)} files"
                message = f"auto: checkpoint #{self._commit_count} — {files_desc} ({now})"

            self.repo.index.commit(message)
            self._last_commit_time = datetime.utcnow()
            self._commit_count += 1 if message and not message.startswith("auto:") else 0
            logger.info(f"Git commit: {message}")
            return True

        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return False

    # =================================================================
    # push
    # =================================================================

    def push(self, force: bool = False) -> bool:
        """Push to remote (origin). Returns True if push succeeded."""
        if not self.is_enabled:
            return False

        if self._use_cli:
            return self._push_cli(force)
        return self._push_gitpython(force)

    def _push_cli(self, force: bool = False) -> bool:
        """Push using git CLI."""
        branch = (self._run_git(["branch", "--show-current"]) or "").strip()
        if not branch:
            logger.warning("Cannot determine current branch")
            return False

        # Check if remote exists
        remotes = (self._run_git(["remote"]) or "").strip()
        if not remotes:
            logger.warning("No remote configured — cannot push")
            return False

        logger.info(f"Pushing to origin/{branch}...")
        cmd = ["push", "origin", branch]
        if force:
            cmd.insert(1, "--force")

        rc, stdout, stderr = self._run_git_rc(cmd)
        if rc != 0:
            self._push_failures += 1
            error_msg = stderr.strip()
            logger.error(f"Git push failed: {error_msg}")

            if "Authentication" in error_msg or "403" in error_msg:
                logger.error("🔑 AUTH ISSUE: GitHub credentials not configured")
            elif "rejected" in error_msg or "non-fast-forward" in error_msg:
                logger.error("🔀 DIVERGENCE: Local and remote have diverged")
            elif "Could not resolve host" in error_msg:
                logger.error("🌐 NETWORK: Cannot reach GitHub")

            return False

        self._last_push_time = datetime.utcnow()
        self._push_failures = 0
        logger.info(f"✅ Git push to origin/{branch} successful")
        return True

    def _push_gitpython(self, force: bool = False) -> bool:
        """Push using GitPython."""
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

            if push_info:
                for info in push_info:
                    if info.flags & info.ERROR:
                        logger.error(f"Push error: {info.summary}")
                        self._push_failures += 1
                        return False
                    elif info.flags & info.REJECTED:
                        logger.error(f"Push rejected: {info.summary}")
                        self._push_failures += 1
                        return False

            self._last_push_time = datetime.utcnow()
            self._push_failures = 0
            logger.info(f"✅ Git push to origin/{branch} successful")
            return True

        except Exception as e:
            self._push_failures += 1
            logger.error(f"Git push failed: {e}")
            return False

    # =================================================================
    # High-level operations
    # =================================================================

    def commit_and_push(self, message: str = None) -> bool:
        """Convenience: commit then push."""
        committed = self.auto_commit(message)
        if committed:
            return self.push()
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
            result["error"] = "⚠️ Git not available. Install git or add to PATH."
            return result

        if self._use_cli:
            return self._sync_now_cli(result)
        return self._sync_now_gitpython(result)

    def _sync_now_cli(self, result: dict) -> dict:
        """Full sync using git CLI."""
        try:
            branch = (self._run_git(["branch", "--show-current"]) or "").strip()
            result["branch"] = branch or "detached HEAD"

            remotes = (self._run_git(["remote"]) or "").strip()
            result["has_remote"] = bool(remotes)

            status_out = (self._run_git(["status", "--porcelain"]) or "").strip()
            result["dirty"] = bool(status_out)

            if result["has_remote"] and branch:
                unpushed = self._run_git(["log", f"origin/{branch}..HEAD", "--oneline"])
                if unpushed is not None:
                    lines = [l for l in unpushed.strip().split("\n") if l]
                    result["unpushed_commits"] = len(lines)
                else:
                    result["unpushed_commits"] = "unknown"

            committed = self.auto_commit(f"sync: manual sync ({datetime.utcnow().strftime('%H:%M UTC')})")
            result["committed"] = committed

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

    def _sync_now_gitpython(self, result: dict) -> dict:
        """Full sync using GitPython."""
        try:
            result["branch"] = self.repo.active_branch.name
            result["has_remote"] = len(self.repo.remotes) > 0
            result["dirty"] = self.repo.is_dirty(untracked_files=True)

            if result["has_remote"]:
                try:
                    branch = self.repo.active_branch.name
                    ahead = list(self.repo.iter_commits(f"origin/{branch}..{branch}"))
                    result["unpushed_commits"] = len(ahead)
                except Exception:
                    result["unpushed_commits"] = "unknown"

            committed = self.auto_commit(f"sync: manual sync ({datetime.utcnow().strftime('%H:%M UTC')})")
            result["committed"] = committed

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

    # =================================================================
    # Status
    # =================================================================

    def get_status(self) -> dict:
        """Get comprehensive Git sync status."""
        if not self.is_enabled:
            return {"enabled": False, "reason": "Git not available or not a repository"}

        if self._use_cli:
            return self._get_status_cli()
        return self._get_status_gitpython()

    def _get_status_cli(self) -> dict:
        """Get status using git CLI."""
        try:
            branch = (self._run_git(["branch", "--show-current"]) or "").strip()
            remotes = (self._run_git(["remote"]) or "").strip().split("\n")
            remotes = [r for r in remotes if r]
            status_out = (self._run_git(["status", "--porcelain"]) or "").strip()

            status = {
                "enabled": True,
                "mode": "cli",
                "repo_path": str(self.repo_path),
                "branch": branch or "detached HEAD",
                "remotes": remotes,
                "dirty": bool(status_out),
                "last_commit": self._last_commit_time.isoformat() if self._last_commit_time else None,
                "last_push": self._last_push_time.isoformat() if self._last_push_time else None,
                "commit_count": self._commit_count,
                "push_failures": self._push_failures,
            }

            if remotes and branch:
                unpushed = self._run_git(["log", f"origin/{branch}..HEAD", "--oneline"])
                if unpushed is not None:
                    lines = [l for l in unpushed.strip().split("\n") if l]
                    status["unpushed_commits"] = len(lines)
                else:
                    status["unpushed_commits"] = "unknown"

            return status

        except Exception as e:
            return {"enabled": True, "mode": "cli", "error": str(e)}

    def _get_status_gitpython(self) -> dict:
        """Get status using GitPython."""
        try:
            status = {
                "enabled": True,
                "mode": "gitpython",
                "repo_path": str(self.repo_path),
                "branch": self.repo.active_branch.name,
                "remotes": [r.name for r in self.repo.remotes],
                "dirty": self.repo.is_dirty(untracked_files=True),
                "last_commit": self._last_commit_time.isoformat() if self._last_commit_time else None,
                "last_push": self._last_push_time.isoformat() if self._last_push_time else None,
                "commit_count": self._commit_count,
                "push_failures": self._push_failures,
            }

            if self.repo.remotes:
                try:
                    branch = self.repo.active_branch.name
                    ahead = list(self.repo.iter_commits(f"origin/{branch}..{branch}"))
                    status["unpushed_commits"] = len(ahead)
                except Exception:
                    status["unpushed_commits"] = "unknown"

            return status

        except Exception as e:
            return {"enabled": True, "mode": "gitpython", "error": str(e)}
