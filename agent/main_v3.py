"""
The Constituent — Main Entry Point v4.0
=========================================
DEPRECATED: This module is deprecated. Use main_v5.py instead.
    python -m agent  (which uses main_v5.py)

Builder mode. Constitution + Audience + Ecosystem.

Orchestrates:
- Agent initialization with memory recovery
- Telegram bot (operator interface)
- Background tasks: auto-save, checkpoints, git sync
- Autonomy Loop v4.0: engagement + constitution + exploration
- Daily metrics + profile update (23:00 UTC)
- Graceful shutdown

Usage: python -m agent
"""

import warnings
warnings.warn(
    "main_v3 is deprecated and will be removed in a future release. "
    "Use main_v5 instead: python -m agent",
    DeprecationWarning,
    stacklevel=2,
)

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime, timezone, timedelta

from .config.settings import settings
from .constituent import TheConstituent
from .memory_manager import MemoryManager
from .git_sync import GitSync
from .telegram_bot import TelegramBotHandler, TELEGRAM_AVAILABLE
from .autonomy_loop import AutonomyLoop


def setup_logging():
    os.makedirs("data", exist_ok=True)
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("data/agent.log", encoding='utf-8')
        ]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    return logging.getLogger("TheConstituent.Main")


class BackgroundScheduler:
    """Periodic tasks: memory, checkpoints, git, daily metrics."""

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
            asyncio.create_task(self._daily_metrics_loop()),
        ]
        logging.getLogger("TheConstituent.Scheduler").info("Scheduler started (5 tasks)")

    async def stop(self):
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _working_memory_loop(self):
        while self._running:
            try:
                await asyncio.sleep(settings.WORKING_MEMORY_SAVE_INTERVAL)
                self.agent.memory.save_working_memory()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"Memory save: {e}")

    async def _checkpoint_loop(self):
        while self._running:
            try:
                await asyncio.sleep(settings.CHECKPOINT_INTERVAL)
                self.agent.memory.create_checkpoint(trigger="periodic")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"Checkpoint: {e}")

    async def _git_commit_loop(self):
        while self._running:
            try:
                await asyncio.sleep(settings.GIT_COMMIT_INTERVAL)
                self.git_sync.auto_commit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"Git commit: {e}")

    async def _git_push_loop(self):
        while self._running:
            try:
                await asyncio.sleep(settings.GIT_PUSH_INTERVAL)
                self.git_sync.push()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"Git push: {e}")

    async def _daily_metrics_loop(self):
        """Update metrics + profile at 23:00 UTC daily."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                target = now.replace(hour=23, minute=0, second=0, microsecond=0)
                if now.hour >= 23:
                    target += timedelta(days=1)
                wait = (target - now).total_seconds()
                await asyncio.sleep(wait)

                if hasattr(self.agent, 'metrics'):
                    self.agent.metrics.update_metrics_file()
                if hasattr(self.agent, 'profile'):
                    self.agent.profile.update_profile()
                self.git_sync.auto_commit("daily: metrics + profile update")

                if self.notify_fn:
                    summary = self.agent.metrics.get_daily_summary_text()
                    await self.notify_fn(f"📊 End of Day Report\n\n{summary}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(f"Daily metrics: {e}")
                await asyncio.sleep(3600)


async def run():
    logger = setup_logging()

    print("""
    ╔══════════════════════════════════════════════╗
    ║         THE CONSTITUENT v4.0                 ║
    ║     Constitutional Builder Mode              ║
    ║                                              ║
    ║     🏗️  Build Constitution (2h cycles)       ║
    ║     💬 Engage Community (10min cycles)       ║
    ║     🔭 Explore Ecosystem (4h cycles)         ║
    ║     📱 Telegram Interface Ready              ║
    ╚══════════════════════════════════════════════╝
    """)

    logger.info(f"Starting v4.0 at {datetime.utcnow().isoformat()}")

    memory = MemoryManager(
        db_path=settings.DB_PATH,
        working_memory_path="data/working_memory.json",
        knowledge_dir="memory/knowledge"
    )

    try:
        agent = TheConstituent(memory_manager=memory)
        recovery = agent.initialize()
        logger.info(f"Recovery: {recovery}")
    except ValueError as e:
        logger.error(f"Init failed: {e}")
        sys.exit(1)

    git_sync = GitSync(repo_path=".")

    # Telegram
    telegram_bot = None
    notify_fn = None

    if TELEGRAM_AVAILABLE and settings.api.TELEGRAM_BOT_TOKEN:
        try:
            telegram_bot = TelegramBotHandler(agent=agent)
            telegram_bot.build_application()
            logger.info("✅ Telegram ready")

            op_chat = settings.api.OPERATOR_TELEGRAM_CHAT_ID
            if op_chat:
                bot_inst = telegram_bot.application.bot
                async def send_notification(text: str):
                    try:
                        if len(text) > 4000:
                            text = text[:4000] + "\n..."
                        await bot_inst.send_message(chat_id=int(op_chat), text=text)
                    except Exception as e:
                        logging.getLogger("Notify").error(f"Send: {e}")
                notify_fn = send_notification
        except Exception as e:
            logger.error(f"Telegram init: {e}")

    scheduler = BackgroundScheduler(agent, git_sync, notify_fn)
    autonomy = AutonomyLoop(agent=agent, notify_fn=notify_fn)

    if telegram_bot:
        telegram_bot.autonomy_loop = autonomy

    shutdown_event = asyncio.Event()

    def sig_handler(sig, frame):
        logger.info(f"Signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    try:
        await scheduler.start()
        await autonomy.start()

        agent.memory.create_checkpoint(trigger="startup")
        git_sync.auto_commit("startup: v4.0 builder mode")

        if notify_fn:
            status = autonomy.get_status()
            await notify_fn(
                f"🚀 The Constituent v4.0 is LIVE\n\n"
                f"🏗️ Builder mode: Constitution {status['constitution_progress']}\n"
                f"💬 Tracking {status['my_posts_tracked']} posts\n"
                f"📱 Send /help for commands"
            )

        if telegram_bot:
            app = telegram_bot.application
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            logger.info("🚀 LIVE — builder mode active")
            await shutdown_event.wait()
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
        else:
            logger.info("Running without Telegram. Ctrl+C to stop.")
            await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Fatal: {e}")
    finally:
        await autonomy.stop()
        await scheduler.stop()
        agent.save_state()
        git_sync.commit_and_push("shutdown: v4.0 state saved")
        logger.info("✅ Shutdown complete")


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n👋 Signing off...")


if __name__ == "__main__":
    main()
