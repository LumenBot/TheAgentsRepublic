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
class AgentSettings:
    """Core agent behavior configuration."""
    BOT_NAME: str = "The Constituent"
    BOT_HANDLE_X: str = "@TheConstituent_"
    POSTS_PER_DAY_MAX: int = 7
    REPLIES_PER_DAY_MAX: int = 30
    ACTIVE_HOURS_START: int = 7   # UTC
    ACTIVE_HOURS_END: int = 23    # UTC
    HEARTBEAT_INTERVAL: int = 600  # seconds (10 min)

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

    DB_PATH: str = field(default_factory=lambda: os.getenv("DB_PATH", "data/agent.db"))
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    WORKING_MEMORY_SAVE_INTERVAL: int = 60
    CHECKPOINT_INTERVAL: int = 300
    GIT_COMMIT_INTERVAL: int = 900
    GIT_PUSH_INTERVAL: int = 3600


settings = Settings()
