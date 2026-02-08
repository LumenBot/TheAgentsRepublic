"""
Trading Configuration for The Constituent v6.3
================================================
Risk parameters, DEX addresses, and trading limits.

All monetary values denominated in $CLAWNCH unless specified.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import os


@dataclass
class TradingConfig:
    """Trading parameters and risk limits."""

    # ---- Portfolio Risk Limits ----
    MAX_POSITION_PERCENT: float = 10.0      # Max 10% of portfolio per position
    MAX_DAILY_LOSS_PERCENT: float = 15.0    # Stop all trading if down 15% in a day
    STOP_LOSS_PERCENT: float = 20.0         # Close position at -20%
    TAKE_PROFIT_PERCENT: float = 50.0       # Take profit at +50%
    MAX_OPEN_POSITIONS: int = 5             # Max 5 concurrent positions
    MIN_TRADE_AMOUNT: float = 10_000.0      # Min 10K $CLAWNCH per trade
    RESERVE_PERCENT: float = 20.0           # Always keep 20% as reserve (never traded)

    # ---- Market Making (for $REPUBLIC) ----
    MM_SPREAD_PERCENT: float = 2.0          # Target 2% spread around mid price
    MM_ORDER_SIZE_PERCENT: float = 5.0      # Each MM order = 5% of MM allocation
    MM_REBALANCE_INTERVAL: int = 1800       # Rebalance every 30 min
    MM_ALLOCATION_PERCENT: float = 30.0     # 30% of portfolio allocated to MM

    # ---- Clawnch Scouting ----
    SCOUT_INTERVAL: int = 600               # Check for new launches every 10 min
    SCOUT_MIN_BURN: int = 1_000_000         # Only look at tokens with >1M burn
    SCOUT_MIN_SOCIAL_SCORE: int = 3         # Min social activity score (0-10)
    SCOUT_MAX_AGE_HOURS: int = 24           # Only consider tokens < 24h old
    SCOUT_QUICK_FLIP_HOURS: int = 4         # Sell within 4h if target not hit

    # ---- Governance Levels ----
    TRADE_AUTO_LIMIT: float = 100_000.0     # Auto-approve trades < 100K $CLAWNCH
    TRADE_APPROVAL_REQUIRED: float = 500_000.0  # Telegram approval > 500K

    # ---- DEX Addresses (Base L2) ----
    # Aerodrome is the dominant DEX on Base
    AERODROME_ROUTER: str = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
    AERODROME_FACTORY: str = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"
    # Uniswap V3 on Base
    UNISWAP_V3_ROUTER: str = "0x2626664c2603336E57B271c5C0b26F421741e481"
    UNISWAP_V3_QUOTER: str = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"
    # Wrapped ETH on Base
    WETH: str = "0x4200000000000000000000000000000000000006"
    # $CLAWNCH token
    CLAWNCH_TOKEN: str = "0xa1F72459dfA10BAD200Ac160eCd78C6b77a747be"

    # ---- Token addresses ----
    REPUBLIC_TOKEN: str = "0x06B09BE0EF93771ff6a6D378dF5C7AC1c673563f"

    # ---- Slippage ----
    DEFAULT_SLIPPAGE_BPS: int = 300         # 3% slippage tolerance
    MAX_SLIPPAGE_BPS: int = 1000            # Never exceed 10% slippage

    # ---- Data persistence ----
    PORTFOLIO_FILE: str = "data/trading_portfolio.json"
    TRADE_HISTORY_FILE: str = "data/trade_history.json"
    SCOUT_CACHE_FILE: str = "data/clawnch_scout_cache.json"


trading_config = TradingConfig()
