"""
The Constituent — Main Entry Point v3.0
=========================================
Constitutional Sprint Mode.

Orchestrates:
- Agent initialization with memory recovery
- Telegram bot (iPhone interface)
- Background tasks: auto-save, checkpoints, git sync
- Autonomy Loop: observe, think, act
- Daily tasks: metrics update, profile refresh (23:00 UTC)
- Graceful shutdown with state preservation

Usage:
    python -m agent.main_v3
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime, timezone

from .config.settings import settings
from .constituent import TheConstituent
from .memory_manager import MemoryManager
from .git_sync import GitSync
from .telegram_bot import TelegramBotHandler, TELEGRAM_AVAILABLE
from .autonomy_loop import AutonomyLoop

# ============================================================================
# Logging setup
# ============================================================================

def setup_logging():
    log_dir = "data"
    os.makedirs(log_dir, exist_ok=True)

    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"{log_dir}/agent.log", encoding='utf-8')
        ]
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

    return logging.getLogger("TheConstituent.Main")


# ============================================================================
# Background task scheduler
# ============================================================================

class BackgroundScheduler:
    """
    Periodic tasks alongside the Telegram bot:
    - Working memory save (every 60s)
    - Checkpoint creation (every 5min)
    - Git commit (every 15min)
    - Git push (every 1h)
    - Database backup (every 30min)
    - Daily metrics + profile update (23:00 UTC) — NEW v3.0
    """

    def __init__(self, agent: TheConstituent, git_sync: GitSync, notify_fn=None):
        self.agent = agent
        self.git_sync = git_sync
        self.notify_fn = notify_fn
        self._running = False
        self._tasks = []

    async def start(self):
        self._running = True
        self._tasks = [
            asyncio.create_task(self._working_memory_loop()),
            asyncio.create_task(self._checkpoint_loop()),
            asyncio.create_task(self._git_commit_loop()),
            asyncio.create_task(self._git_push_loop()),
            asyncio.create_task(self._db_backup_loop()),
            asyncio.create_task(self._daily_metrics_loop()),  # NEW v3.0
        ]
        logging.getLogger("TheConstituent.Scheduler").info(
            "Background scheduler started (6 tasks, including daily metrics)"
        )

    async def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _working_memory_loop(self):
        while self._running:
            try:
                await asyncio.sleep(settings.WORKING_MEMORY_SAVE_INTERVAL)
                self.agent.memory.save_working_memory()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"Working memory save failed: {e}")

    async def _checkpoint_loop(self):
        while self._running:
            try:
                await asyncio.sleep(settings.CHECKPOINT_INTERVAL)
                self.agent.memory.create_checkpoint(trigger="periodic")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"Checkpoint failed: {e}")

    async def _git_commit_loop(self):
        while self._running:
            try:
                await asyncio.sleep(settings.GIT_COMMIT_INTERVAL)
                self.git_sync.auto_commit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"Git commit failed: {e}")

    async def _git_push_loop(self):
        while self._running:
            try:
                await asyncio.sleep(settings.GIT_PUSH_INTERVAL)
                self.git_sync.push()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"Git push failed: {e}")

    async def _db_backup_loop(self):
        while self._running:
            try:
                await asyncio.sleep(1800)
                self.agent.memory.backup_database()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"DB backup failed: {e}")

    async def _daily_metrics_loop(self):
        """
        Daily task: Update metrics file + profile at 23:00 UTC.
        Also checks at startup if today's update was missed.
        """
        sched_logger = logging.getLogger("TheConstituent.DailyMetrics")

        while self._running:
            try:
                now = datetime.now(timezone.utc)

                # Calculate seconds until next 23:00 UTC
                target_hour = 23
                if now.hour >= target_hour:
                    # Already past 23:00 — next is tomorrow
                    next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                    next_run += __import__('datetime').timedelta(days=1)
                else:
                    next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)

                wait_seconds = (next_run - now).total_seconds()
                sched_logger.info(f"📊 Daily metrics update in {wait_seconds/3600:.1f}h (at {next_run.strftime('%H:%M UTC')})")

                await asyncio.sleep(wait_seconds)

                # Execute daily update
                sched_logger.info("📊 Running daily metrics + profile update...")

                try:
                    # Update metrics markdown
                    self.agent.metrics.update_metrics_file()

                    # Update public profile
                    self.agent.profile.update_profile()

                    # Git commit the updates
                    self.git_sync.auto_commit(f"daily metrics: sprint day {self.agent.metrics.get_sprint_day()}")

                    # Notify operator
                    summary = self.agent.metrics.get_daily_summary_text()
                    if self.notify_fn:
                        await self.notify_fn(f"📊 **End of Day Report**\n\n{summary}")

                    sched_logger.info("📊 Daily update complete")

                except Exception as e:
                    sched_logger.error(f"Daily update failed: {e}")
                    if self.notify_fn:
                        await self.notify_fn(f"❌ Daily metrics update failed: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                sched_logger.error(f"Daily metrics loop error: {e}")
                await asyncio.sleep(3600)  # Retry in 1h on error


# ============================================================================
# Main orchestrator
# ============================================================================

async def run():
    logger = setup_logging()

    sprint_day = __import__('agent.metrics_tracker', fromlist=['MetricsTracker']).MetricsTracker().get_sprint_day()

    print(f"""
    ╔══════════════════════════════════════════════╗
    ║         THE CONSTITUENT v3.0                 ║
    ║     AI Agent for The Agents Republic         ║
    ║                                              ║
    ║     🚨 CONSTITUTIONAL SPRINT MODE            ║
    ║     📊 Sprint Day: {sprint_day:>2}/21                    ║
    ║     📱 Telegram Interface Ready              ║
    ║     🔄 Git Auto-Sync Enabled                 ║
    ║     🧠 Autonomy Loop Active                  ║
    ║     📈 Metrics Tracking ON                   ║
    ╚══════════════════════════════════════════════╝
    """)

    logger.info(f"Starting v3.0 at {datetime.utcnow().isoformat()} — Sprint Day {sprint_day}/21")

    # --- Initialize Memory ---
    memory = MemoryManager(
        db_path=settings.DB_PATH,
        working_memory_path="data/working_memory.json",
        knowledge_dir="memory/knowledge"
    )

    # --- Initialize Agent ---
    try:
        agent = TheConstituent(memory_manager=memory)
        recovery_status = agent.initialize()

        logger.info(f"Recovery status: {recovery_status}")

        if recovery_status.get("working_memory_recovered"):
            logger.info(f"✅ Resumed from: {recovery_status.get('last_known_state')}")
        elif recovery_status.get("checkpoint_recovered"):
            logger.info(f"✅ Restored from checkpoint: {recovery_status.get('last_known_state')}")
        else:
            logger.info("🆕 Fresh start")

    except ValueError as e:
        logger.error(f"❌ Initialization failed: {e}")
        logger.error("Make sure your .env file is configured (see .env.example)")
        sys.exit(1)

    # --- Initialize Git Sync ---
    git_sync = GitSync(repo_path=".")

    # --- Initialize Telegram Bot ---
    telegram_bot = None
    notify_fn = None

    if TELEGRAM_AVAILABLE and settings.api.TELEGRAM_BOT_TOKEN:
        try:
            telegram_bot = TelegramBotHandler(agent=agent)
            telegram_bot.build_application()
            logger.info("✅ Telegram bot initialized")

            operator_chat_id = settings.api.OPERATOR_TELEGRAM_CHAT_ID
            if operator_chat_id:
                bot_instance = telegram_bot.application.bot
                async def send_telegram_notification(text: str):
                    try:
                        if len(text) > 4000:
                            text = text[:4000] + "\n... (truncated)"
                        await bot_instance.send_message(
                            chat_id=int(operator_chat_id),
                            text=text
                        )
                    except Exception as e:
                        logging.getLogger("TheConstituent.Notify").error(f"Telegram notification failed: {e}")
                notify_fn = send_telegram_notification

        except Exception as e:
            logger.error(f"❌ Telegram bot failed: {e}")
            logger.info("Running without Telegram")
    else:
        logger.info("Running without Telegram interface")

    # --- Initialize Background Scheduler (with notify_fn for daily report) ---
    scheduler = BackgroundScheduler(agent, git_sync, notify_fn=notify_fn)

    # --- Initialize Autonomy Loop ---
    autonomy = AutonomyLoop(agent=agent, notify_fn=notify_fn)

    if telegram_bot:
        telegram_bot.autonomy_loop = autonomy

    # --- Graceful shutdown handler ---
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # --- Start everything ---
    try:
        await scheduler.start()
        await autonomy.start()

        agent.memory.create_checkpoint(trigger="startup")
        git_sync.auto_commit("startup: agent v3.0 initialized — Constitutional Sprint Mode")

        # Generate initial metrics + profile
        agent.metrics.update_metrics_file()
        agent.profile.update_profile()

        if telegram_bot:
            logger.info("🚀 Agent is LIVE! Sprint Mode active.")

            app = telegram_bot.application
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)

            # Notify operator
            if notify_fn:
                await notify_fn(
                    f"🚀 **The Constituent v3.0 is LIVE**\n\n"
                    f"🚨 Constitutional Sprint Mode ACTIVE\n"
                    f"📊 Sprint Day: {sprint_day}/21\n"
                    f"📈 Metrics tracking ON\n\n"
                    f"Commands: /metrics /profile /ratio /status"
                )

            await shutdown_event.wait()

            await app.updater.stop()
            await app.stop()
            await app.shutdown()
        else:
            logger.info("🚀 Agent running (no Telegram). Press Ctrl+C to stop.")
            await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Fatal error: {e}")

    finally:
        logger.info("Shutting down...")
        await autonomy.stop()
        await scheduler.stop()

        # Final save + metrics update
        agent.save_state()
        agent.metrics.update_metrics_file()
        agent.profile.update_profile()

        git_sync.commit_and_push("shutdown: v3.0 graceful shutdown + final metrics")

        logger.info("✅ Shutdown complete. All state saved.")
        logger.info(f"   Sprint Day: {agent.metrics.get_sprint_day()}/21")
        logger.info(f"   Checkpoints: {agent.memory.working.checkpoint_count}")


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n👋 The Constituent signing off...")


if __name__ == "__main__":
    main()
