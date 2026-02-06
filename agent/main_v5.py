"""
The Constituent v5.0 — Main Entry Point
==========================================
Wires up: Engine + Heartbeat Runner + Telegram Bot
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from .engine import Engine
from .infra.heartbeat import HeartbeatRunner
from .config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TheConstituent.Main")


async def main():
    logger.info("=" * 60)
    logger.info("  The Constituent v5.0 — Starting")
    logger.info("  Tool-based engine + OpenClaw-inspired architecture")
    logger.info("=" * 60)

    # 1. Initialize Engine
    workspace = Path(".")
    engine = Engine(workspace_dir=workspace)
    init_result = engine.initialize()
    logger.info(f"Engine: {init_result}")

    # 2. Initialize Heartbeat Runner
    heartbeat = HeartbeatRunner(engine, interval_seconds=600)  # 10 min

    # 3. Initialize Telegram Bot (wired to engine)
    telegram = None
    if settings.api.TELEGRAM_ENABLED and settings.api.TELEGRAM_BOT_TOKEN:
        try:
            from .telegram_bot import TelegramBotHandler
            telegram = TelegramBotHandler(agent=engine)
            logger.info("Telegram bot configured")
        except ImportError as e:
            logger.warning(f"Telegram bot not available: {e}")
    else:
        logger.warning("Telegram disabled (no token or TELEGRAM_ENABLED=false)")

    # 4. Shutdown handler
    stop_event = asyncio.Event()

    def shutdown(sig=None, frame=None):
        logger.info("Shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 5. Start services
    try:
        tasks = []

        # Start heartbeat
        await heartbeat.start()

        # Start telegram
        if telegram:
            tasks.append(asyncio.create_task(telegram.run_async()))

        logger.info("All services started. Waiting for shutdown signal...")

        # Wait for shutdown
        await stop_event.wait()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        # Cleanup
        await heartbeat.stop()
        engine.save_state()
        logger.info("Shutdown complete")


def run():
    """Entry point for `python -m agent`."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
