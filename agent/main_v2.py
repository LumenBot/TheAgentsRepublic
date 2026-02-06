"""
The Constituent — Main Entry Point v2.3
=========================================
Phase 2B: Autonomous agent with background intelligence.

Orchestrates:
- Agent initialization with memory recovery
- Telegram bot (iPhone interface)
- Background tasks: auto-save, checkpoints, git sync
- AUTONOMY LOOP: observe, think, act (NEW)
- Graceful shutdown with state preservation

Usage:
    python -m agent.main_v2
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime

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
    """Configure logging to console + file."""
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

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

    return logging.getLogger("TheConstituent.Main")


# ============================================================================
# Background task scheduler
# ============================================================================

class BackgroundScheduler:
    """
    Runs periodic tasks alongside the Telegram bot:
    - Working memory save (every 60s)
    - Checkpoint creation (every 5min)
    - Git commit (every 15min)
    - Git push (every 1h)
    - Database backup (every 30min)
    """

    def __init__(self, agent: TheConstituent, git_sync: GitSync):
        self.agent = agent
        self.git_sync = git_sync
        self._running = False
        self._tasks = []

    async def start(self):
        """Start all background tasks."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._working_memory_loop()),
            asyncio.create_task(self._checkpoint_loop()),
            asyncio.create_task(self._git_commit_loop()),
            asyncio.create_task(self._git_push_loop()),
            asyncio.create_task(self._db_backup_loop()),
        ]
        logging.getLogger("TheConstituent.Scheduler").info(
            "Background scheduler started (5 tasks)"
        )

    async def stop(self):
        """Stop all background tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _working_memory_loop(self):
        """Save working memory every 60 seconds."""
        while self._running:
            try:
                await asyncio.sleep(settings.WORKING_MEMORY_SAVE_INTERVAL)
                self.agent.memory.save_working_memory()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(
                    f"Working memory save failed: {e}"
                )

    async def _checkpoint_loop(self):
        """Create checkpoint every 5 minutes."""
        while self._running:
            try:
                await asyncio.sleep(settings.CHECKPOINT_INTERVAL)
                self.agent.memory.create_checkpoint(trigger="periodic")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(
                    f"Checkpoint failed: {e}"
                )

    async def _git_commit_loop(self):
        """Git commit every 15 minutes."""
        while self._running:
            try:
                await asyncio.sleep(settings.GIT_COMMIT_INTERVAL)
                self.git_sync.auto_commit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(
                    f"Git commit failed: {e}"
                )

    async def _git_push_loop(self):
        """Git push every hour."""
        while self._running:
            try:
                await asyncio.sleep(settings.GIT_PUSH_INTERVAL)
                self.git_sync.push()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(
                    f"Git push failed: {e}"
                )

    async def _db_backup_loop(self):
        """Database backup every 30 minutes."""
        while self._running:
            try:
                await asyncio.sleep(1800)
                self.agent.memory.backup_database()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.getLogger("TheConstituent.Scheduler").error(
                    f"DB backup failed: {e}"
                )


# ============================================================================
# Main orchestrator
# ============================================================================

async def run():
    """Main async entry point."""
    logger = setup_logging()

    # Banner
    print("""
    ╔══════════════════════════════════════════════╗
    ║         THE CONSTITUENT v2.3                 ║
    ║     AI Agent for The Agents Republic         ║
    ║                                              ║
    ║     🛡️  Resilient Memory System Active       ║
    ║     📱 Telegram Interface Ready              ║
    ║     🔄 Git Auto-Sync Enabled                 ║
    ║     🧠 Autonomy Loop Active                  ║
    ╚══════════════════════════════════════════════╝
    """)

    logger.info(f"Starting at {datetime.utcnow().isoformat()}")

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

    # --- Initialize Background Scheduler ---
    scheduler = BackgroundScheduler(agent, git_sync)

    # --- Initialize Telegram Bot ---
    telegram_bot = None
    notify_fn = None

    if TELEGRAM_AVAILABLE and settings.api.TELEGRAM_BOT_TOKEN:
        try:
            telegram_bot = TelegramBotHandler(agent=agent)
            telegram_bot.build_application()
            logger.info("✅ Telegram bot initialized")

            # Create notification function for autonomy loop
            operator_chat_id = settings.api.OPERATOR_TELEGRAM_CHAT_ID
            if operator_chat_id:
                bot_instance = telegram_bot.application.bot
                async def send_telegram_notification(text: str):
                    """Send notification to operator via Telegram."""
                    try:
                        # Truncate if too long
                        if len(text) > 4000:
                            text = text[:4000] + "\n... (truncated)"
                        await bot_instance.send_message(
                            chat_id=int(operator_chat_id),
                            text=text
                        )
                    except Exception as e:
                        logging.getLogger("TheConstituent.Notify").error(
                            f"Telegram notification failed: {e}"
                        )
                notify_fn = send_telegram_notification

        except Exception as e:
            logger.error(f"❌ Telegram bot failed to initialize: {e}")
            logger.info("Agent will run without Telegram interface")
    else:
        if not TELEGRAM_AVAILABLE:
            logger.warning("python-telegram-bot not installed")
        if not settings.api.TELEGRAM_BOT_TOKEN:
            logger.warning("TELEGRAM_BOT_TOKEN not set")
        logger.info("Running without Telegram interface")

    # --- Initialize Autonomy Loop ---
    autonomy = AutonomyLoop(agent=agent, notify_fn=notify_fn)

    # Store autonomy reference on the bot for Telegram commands
    if telegram_bot:
        telegram_bot.autonomy_loop = autonomy

    # --- Graceful shutdown handler ---
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # --- Start everything ---
    try:
        # Start background scheduler
        await scheduler.start()

        # Start autonomy loop
        await autonomy.start()

        # Initial checkpoint
        agent.memory.create_checkpoint(trigger="startup")

        # Initial git commit
        git_sync.auto_commit("startup: agent v2.3 initialized with autonomy loop")

        if telegram_bot:
            # Run Telegram bot (this blocks until shutdown)
            logger.info("🚀 Agent is live! Telegram bot polling + Autonomy Loop active")

            # Start the bot in polling mode
            app = telegram_bot.application
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)

            # Wait for shutdown signal
            await shutdown_event.wait()

            # Cleanup telegram
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
        else:
            # No Telegram — just run background tasks and wait
            logger.info("🚀 Agent running (no Telegram). Press Ctrl+C to stop.")
            await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Fatal error: {e}")

    finally:
        # --- Graceful shutdown ---
        logger.info("Shutting down gracefully...")

        # Stop autonomy loop
        await autonomy.stop()

        # Stop background tasks
        await scheduler.stop()

        # Final state save
        agent.save_state()

        # Final git sync
        git_sync.commit_and_push("shutdown: graceful shutdown state save")

        logger.info("✅ Shutdown complete. All state saved.")
        logger.info(f"   Checkpoints: {agent.memory.working.checkpoint_count}")
        logger.info(f"   Git commits: {git_sync._commit_count}")


def main():
    """Sync entry point."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n👋 The Constituent signing off...")


if __name__ == "__main__":
    main()
