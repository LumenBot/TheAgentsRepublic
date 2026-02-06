"""
Heartbeat Runner for The Constituent v5.1
============================================
Timer-based scheduler that:
1. Runs due cron jobs (from data/cron_jobs.json)
2. Sends heartbeat prompts to the engine (from HEARTBEAT.md)
Inspired by OpenClaw heartbeat-runner.ts + cron service.

v5.1 changes:
- Uses interval from settings.rate_limits (default 1200s / 20min)
- Limits to ONE cron job per tick to prevent token explosion
- Logs budget status after each tick
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Optional

from ..tools.cron_tool import _get_due_jobs, mark_job_run
from ..config.settings import settings

logger = logging.getLogger("TheConstituent.Heartbeat")


class HeartbeatRunner:
    """
    Runs the engine's heartbeat cycle on a timer.

    Each tick:
    1. Check cron jobs → run ONE that is due (most overdue first)
    2. If no cron jobs, run general heartbeat
    3. Schedule next tick

    v5.1: Only ONE action per tick to control token usage.
    """

    def __init__(self, engine, interval_seconds: int = None):
        self.engine = engine
        self.interval = interval_seconds or settings.rate_limits.HEARTBEAT_INTERVAL
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._tick_count = 0
        self._quiet_start = settings.rate_limits.QUIET_HOURS_START
        self._quiet_end = settings.rate_limits.QUIET_HOURS_END

    async def start(self):
        """Start the heartbeat loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Heartbeat started (every {self.interval}s / {self.interval//60}min)")

    async def stop(self):
        """Stop the heartbeat loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat stopped")

    async def _loop(self):
        """Main heartbeat loop."""
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Heartbeat tick error: {e}")

            await asyncio.sleep(self.interval)

    async def _tick(self):
        """Single heartbeat tick — ONE action only."""
        self._tick_count += 1
        start = time.time()

        # Check quiet hours
        hour = datetime.now(timezone.utc).hour
        if self._quiet_start <= hour or hour < self._quiet_end:
            logger.debug(f"Heartbeat #{self._tick_count}: quiet hours, skipping")
            return

        logger.info(f"━━━ Heartbeat #{self._tick_count} START ━━━")

        # 1. Check for due cron jobs — run only the FIRST one (most overdue)
        due_jobs = _get_due_jobs()
        if due_jobs:
            # Sort by next_run_at to get most overdue first
            due_jobs.sort(key=lambda j: j.get("next_run_at", 0))
            job = due_jobs[0]  # Only run ONE job per tick
            job_name = job["name"]
            task = job["task"]
            logger.info(f"  Cron job due: {job_name} → {task[:80]} "
                        f"({len(due_jobs)} total due, running 1)")

            try:
                result = self.engine.run_heartbeat(section=job_name)
                status = result.get("status", "error")
                mark_job_run(job_name, status)
                logger.info(f"  Cron job {job_name}: {status}")
            except Exception as e:
                mark_job_run(job_name, f"error: {e}")
                logger.error(f"  Cron job {job_name} failed: {e}")
        else:
            # 2. No cron jobs due — run general heartbeat
            result = self.engine.run_heartbeat()
            status = result.get("status", "?")
            response = result.get("response", "")[:100]
            logger.info(f"  Heartbeat: {status} → {response}")

        duration_ms = int((time.time() - start) * 1000)

        # Log budget status
        budget = self.engine.get_budget_status()
        logger.info(f"━━━ Heartbeat #{self._tick_count} END [{duration_ms}ms] "
                    f"| API: {budget['api_calls_today']}/{budget['max_per_day']}/day ━━━")

    async def run_once(self, section: str = None):
        """Run a single heartbeat tick (for testing or manual trigger)."""
        if section:
            result = self.engine.run_heartbeat(section=section)
        else:
            await self._tick()
            result = {"status": "ok", "tick": self._tick_count}
        return result

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "interval_seconds": self.interval,
            "tick_count": self._tick_count,
            "budget": self.engine.get_budget_status(),
        }
