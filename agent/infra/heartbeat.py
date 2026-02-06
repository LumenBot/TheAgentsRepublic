"""
Heartbeat Runner for The Constituent v5.0
============================================
Timer-based scheduler that:
1. Runs due cron jobs (from data/cron_jobs.json)
2. Sends heartbeat prompts to the engine (from HEARTBEAT.md)
Inspired by OpenClaw heartbeat-runner.ts + cron service.
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Optional

from ..tools.cron_tool import _get_due_jobs, mark_job_run

logger = logging.getLogger("TheConstituent.Heartbeat")

# Default heartbeat interval
DEFAULT_HEARTBEAT_INTERVAL = 600  # 10 minutes
QUIET_HOURS_START = 23  # UTC
QUIET_HOURS_END = 7    # UTC


class HeartbeatRunner:
    """
    Runs the engine's heartbeat cycle on a timer.

    Each tick:
    1. Check cron jobs → run any that are due
    2. Run heartbeat (reads HEARTBEAT.md via engine)
    3. Schedule next tick
    """

    def __init__(self, engine, interval_seconds: int = DEFAULT_HEARTBEAT_INTERVAL):
        self.engine = engine
        self.interval = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._tick_count = 0

    async def start(self):
        """Start the heartbeat loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Heartbeat started (every {self.interval}s)")

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
        """Single heartbeat tick."""
        self._tick_count += 1
        start = time.time()

        # Check quiet hours
        hour = datetime.now(timezone.utc).hour
        if QUIET_HOURS_START <= hour or hour < QUIET_HOURS_END:
            logger.debug(f"Heartbeat #{self._tick_count}: quiet hours, skipping")
            return

        logger.info(f"━━━ Heartbeat #{self._tick_count} START ━━━")

        # 1. Run due cron jobs
        due_jobs = _get_due_jobs()
        for job in due_jobs:
            job_name = job["name"]
            task = job["task"]
            logger.info(f"  Cron job due: {job_name} → {task[:80]}")

            try:
                # Run via engine heartbeat with the specific section
                result = self.engine.run_heartbeat(section=job_name)
                status = result.get("status", "error")
                mark_job_run(job_name, status)
                logger.info(f"  Cron job {job_name}: {status}")
            except Exception as e:
                mark_job_run(job_name, f"error: {e}")
                logger.error(f"  Cron job {job_name} failed: {e}")

        # 2. Run general heartbeat (if no specific jobs ran)
        if not due_jobs:
            result = self.engine.run_heartbeat()
            status = result.get("status", "?")
            response = result.get("response", "")[:100]
            logger.info(f"  Heartbeat: {status} → {response}")

        duration_ms = int((time.time() - start) * 1000)
        logger.info(f"━━━ Heartbeat #{self._tick_count} END [{duration_ms}ms] ━━━")

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
        }
