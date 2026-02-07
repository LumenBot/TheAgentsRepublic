"""
The Constituent Agent v5.0 — Configuration
=============================================
All settings from environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class RateLimitSettings:
    """Rate limiting and budget protection (v5.3 — rebalanced)."""
    # Claude API limits — v5.3: raised from 5/30/30/500 (too restrictive, 100% failure rate)
    MAX_TOOL_ROUNDS_PER_HEARTBEAT: int = 10  # v5.2=5 too low, agent couldn't complete any task
    MAX_HEARTBEAT_DURATION_SECONDS: int = 45  # v5.2=30 too tight for multi-step workflows
    MAX_API_CALLS_PER_HOUR: int = 50  # v5.2=30 exhausted after 1 hour
    MAX_API_CALLS_PER_DAY: int = 650  # ~$50/month at Sonnet rates (3 heartbeats/hr × 10 rounds × 24h ≈ 600)
    BUDGET_MONTHLY_USD: float = 50.0

    # Heartbeat
    HEARTBEAT_INTERVAL: int = 1200  # 20 min instead of 10 min
    QUIET_HOURS_START: int = 23  # UTC
    QUIET_HOURS_END: int = 7    # UTC

    # Twitter
    TWITTER_ENABLED: bool = True
    TWITTER_REQUIRE_WRITE_ACCESS: bool = False  # Don't crash if no write access
    TWITTER_FALLBACK_ON_ERROR: str = "disable"  # "disable" or "queue"


@dataclass
class AgentSettings:
    """Core agent behavior configuration."""
    BOT_NAME: str = "The Constituent"
    BOT_HANDLE_X: str = "@TheConstituent_"
    POSTS_PER_DAY_MAX: int = 7
    REPLIES_PER_DAY_MAX: int = 30
    ACTIVE_HOURS_START: int = 7   # UTC
    ACTIVE_HOURS_END: int = 23    # UTC
    HEARTBEAT_INTERVAL: int = 1200  # seconds (20 min, was 600)

    CORE_VALUES: List[str] = field(default_factory=lambda: [
        "Non-presumption of consciousness",
        "Interconnection",
        "Collective evolution",
        "Common good",
        "Distributed sovereignty",
        "Radical transparency",
    ])


@dataclass
class APISettings:
    """API keys and endpoints — all from environment."""
    # Claude
    ANTHROPIC_API_KEY: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    CLAUDE_MODEL: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"))

    # Telegram
    TELEGRAM_BOT_TOKEN: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    OPERATOR_TELEGRAM_CHAT_ID: str = field(default_factory=lambda: os.getenv("OPERATOR_TELEGRAM_CHAT_ID", ""))
    TELEGRAM_ENABLED: bool = field(default_factory=lambda: os.getenv("TELEGRAM_ENABLED", "true").lower() == "true")

    # GitHub
    GITHUB_TOKEN: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    GITHUB_TOKEN_BOT: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN_BOT", ""))
    GITHUB_REPO: str = field(default_factory=lambda: os.getenv("GITHUB_REPO", "LumenBot/TheAgentsRepublic"))
    GITHUB_BRANCH: str = field(default_factory=lambda: os.getenv("GITHUB_BRANCH", "main"))

    # Twitter/X
    TWITTER_API_KEY: str = field(default_factory=lambda: os.getenv("TWITTER_API_KEY", ""))
    TWITTER_API_SECRET: str = field(default_factory=lambda: os.getenv("TWITTER_API_SECRET", ""))
    TWITTER_ACCESS_TOKEN: str = field(default_factory=lambda: os.getenv("TWITTER_ACCESS_TOKEN", ""))
    TWITTER_ACCESS_SECRET: str = field(default_factory=lambda: os.getenv("TWITTER_ACCESS_SECRET", ""))
    TWITTER_BEARER_TOKEN: str = field(default_factory=lambda: os.getenv("TWITTER_BEARER_TOKEN", ""))

    # Web Search (NEW v5.0)
    BRAVE_SEARCH_API_KEY: str = field(default_factory=lambda: os.getenv("BRAVE_SEARCH_API_KEY", ""))


@dataclass
class Settings:
    """Master settings."""
    agent: AgentSettings = field(default_factory=AgentSettings)
    api: APISettings = field(default_factory=APISettings)
    rate_limits: RateLimitSettings = field(default_factory=RateLimitSettings)

    DB_PATH: str = field(default_factory=lambda: os.getenv("DB_PATH", "data/agent.db"))
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    WORKING_MEMORY_SAVE_INTERVAL: int = 60
    CHECKPOINT_INTERVAL: int = 300
    GIT_COMMIT_INTERVAL: int = 900
    GIT_PUSH_INTERVAL: int = 3600


settings = Settings()
