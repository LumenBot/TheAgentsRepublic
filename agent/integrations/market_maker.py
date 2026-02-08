"""
Market Maker — $REPUBLIC Price Support
========================================
Provides liquidity and price support for $REPUBLIC on Base L2 DEXes.

Strategy:
1. Monitor $REPUBLIC price and trading activity
2. Place buy orders when price drops below target spread
3. Place sell orders when price rises above target spread
4. Rebalance periodically to maintain inventory
5. Use profits from Clawnch scouting to fund MM operations

v6.3: Initial market making capabilities.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from ..config.trading import trading_config

logger = logging.getLogger("TheConstituent.MarketMaker")


class MarketMaker:
    """
    Market maker for $REPUBLIC token on Base L2.

    Operates a simple spread-based strategy:
    - Buys when price drops below mid - spread/2
    - Sells when price rises above mid + spread/2
    - Tracks mid price using exponential moving average
    - Respects inventory limits and daily loss caps

    All operations routed through DeFiTrader.
    """

    STATE_FILE = "data/market_maker_state.json"

    def __init__(self, trader=None):
        """
        Args:
            trader: DeFiTrader instance for executing swaps
        """
        self._trader = trader
        self._state: Dict = {}
        self._load_state()

    def set_trader(self, trader):
        """Set the DeFiTrader instance (for late binding)."""
        self._trader = trader

    def _load_state(self):
        """Load MM state from disk."""
        path = Path(self.STATE_FILE)
        if path.exists():
            try:
                self._state = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load MM state: {e}")
                self._state = self._default_state()
        else:
            self._state = self._default_state()

    def _save_state(self):
        """Save state to disk."""
        path = Path(self.STATE_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(self._state, indent=2, default=str), encoding="utf-8")

    def _default_state(self) -> Dict:
        return {
            "mid_price": 0.0,
            "ema_price": 0.0,
            "total_buys": 0,
            "total_sells": 0,
            "total_volume_clawnch": 0.0,
            "total_pnl": 0.0,
            "inventory_republic": 0.0,
            "inventory_clawnch_allocated": 0.0,
            "last_buy_price": 0.0,
            "last_sell_price": 0.0,
            "last_rebalance": "",
            "active": False,
            "created": datetime.now(timezone.utc).isoformat(),
        }

    # =================================================================
    # Price Monitoring
    # =================================================================

    def get_republic_price(self) -> Dict:
        """
        Get current $REPUBLIC price via DexScreener (free, no auth).
        Also gets $CLAWNCH price for relative pricing.
        """
        from .dex_oracle import get_token_price

        republic_data = get_token_price(trading_config.REPUBLIC_TOKEN)
        clawnch_data = get_token_price(trading_config.CLAWNCH_TOKEN)

        republic_usd = republic_data.get("price_usd", 0)
        clawnch_usd = clawnch_data.get("price_usd", 0)

        # Calculate REPUBLIC price in CLAWNCH terms
        if clawnch_usd > 0 and republic_usd > 0:
            price_per_republic = republic_usd / clawnch_usd
        else:
            price_per_republic = 0

        # Update EMA
        alpha = 0.2  # Smoothing factor
        if self._state.get("ema_price", 0) > 0:
            self._state["ema_price"] = alpha * price_per_republic + (1 - alpha) * self._state["ema_price"]
        else:
            self._state["ema_price"] = price_per_republic

        self._state["mid_price"] = price_per_republic
        self._save_state()

        return {
            "price_per_republic": price_per_republic,
            "price_usd": republic_usd,
            "clawnch_price_usd": clawnch_usd,
            "ema_price": self._state["ema_price"],
            "liquidity_usd": republic_data.get("liquidity_usd", 0),
            "volume_24h": republic_data.get("volume_24h", 0),
            "price_change_24h": republic_data.get("price_change_24h", 0),
            "source": "dexscreener",
        }

    # =================================================================
    # Market Making Logic
    # =================================================================

    def evaluate_action(self) -> Dict:
        """
        Evaluate whether to buy, sell, or hold $REPUBLIC.

        Returns:
            {"action": "buy"|"sell"|"hold", "reason": "...", "amount": float}
        """
        price_info = self.get_republic_price()
        if "error" in price_info:
            return {"action": "hold", "reason": f"Price unavailable: {price_info['error']}"}

        current_price = price_info.get("price_per_republic", 0)
        ema_price = self._state.get("ema_price", 0)

        if current_price <= 0 or ema_price <= 0:
            return {"action": "hold", "reason": "No price data available yet"}

        spread = trading_config.MM_SPREAD_PERCENT / 100
        buy_threshold = ema_price * (1 - spread / 2)
        sell_threshold = ema_price * (1 + spread / 2)

        # Get available CLAWNCH for MM
        if self._trader:
            clawnch_bal = self._trader.get_token_balance(trading_config.CLAWNCH_TOKEN)
            available = clawnch_bal.get("balance", 0) * trading_config.MM_ALLOCATION_PERCENT / 100
        else:
            available = 0

        order_size = available * trading_config.MM_ORDER_SIZE_PERCENT / 100

        if current_price < buy_threshold and order_size > trading_config.MIN_TRADE_AMOUNT:
            deviation = (ema_price - current_price) / ema_price * 100
            return {
                "action": "buy",
                "reason": f"Price ({current_price:.6f}) below buy threshold ({buy_threshold:.6f}), -{deviation:.1f}% from EMA",
                "amount": order_size,
                "price": current_price,
                "ema": ema_price,
            }

        elif current_price > sell_threshold:
            # Check if we have REPUBLIC to sell
            if self._trader:
                republic_bal = self._trader.get_token_balance(trading_config.REPUBLIC_TOKEN)
                republic_amount = republic_bal.get("balance", 0)
                if republic_amount > 0:
                    sell_amount = republic_amount * trading_config.MM_ORDER_SIZE_PERCENT / 100
                    deviation = (current_price - ema_price) / ema_price * 100
                    return {
                        "action": "sell",
                        "reason": f"Price ({current_price:.6f}) above sell threshold ({sell_threshold:.6f}), +{deviation:.1f}% from EMA",
                        "amount": sell_amount,
                        "price": current_price,
                        "ema": ema_price,
                    }

        return {
            "action": "hold",
            "reason": f"Price ({current_price:.6f}) within spread [{buy_threshold:.6f} - {sell_threshold:.6f}]",
            "price": current_price,
            "ema": ema_price,
        }

    def execute_mm_cycle(self) -> Dict:
        """
        Run one market-making cycle: evaluate + execute if needed.

        Returns result of the action taken.
        """
        if not self._state.get("active", False):
            return {"action": "skip", "reason": "Market maker not active. Use /mm_start to activate."}

        evaluation = self.evaluate_action()
        action = evaluation.get("action")

        if action == "buy":
            amount = evaluation.get("amount", 0)
            result = self._trader.buy_republic(amount, reason="MM buy - price support")
            self._state["total_buys"] += 1
            self._state["total_volume_clawnch"] += amount
            self._state["last_buy_price"] = evaluation.get("price", 0)
            self._save_state()
            return {"action": "buy", "evaluation": evaluation, "result": result}

        elif action == "sell":
            amount = evaluation.get("amount", 0)
            result = self._trader.sell_token(
                trading_config.REPUBLIC_TOKEN, amount,
                reason="MM sell - take profit"
            )
            self._state["total_sells"] += 1
            if "pnl" in result:
                self._state["total_pnl"] += result.get("pnl", 0)
            self._state["last_sell_price"] = evaluation.get("price", 0)
            self._save_state()
            return {"action": "sell", "evaluation": evaluation, "result": result}

        return {"action": "hold", "evaluation": evaluation}

    # =================================================================
    # Control
    # =================================================================

    def start(self) -> Dict:
        """Activate market making."""
        self._state["active"] = True
        self._save_state()
        logger.info("Market maker activated for $REPUBLIC")
        return {"status": "ok", "message": "Market maker activated"}

    def stop(self) -> Dict:
        """Deactivate market making."""
        self._state["active"] = False
        self._save_state()
        logger.info("Market maker deactivated")
        return {"status": "ok", "message": "Market maker deactivated"}

    def is_active(self) -> bool:
        return self._state.get("active", False)

    # =================================================================
    # Reporting
    # =================================================================

    def get_mm_report(self) -> str:
        """Generate market maker status report."""
        price_info = self.get_republic_price() if self._trader else {}

        lines = [
            "Market Maker Report — $REPUBLIC",
            "=" * 40,
            f"Active: {'YES' if self._state.get('active') else 'NO'}",
            f"Current price: {price_info.get('price_per_republic', 'N/A')}",
            f"EMA price: {self._state.get('ema_price', 'N/A')}",
            f"Spread target: {trading_config.MM_SPREAD_PERCENT}%",
            f"Total buys: {self._state.get('total_buys', 0)}",
            f"Total sells: {self._state.get('total_sells', 0)}",
            f"Total volume: {self._state.get('total_volume_clawnch', 0):,.0f} CLAWNCH",
            f"Total P&L: {self._state.get('total_pnl', 0):,.0f} CLAWNCH",
            f"Last buy price: {self._state.get('last_buy_price', 'N/A')}",
            f"Last sell price: {self._state.get('last_sell_price', 'N/A')}",
        ]

        return "\n".join(lines)

    def get_status(self) -> Dict:
        """Quick status."""
        return {
            "active": self._state.get("active", False),
            "mid_price": self._state.get("mid_price", 0),
            "ema_price": self._state.get("ema_price", 0),
            "total_buys": self._state.get("total_buys", 0),
            "total_sells": self._state.get("total_sells", 0),
            "total_pnl": self._state.get("total_pnl", 0),
        }
