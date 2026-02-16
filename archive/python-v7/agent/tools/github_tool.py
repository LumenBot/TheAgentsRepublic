"""
GitHub Tools for The Constituent v5.0
=======================================
Git operations and GitHub API via gh CLI.
"""

import subprocess
import logging
from pathlib import Path
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.GitHub")


def _run(cmd: str, cwd: str = ".", timeout: int = 30) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        output = (r.stdout + r.stderr).strip()
        return output if output else f"(exit code {r.returncode})"
    except Exception as e:
        return f"Error: {e}"


def _git_commit(message: str) -> str:
    _run("git add -A")
    result = _run(f'git commit -m "{message}"')
    if "nothing to commit" in result:
        return "Nothing to commit (working tree clean)"
    return result


def _git_push() -> str:
    return _run("git push")


def _git_status() -> str:
    return _run("git status --short")


def _git_log(count: int = 10) -> str:
    return _run(f"git log --oneline -n {count}")


def _github_create_issue(title: str, body: str) -> str:
    return _run(f'gh issue create --title "{title}" --body "{body}"')


def _github_list_issues(state: str = "open") -> str:
    return _run(f"gh issue list --state {state} --limit 20")


def _github_create_pr(title: str, body: str, branch: str = "") -> str:
    if branch:
        return _run(f'gh pr create --title "{title}" --body "{body}" --head {branch}')
    return _run(f'gh pr create --title "{title}" --body "{body}"')


def _github_list_prs() -> str:
    return _run("gh pr list --limit 10")


def get_tools() -> List[Tool]:
    return [
        Tool(name="git_commit", description="Stage all changes and commit.", category="github",
             params=[ToolParam("message", "string", "Commit message")],
             handler=_git_commit),
        Tool(name="git_push", description="Push commits to remote.", category="github",
             params=[], handler=_git_push),
        Tool(name="git_status", description="Show modified/untracked files.", category="github",
             params=[], handler=_git_status),
        Tool(name="git_log", description="Show recent commits.", category="github",
             params=[ToolParam("count", "integer", "Number of commits", required=False, default=10)],
             handler=lambda count=10: _git_log(int(count))),
        Tool(name="github_create_issue", description="Create a GitHub issue.", category="github",
             governance_level="L2",
             params=[ToolParam("title", "string", "Issue title"), ToolParam("body", "string", "Issue body")],
             handler=_github_create_issue),
        Tool(name="github_list_issues", description="List GitHub issues.", category="github",
             params=[ToolParam("state", "string", "open/closed/all", required=False, default="open")],
             handler=lambda state="open": _github_list_issues(state)),
        Tool(name="github_create_pr", description="Create a pull request.", category="github",
             governance_level="L2",
             params=[ToolParam("title", "string", "PR title"), ToolParam("body", "string", "PR body"),
                     ToolParam("branch", "string", "Source branch", required=False, default="")],
             handler=_github_create_pr),
        Tool(name="github_list_prs", description="List open pull requests.", category="github",
             params=[], handler=_github_list_prs),
    ]
