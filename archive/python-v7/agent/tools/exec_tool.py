"""
Exec Tool for The Constituent v5.0
====================================
Sandboxed shell command execution.
Inspired by OpenClaw exec tool with safety guardrails.
"""

import subprocess
import logging
from pathlib import Path
from typing import List

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Exec")

# Safety: blocked commands
BLOCKED_PATTERNS = [
    "rm -rf /", "rm -rf ~", "sudo", "chmod 777", "mkfs",
    "dd if=", "> /dev/", ":(){ :|:", "fork bomb",
    "curl.*| sh", "wget.*| sh", "eval ", "exec(",
]

MAX_OUTPUT = 10000
DEFAULT_TIMEOUT = 30


def _exec(workspace: Path, command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Execute a shell command safely."""
    # Safety check
    cmd_lower = command.lower()
    for blocked in BLOCKED_PATTERNS:
        if blocked in cmd_lower:
            return f"Error: blocked command pattern: '{blocked}'"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(workspace),
            env=None,  # Inherit environment
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n--- stderr ---\n" + result.stderr) if output else result.stderr

        if not output.strip():
            output = f"(command completed with exit code {result.returncode})"

        if len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT] + "\n...(truncated)"

        if result.returncode != 0:
            output = f"Exit code: {result.returncode}\n{output}"

        return output

    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


def get_tools(workspace_dir: Path) -> List[Tool]:
    """Register exec tools."""
    ws = Path(workspace_dir).resolve()

    return [
        Tool(
            name="exec",
            description="Execute a shell command in the workspace directory. Use for git, python, curl, etc.",
            category="system",
            params=[
                ToolParam("command", "string", "Shell command to execute"),
                ToolParam("timeout", "integer", "Timeout in seconds", required=False, default=30),
            ],
            handler=lambda command, timeout=30: _exec(ws, command, int(timeout)),
        ),
    ]
