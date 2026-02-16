"""
Cron Tools for The Constituent v5.0
=====================================
Persistent job scheduler. Add, list, remove scheduled tasks.
Inspired by OpenClaw src/cron/service.ts.
"""

import json
import time
import logging
from pathlib import Path
from typing import List, Dict

from ..tool_registry import Tool, ToolParam

logger = logging.getLogger("TheConstituent.Tools.Cron")

CRON_FILE = Path("data/cron_jobs.json")


def _load_jobs() -> List[Dict]:
    if CRON_FILE.exists():
        try:
            return json.loads(CRON_FILE.read_text())
        except Exception:
            return []
    return []


def _save_jobs(jobs: List[Dict]):
    CRON_FILE.parent.mkdir(parents=True, exist_ok=True)
    CRON_FILE.write_text(json.dumps(jobs, indent=2))


def _cron_add(name: str, every_minutes: int, task: str) -> str:
    jobs = _load_jobs()
    # Check for duplicate
    for j in jobs:
        if j["name"] == name:
            return f"Error: job '{name}' already exists. Remove it first."
    job = {
        "id": f"job_{int(time.time())}",
        "name": name,
        "every_minutes": every_minutes,
        "task": task,
        "enabled": True,
        "created_at": time.time(),
        "last_run_at": None,
        "next_run_at": time.time() + (every_minutes * 60),
        "run_count": 0,
        "last_status": None,
    }
    jobs.append(job)
    _save_jobs(jobs)
    return f"Added job '{name}': every {every_minutes}min → {task[:100]}"


def _cron_list() -> str:
    jobs = _load_jobs()
    if not jobs:
        return "No cron jobs configured."
    lines = ["Cron jobs:"]
    for j in jobs:
        status = "✅" if j.get("enabled") else "⏸️"
        last = j.get("last_status", "never")
        lines.append(
            f"  {status} {j['name']} (every {j['every_minutes']}min) "
            f"runs={j.get('run_count', 0)} last={last}"
        )
    return "\n".join(lines)


def _cron_remove(name: str) -> str:
    jobs = _load_jobs()
    new_jobs = [j for j in jobs if j["name"] != name]
    if len(new_jobs) == len(jobs):
        return f"Error: job '{name}' not found"
    _save_jobs(new_jobs)
    return f"Removed job '{name}'"


def _cron_toggle(name: str, enabled: bool) -> str:
    jobs = _load_jobs()
    for j in jobs:
        if j["name"] == name:
            j["enabled"] = enabled
            _save_jobs(jobs)
            return f"Job '{name}' {'enabled' if enabled else 'disabled'}"
    return f"Error: job '{name}' not found"


def _get_due_jobs() -> List[Dict]:
    """Get jobs that are due to run now."""
    jobs = _load_jobs()
    now = time.time()
    due = []
    for j in jobs:
        if not j.get("enabled"):
            continue
        next_run = j.get("next_run_at", 0)
        if now >= next_run:
            due.append(j)
    return due


def mark_job_run(name: str, status: str = "ok"):
    """Mark a job as just run (called by heartbeat runner)."""
    jobs = _load_jobs()
    for j in jobs:
        if j["name"] == name:
            j["last_run_at"] = time.time()
            j["next_run_at"] = time.time() + (j["every_minutes"] * 60)
            j["run_count"] = j.get("run_count", 0) + 1
            j["last_status"] = status
            break
    _save_jobs(jobs)


def get_tools() -> List[Tool]:
    return [
        Tool(name="cron_add", description="Add a scheduled recurring task.", category="cron",
             params=[
                 ToolParam("name", "string", "Job name (unique)"),
                 ToolParam("every_minutes", "integer", "Run every N minutes"),
                 ToolParam("task", "string", "Task description (what to do)"),
             ],
             handler=_cron_add),
        Tool(name="cron_list", description="List all scheduled jobs.", category="cron",
             params=[], handler=_cron_list),
        Tool(name="cron_remove", description="Remove a scheduled job.", category="cron",
             params=[ToolParam("name", "string", "Job name to remove")],
             handler=_cron_remove),
        Tool(name="cron_enable", description="Enable a job.", category="cron",
             params=[ToolParam("name", "string", "Job name")],
             handler=lambda name: _cron_toggle(name, True)),
        Tool(name="cron_disable", description="Disable a job.", category="cron",
             params=[ToolParam("name", "string", "Job name")],
             handler=lambda name: _cron_toggle(name, False)),
    ]
