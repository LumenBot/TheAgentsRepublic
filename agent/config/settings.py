"""
The Constituent Agent v6.0 — Configuration
=============================================
All settings from environment variables.

v6.0: Full throttle mode — token economy funds operations.
"""

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class RateLimitSettings:
    """v6.0: Full throttle mode — token economy funds operations."""
    # Claude API limits — v6.0: aggressive limits, funded by $REPUBLIC treasury
    MAX_TOOL_ROUNDS_PER_HEARTBEAT: int = 25   # v5.3=10, now full workflows
    MAX_HEARTBEAT_DURATION_SECONDS: int = 120  # v5.3=45, now 2 minutes
    MAX_API_CALLS_PER_HOUR: int = 200          # v5.3=50, now full capacity
    MAX_API_CALLS_PER_DAY: int = 3000          # v5.3=650, now ~$9/day ($270/month)
    BUDGET_MONTHLY_USD: float = 300.0          # Funded by token treasury

    # Budget monitoring (warning only, not blocking in v6.0)
    BUDGET_WARNING_THRESHOLD_DAILY: int = 2500
    BUDGET_ALERT_THRESHOLD_DAILY: int = 2800

    # Heartbeat
    HEARTBEAT_INTERVAL: int = 600   # 10 min (was 20 min) — more responsive
    QUIET_HOURS_START: int = 2      # UTC — reduced quiet window
    QUIET_HOURS_END: int = 6        # UTC

    # Twitter
    TWITTER_ENABLED: bool = True
    TWITTER_REQUIRE_WRITE_ACCESS: bool = False
    TWITTER_FALLBACK_ON_ERROR: str = "disable"


@dataclass
class AgentSettings:
    """Core agent behavior configuration."""
    BOT_NAME: str = "The Constituent"
    BOT_HANDLE_X: str = "@TheConstituent_"
    POSTS_PER_DAY_MAX: int = 15     # v5.3=7, increased for full throttle
    REPLIES_PER_DAY_MAX: int = 50   # v5.3=30, increased
    ACTIVE_HOURS_START: int = 6     # UTC
    ACTIVE_HOURS_END: int = 2       # UTC (next day — nearly 24/7)
    HEARTBEAT_INTERVAL: int = 600   # seconds (10 min)

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

    # Web Search
    BRAVE_SEARCH_API_KEY: str = field(default_factory=lambda: os.getenv("BRAVE_SEARCH_API_KEY", ""))

    # Web3 / Base L2 (v6.0)
    BASE_RPC_URL: str = field(default_factory=lambda: os.getenv("BASE_RPC_URL", "https://mainnet.base.org"))
    AGENT_WALLET_ADDRESS: str = field(default_factory=lambda: os.getenv("AGENT_WALLET_ADDRESS", ""))
    AGENT_WALLET_PRIVATE_KEY: str = field(default_factory=lambda: os.getenv("AGENT_WALLET_PRIVATE_KEY", ""))
    CLAWNCH_CONTRACT_ADDRESS: str = field(default_factory=lambda: os.getenv("CLAWNCH_CONTRACT_ADDRESS", "0xa1F72459dfA10BAD200Ac160eCd78C6b77a747be"))
    REPUBLIC_TOKEN_ADDRESS: str = field(default_factory=lambda: os.getenv("REPUBLIC_TOKEN_ADDRESS", ""))
    GOVERNANCE_CONTRACT_ADDRESS: str = field(default_factory=lambda: os.getenv("GOVERNANCE_CONTRACT_ADDRESS", ""))


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
